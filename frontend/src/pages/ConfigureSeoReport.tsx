import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, ArrowLeft } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

type TabKey = "gsc" | "ga" | "rank" | "base" | "overview";

const TABS: { key: TabKey; label: string }[] = [
  { key: "gsc", label: "Google Search Console" },
  { key: "ga", label: "Google Analytics" },
  { key: "rank", label: "Keyword Ranking" },
  { key: "base", label: "Domain Metrics" },
  { key: "overview", label: "Summary" },
];

const WEEK_INTERVALS = [
  "Past 1 week", "Past 2 weeks", "Past 3 weeks", "Past 4 weeks", "Past 5 weeks",
  "Past 6 weeks", "Past 7 weeks", "Past 8 weeks", "Past 9 weeks",
  "Past 10 weeks", "Past 11 weeks", "Past 12 weeks",
];
const MONTH_INTERVALS = [
  "Past 1 month", "Past 2 months", "Past 3 months", "Past 4 months",
  "Past 5 months", "Past 6 months", "Past 7 months", "Past 8 months",
  "Past 9 months", "Past 10 months", "Past 11 months", "Past 12 months",
];
const ORDER_BY_VALS = ["Ascending", "Descending"];

const ConfigureSeoReport = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [activeTab, setActiveTab] = useState<TabKey>("gsc");
  const [loading, setLoading] = useState(false);

  // GSC/GA connection status
  const [isGscConnected, setIsGscConnected] = useState(false);
  const [isGaConnected, setIsGaConnected] = useState(false);

  // Fetch integration status on mount
  useEffect(() => {
    if (selectedDomain?.id) {
      const checkIntegrations = async () => {
        try {
          const res = (await apiClient.getIntegrationsByDomain(
            selectedDomain.id
          )) as any;
          // Response is a direct array from DRF serializer
          const list = Array.isArray(res) ? res : (Array.isArray(res?.results) ? res.results : []);

          const isConnected = (i: any) =>
            i.status === "active" &&
            !!i.provider_id &&
            i.provider_id !== "" &&
            i.provider_id !== "pending_selection";

          const gsc = list.find((i: any) => i.type === "search_console" && isConnected(i));
          const ga = list.find((i: any) => i.type === "google_analytics" && isConnected(i));

          setIsGscConnected(!!gsc);
          setIsGaConnected(!!ga);
        } catch {
          setIsGscConnected(false);
          setIsGaConnected(false);
        }
      };
      checkIntegrations();
    }
  }, [selectedDomain?.id]);

  // Form state
  const [formState, setFormState] = useState({
    sheetName: "",
    gscTypes: [] as string[],
    gscMetrics: [] as string[],
    gaType: "Landing Pages",
    rankMetrics: [] as string[],
    summaryMetric: "google_analytics",
    summaryEventNames: "Register_submit, otp_verified, Live_account",
    schedule: "Weekly Schedule",
    weekInterval: "Past 2 weeks",
    monthInterval: "Past 3 months",
    orderBy: "Ascending",
    changeUnits: [] as string[],
  });

  const isMonthly = formState.schedule === "Monthly Schedule";

  const toggleArrayItem = (
    field: "gscTypes" | "gscMetrics" | "rankMetrics" | "changeUnits",
    value: string
  ) => {
    setFormState((prev) => {
      const arr = prev[field];
      return {
        ...prev,
        [field]: arr.includes(value)
          ? arr.filter((v) => v !== value)
          : [...arr, value],
      };
    });
  };

  const handleSubmit = async () => {
    if (!selectedDomain?.id) {
      toast({ title: "Error", description: "Please select a domain first.", variant: "destructive" });
      return;
    }

    if (!formState.sheetName.trim()) {
      toast({ title: "Validation", description: "Please enter the sheet name.", variant: "destructive" });
      return;
    }

    let sheetType = "";
    let metrics: string[] = [];
    const changeUnits: string[] = formState.changeUnits;
    let schedule = isMonthly ? "monthly" : "weekly";
    let duration = 2;

    const intervalStr = isMonthly ? formState.monthInterval : formState.weekInterval;
    const match = intervalStr.match(/Past (\d+)/);
    if (match) duration = parseInt(match[1]);

    switch (activeTab) {
      case "gsc": {
        if (!isGscConnected) {
          toast({ title: "Validation", description: "Connect Google Search Console to add GSC sheet.", variant: "destructive" });
          return;
        }
        if (formState.gscTypes.length === 0) {
          toast({ title: "Validation", description: "Please select the Types.", variant: "destructive" });
          return;
        }
        if (formState.gscMetrics.length === 0) {
          toast({ title: "Validation", description: "Please select the Metrics.", variant: "destructive" });
          return;
        }
        // RankMaxx creates one sheet per selected type.
        // If both branded & non-branded are selected, merge into 'gsc_queries'.
        const selectedTypes = [...formState.gscTypes];
        const hasBranded = selectedTypes.includes("gsc_branded_queries");
        const hasNonBranded = selectedTypes.includes("gsc_non_branded_queries");
        const sheetTypes: string[] = [];
        if (selectedTypes.includes("gsc_pages")) sheetTypes.push("gsc_pages");
        if (hasBranded && hasNonBranded) {
          sheetTypes.push("gsc_queries");
        } else {
          if (hasBranded) sheetTypes.push("gsc_branded_queries");
          if (hasNonBranded) sheetTypes.push("gsc_non_branded_queries");
        }
        metrics = formState.gscMetrics;

        // Create one sheet per resolved type
        setLoading(true);
        try {
          for (const st of sheetTypes) {
            await apiClient.addSeoReportSheet({
              domain_id: selectedDomain.id,
              sheet_name: formState.sheetName.trim(),
              category: activeTab,
              sheet_type: st,
              metrics,
              change_units: changeUnits,
              schedule,
              duration,
              order_by: formState.orderBy,
            });
          }
          toast({ title: "Success", description: `Report "${formState.sheetName}" added successfully.` });
          navigate("/seo-reports");
        } catch (err: any) {
          toast({ title: "Error", description: err.message || "Failed to add report.", variant: "destructive" });
        } finally {
          setLoading(false);
        }
        return; // Early return — we handled submission above
      }

      case "ga":
        if (!isGaConnected) {
          toast({ title: "Validation", description: "Connect Google Analytics to add GA sheet.", variant: "destructive" });
          return;
        }
        if (formState.gaType === "GA vs GSC" && !isGscConnected) {
          toast({ title: "Validation", description: "GA vs GSC needs both Google Analytics and Google Search Console connected.", variant: "destructive" });
          return;
        }
        sheetType =
          formState.gaType === "Landing Pages"            ? "ga_landing_pages"
          : formState.gaType === "Other Sources"          ? "ga_other_sources"
          : formState.gaType === "GA vs GSC" ? "ga_gsc_reconcile"
          : "ga_landing_pages";
        break;

      case "rank":
        sheetType = "keyword_ranking";
        metrics = formState.rankMetrics.length > 0 ? formState.rankMetrics : [];
        break;

      case "base":
        sheetType = "domain_metrics";
        schedule = "monthly";
        break;

      case "overview": {
        const summaryMap: Record<string, string> = {
          google_analytics: "ga_overview",
          google_search_console: "gsc_overview",
          keyword_ranking: "keyword_ranking_overview",
          domain_metrics: "domain_metrics",
          ga_organic_traffic_breakup: "ga_organic_traffic_breakup",
          ga_country_events: "ga_country_events",
          keyword_ranking_summary: "keyword_ranking_summary",
          competitor_ranking_summary: "competitor_ranking_summary",
        };
        const needsGa =
          formState.summaryMetric === "google_analytics" ||
          formState.summaryMetric === "ga_organic_traffic_breakup" ||
          formState.summaryMetric === "ga_country_events";
        if (needsGa && !isGaConnected) {
          toast({ title: "Validation", description: "Connect Google Analytics to add GA sheet.", variant: "destructive" });
          return;
        }
        if (formState.summaryMetric === "google_search_console" && !isGscConnected) {
          toast({ title: "Validation", description: "Connect Google Search Console to add GSC sheet.", variant: "destructive" });
          return;
        }
        sheetType = summaryMap[formState.summaryMetric] || "ga_overview";
        if (formState.summaryMetric === "ga_country_events") {
          metrics = formState.summaryEventNames
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean);
          if (metrics.length === 0) {
            toast({
              title: "Validation",
              description: "Enter at least one event name (comma-separated) for Country-wise Events.",
              variant: "destructive",
            });
            return;
          }
        }
        break;
      }
    }

    setLoading(true);
    try {
      await apiClient.addSeoReportSheet({
        domain_id: selectedDomain.id,
        sheet_name: formState.sheetName.trim(),
        category: activeTab,
        sheet_type: sheetType,
        metrics,
        change_units: changeUnits,
        schedule,
        duration,
        order_by: formState.orderBy,
      });

      toast({ title: "Success", description: `Report "${formState.sheetName}" added successfully.` });
      navigate("/seo-reports");
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to add report.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const placeholderMap: Record<TabKey, string> = {
    gsc: "Ex: Google Search Console",
    ga: "Ex: Google Analytics",
    rank: "Ex: Keyword Ranking",
    base: "Ex: Domain Metrics",
    overview: "Ex: Google Analytics Overview",
  };

  // Redirect if no domain selected
  if (!selectedDomain?.id) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Please select a domain first.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: "#FBFDFF" }}>
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-5 bg-white border-b flex-shrink-0">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/seo-reports")}
            className="rounded-full p-2 hover:bg-muted transition-colors"
            aria-label="Back"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-[22px] font-bold leading-7 text-foreground">
              Configure Report
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Customize and control reports to fit your unique requirements.
            </p>
          </div>
        </div>
      </header>

      {/* ── Scrollable Content ── */}
      <div className="flex-1 overflow-y-auto pb-24 px-6 py-5">
        {/* Tab Navigation */}
        <div className="flex flex-wrap gap-2 mb-6">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all border ${
                activeTab === tab.key
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-white text-muted-foreground border-border hover:border-primary/40 hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Form Card ── */}
        <div className="rounded-lg p-6 space-y-6" style={{ backgroundColor: "#f6f9fe" }}>
          {/* Report Name */}
          <div className="bg-white rounded-lg p-5">
            <Label className="text-sm font-semibold">
              Report Name <span className="text-destructive">*</span>
            </Label>
            <Input
              className="mt-2 max-w-sm"
              placeholder={placeholderMap[activeTab]}
              value={formState.sheetName}
              onChange={(e) => setFormState((p) => ({ ...p, sheetName: e.target.value }))}
            />
          </div>

          {/* Tab-specific content (non-overview tabs show metrics first) */}
          {activeTab === "gsc" && <GscForm formState={formState} toggleArrayItem={toggleArrayItem} />}
          {activeTab === "ga" && <GaForm formState={formState} setFormState={setFormState} isGscConnected={isGscConnected} />}
          {activeTab === "rank" && <RankForm formState={formState} toggleArrayItem={toggleArrayItem} />}
          {activeTab === "base" && <BaseForm />}

          {/* Duration & Order By */}
          {activeTab !== "base" ? (
            <DurationOrderSection
              formState={formState}
              setFormState={setFormState}
              isMonthly={isMonthly}
              hideOrderBy={
                activeTab === "overview" &&
                (formState.summaryMetric === "keyword_ranking" ||
                  formState.summaryMetric === "competitor_ranking_summary")
              }
              hideDuration={
                activeTab === "overview" &&
                formState.summaryMetric === "competitor_ranking_summary"
              }
            />
          ) : (
            <BaseDurationSection formState={formState} setFormState={setFormState} />
          )}

          {/* Summary tab: Metrics come AFTER Duration (matches RankMaxx layout) */}
          {activeTab === "overview" && <OverviewForm formState={formState} setFormState={setFormState} />}

          {/* Comparison section */}
          {(activeTab === "gsc" || (activeTab === "ga" && formState.gaType === "Landing Pages") || activeTab === "base") && (
            <ComparisonSection formState={formState} toggleArrayItem={toggleArrayItem} />
          )}

          {/* Action buttons (inside form card, like RankMaxx) */}
          <div className="flex items-center justify-center gap-5 pt-2 pb-1">
            <Button variant="outline" className="min-w-[130px]" onClick={() => navigate("/seo-reports")} disabled={loading}>
              Cancel
            </Button>
            <Button className="min-w-[150px]" onClick={handleSubmit} disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Add Report
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── Section wrapper ─────────────────────────────────────────────────────────

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg p-5">
      <h3 className="text-sm font-semibold mb-3 pb-2 border-b">{title}</h3>
      {children}
    </div>
  );
}

// ─── GSC Form ────────────────────────────────────────────────────────────────

function GscForm({ formState, toggleArrayItem }: { formState: any; toggleArrayItem: (field: any, value: string) => void }) {
  return (
    <>
      <FormSection title="Types">
        <div className="grid grid-cols-3 gap-4">
          {[
            { value: "gsc_pages", label: "Pages" },
            { value: "gsc_branded_queries", label: "Branded Queries" },
            { value: "gsc_non_branded_queries", label: "Non Branded Queries" },
          ].map((item) => (
            <label key={item.value} className="flex items-center gap-2 cursor-pointer">
              <Checkbox checked={formState.gscTypes.includes(item.value)} onCheckedChange={() => toggleArrayItem("gscTypes", item.value)} />
              <span className="text-sm">{item.label}</span>
            </label>
          ))}
        </div>
      </FormSection>

      <FormSection title="Metrics">
        <div className="grid grid-cols-4 gap-4">
          {[
            { value: "clicks", label: "Clicks" },
            { value: "impressions", label: "Impression" },
            { value: "ctr", label: "CTR" },
            { value: "position", label: "Position" },
          ].map((item) => (
            <label key={item.value} className="flex items-center gap-2 cursor-pointer">
              <Checkbox checked={formState.gscMetrics.includes(item.value)} onCheckedChange={() => toggleArrayItem("gscMetrics", item.value)} />
              <span className="text-sm">{item.label}</span>
            </label>
          ))}
        </div>
      </FormSection>
    </>
  );
}

// ─── GA Form ─────────────────────────────────────────────────────────────────

function GaForm({
  formState,
  setFormState,
  isGscConnected,
}: {
  formState: any;
  setFormState: React.Dispatch<React.SetStateAction<any>>;
  isGscConnected: boolean;
}) {
  const isReconcile = formState.gaType === "GA vs GSC";
  return (
    <FormSection title="Types">
      <Select value={formState.gaType} onValueChange={(v) => setFormState((p: any) => ({ ...p, gaType: v }))}>
        <SelectTrigger className="w-[260px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Landing Pages">Landing Pages</SelectItem>
          <SelectItem value="Other Sources">Other Sources</SelectItem>
          <SelectItem
            value="GA vs GSC"
            disabled={!isGscConnected}
          >
            GA vs GSC{!isGscConnected && " (GSC not connected)"}
          </SelectItem>
        </SelectContent>
      </Select>
      {isReconcile && (
        <p className="text-xs text-muted-foreground mt-2">
          This report needs both Google Analytics and Google Search Console connected.
          {!isGscConnected && (
            <span className="text-destructive font-medium">
              {" "}Google Search Console is not connected for this domain — connect it in Domain Settings before saving.
            </span>
          )}
        </p>
      )}
    </FormSection>
  );
}

// ─── Rank Form ───────────────────────────────────────────────────────────────

function RankForm({ formState, toggleArrayItem }: { formState: any; toggleArrayItem: (field: any, value: string) => void }) {
  return (
    <FormSection title="Metrics">
      <div className="grid grid-cols-4 gap-4">
        <label className="flex items-center gap-2 cursor-not-allowed opacity-70">
          <Checkbox checked={true} disabled />
          <span className="text-sm">Keywords</span>
        </label>
        {[
          { value: "average_volume", label: "Search Volume" },
          { value: "landing_pages", label: "Ranking Url" },
          { value: "base_ranking", label: "Base Rank" },
        ].map((item) => (
          <label key={item.value} className="flex items-center gap-2 cursor-pointer">
            <Checkbox checked={formState.rankMetrics.includes(item.value)} onCheckedChange={() => toggleArrayItem("rankMetrics", item.value)} />
            <span className="text-sm">{item.label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

// ─── Base (Domain Metrics) Form ──────────────────────────────────────────────

function BaseForm() {
  return (
    <FormSection title="Metrics">
      <div className="grid grid-cols-4 gap-4">
        {[
          "Domain Authority (MOZ)", "Domain Rating (AHREF)",
          "Number of Backlinks (AHREF)", "Referring Domains (AHREF)",
        ].map((label) => (
          <label key={label} className="flex items-center gap-2 cursor-not-allowed opacity-70">
            <Checkbox checked={true} disabled />
            <span className="text-sm">{label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

// ─── Overview (Summary) Form ─────────────────────────────────────────────────

function OverviewForm({ formState, setFormState }: { formState: any; setFormState: React.Dispatch<React.SetStateAction<any>> }) {
  return (
    <FormSection title="Metrics">
      <div className="grid grid-cols-3 gap-4">
        {[
          { value: "google_analytics", label: "Google Analytics" },
          { value: "google_search_console", label: "Google Search Console" },
          { value: "keyword_ranking", label: "Keyword Ranking" },
          { value: "domain_metrics", label: "Domain Metrics" },
          { value: "ga_organic_traffic_breakup", label: "GA Organic Traffic Breakup" },
          { value: "ga_country_events", label: "GA Country-wise Events" },
          { value: "keyword_ranking_summary", label: "Keyword Ranking Summary" },
          { value: "competitor_ranking_summary", label: "Competitor Ranking Summary" },
        ].map((item) => (
          <label key={item.value} className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="summaryMetric"
              value={item.value}
              checked={formState.summaryMetric === item.value}
              onChange={(e) => setFormState((p: any) => ({ ...p, summaryMetric: e.target.value }))}
              className="h-4 w-4 accent-primary"
            />
            <span className="text-sm">{item.label}</span>
          </label>
        ))}
      </div>
      {formState.summaryMetric === "ga_country_events" && (
        <div className="mt-4">
          <Label className="text-xs text-muted-foreground">
            Event Names <span className="text-destructive">*</span>
          </Label>
          <Input
            type="text"
            placeholder="Register_submit, otp_verified, Live_account"
            value={formState.summaryEventNames}
            onChange={(e) => setFormState((p: any) => ({ ...p, summaryEventNames: e.target.value }))}
            className="mt-1"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Comma-separated GA4 event names to track per country (Organic Search).
          </p>
        </div>
      )}
    </FormSection>
  );
}

// ─── Duration & Order By ─────────────────────────────────────────────────────

function DurationOrderSection({ formState, setFormState, isMonthly, hideOrderBy = false, hideDuration = false }: { formState: any; setFormState: React.Dispatch<React.SetStateAction<any>>; isMonthly: boolean; hideOrderBy?: boolean; hideDuration?: boolean }) {
  if (hideDuration && hideOrderBy) return null;
  return (
    <div className="bg-white rounded-lg p-5">
      <div className="flex flex-wrap gap-12">
        {!hideDuration && (
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">Duration</h3>
          <Label className="text-xs text-muted-foreground">
            Schedule & Interval <span className="text-destructive">*</span>
          </Label>
          <div className="flex gap-3 mt-2">
            <Select value={formState.schedule} onValueChange={(v) => setFormState((p: any) => ({ ...p, schedule: v }))}>
              <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Weekly Schedule">Weekly Schedule</SelectItem>
                <SelectItem value="Monthly Schedule">Monthly Schedule</SelectItem>
              </SelectContent>
            </Select>
            {isMonthly ? (
              <Select value={formState.monthInterval} onValueChange={(v) => setFormState((p: any) => ({ ...p, monthInterval: v }))}>
                <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {MONTH_INTERVALS.map((i) => (<SelectItem key={i} value={i}>{i}</SelectItem>))}
                </SelectContent>
              </Select>
            ) : (
              <Select value={formState.weekInterval} onValueChange={(v) => setFormState((p: any) => ({ ...p, weekInterval: v }))}>
                <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {WEEK_INTERVALS.map((i) => (<SelectItem key={i} value={i}>{i}</SelectItem>))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
        )}
        {!hideOrderBy && (
          <div>
            <h3 className="text-sm font-semibold mb-3 pb-2 border-b">Order By</h3>
            <Label className="text-xs text-muted-foreground">
              Date Sort <span className="text-destructive">*</span>
            </Label>
            <div className="mt-2">
              <Select value={formState.orderBy} onValueChange={(v) => setFormState((p: any) => ({ ...p, orderBy: v }))}>
                <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ORDER_BY_VALS.map((v) => (<SelectItem key={v} value={v}>{v}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Base Duration Section ───────────────────────────────────────────────────

function BaseDurationSection({ formState, setFormState }: { formState: any; setFormState: React.Dispatch<React.SetStateAction<any>> }) {
  return (
    <div className="bg-white rounded-lg p-5">
      <div className="flex flex-wrap gap-12">
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">Duration</h3>
          <Label className="text-xs text-muted-foreground">
            Monthly Interval <span className="text-destructive">*</span>
          </Label>
          <div className="mt-2">
            <Select value={formState.monthInterval} onValueChange={(v) => setFormState((p: any) => ({ ...p, monthInterval: v }))}>
              <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {MONTH_INTERVALS.map((i) => (<SelectItem key={i} value={i}>{i}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">Order By</h3>
          <Label className="text-xs text-muted-foreground">
            Date Sort <span className="text-destructive">*</span>
          </Label>
          <div className="mt-2">
            <Select value={formState.orderBy} onValueChange={(v) => setFormState((p: any) => ({ ...p, orderBy: v }))}>
              <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {ORDER_BY_VALS.map((v) => (<SelectItem key={v} value={v}>{v}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Comparison Section ──────────────────────────────────────────────────────

function ComparisonSection({ formState, toggleArrayItem }: { formState: any; toggleArrayItem: (field: any, value: string) => void }) {
  return (
    <FormSection title="Comparison">
      <div className="flex gap-6">
        {[
          { value: "number", label: "Change in Number" },
          { value: "percentage", label: "Change in Percentage" },
        ].map((item) => (
          <label key={item.value} className="flex items-center gap-2 cursor-pointer">
            <Checkbox checked={formState.changeUnits.includes(item.value)} onCheckedChange={() => toggleArrayItem("changeUnits", item.value)} />
            <span className="text-sm">{item.label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

export default ConfigureSeoReport;
