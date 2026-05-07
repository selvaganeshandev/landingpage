import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
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
import { Loader2, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

type TabKey = "gsc" | "ga" | "rank" | "base" | "overview";

interface TabConfig {
  key: TabKey;
  label: string;
}

const TABS: TabConfig[] = [
  { key: "gsc", label: "Google Search Console" },
  { key: "ga", label: "Google Analytics" },
  { key: "rank", label: "Keyword Ranking" },
  { key: "base", label: "Domain Metrics" },
  { key: "overview", label: "Summary" },
];

const WEEK_INTERVALS = [
  "Past 2 weeks", "Past 3 weeks", "Past 4 weeks", "Past 5 weeks",
  "Past 6 weeks", "Past 7 weeks", "Past 8 weeks", "Past 9 weeks",
  "Past 10 weeks", "Past 11 weeks", "Past 12 weeks",
];
const MONTH_INTERVALS = [
  "Past 1 month", "Past 2 months", "Past 3 months", "Past 4 months",
  "Past 5 months", "Past 6 months", "Past 7 months", "Past 8 months",
  "Past 9 months", "Past 10 months", "Past 11 months", "Past 12 months",
];
const ORDER_BY_VALS = ["Ascending", "Descending"];

interface ConfigureSeoReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function ConfigureSeoReportDialog({
  open,
  onOpenChange,
  onSuccess,
}: ConfigureSeoReportDialogProps) {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [activeTab, setActiveTab] = useState<TabKey>("gsc");
  const [loading, setLoading] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // GSC/GA connection status
  const [isGscConnected, setIsGscConnected] = useState(false);
  const [isGaConnected, setIsGaConnected] = useState(false);

  // Fetch integration status when dialog opens
  useEffect(() => {
    if (open && selectedDomain?.id) {
      const checkIntegrations = async () => {
        try {
          const res = (await apiClient.getIntegrationsByDomain(
            selectedDomain.id
          )) as any;
          const integrations = res?.integrations || res || [];
          const list = Array.isArray(integrations) ? integrations : [];

          const gscIntegration = list.find(
            (i: any) =>
              i.type === "search_console" &&
              i.status === "active" &&
              i.provider_id &&
              i.provider_id !== "" &&
              i.provider_id !== "pending_selection"
          );
          const gaIntegration = list.find(
            (i: any) =>
              i.type === "google_analytics" &&
              i.status === "active" &&
              i.provider_id &&
              i.provider_id !== "" &&
              i.provider_id !== "pending_selection"
          );

          setIsGscConnected(!!gscIntegration);
          setIsGaConnected(!!gaIntegration);
        } catch {
          setIsGscConnected(false);
          setIsGaConnected(false);
        }
      };
      checkIntegrations();
    }
  }, [open, selectedDomain?.id]);

  // Form state per tab
  const [formState, setFormState] = useState(getInitialFormState());

  function getInitialFormState() {
    return {
      sheetName: "",
      gscTypes: [] as string[],
      gscMetrics: [] as string[],
      gaType: "Landing Pages",
      rankMetrics: [] as string[],
      summaryMetric: "google_analytics",
      schedule: "Weekly Schedule",
      weekInterval: "Past 2 weeks",
      monthInterval: "Past 3 months",
      orderBy: "Ascending",
      changeUnits: [] as string[],
    };
  }

  const resetForm = () => {
    setFormState(getInitialFormState());
    setActiveTab("gsc");
  };

  // Animate in/out
  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => setIsVisible(true));
    } else {
      setIsVisible(false);
    }
  }, [open]);

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(() => {
      resetForm();
      onOpenChange(false);
    }, 200);
  };

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
      toast({
        title: "Error",
        description: "Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    if (!formState.sheetName.trim()) {
      toast({
        title: "Validation",
        description: "Please enter the sheet name.",
        variant: "destructive",
      });
      return;
    }

    let sheetType = "";
    let metrics: string[] = [];
    const changeUnits: string[] = formState.changeUnits;
    let schedule = isMonthly ? "monthly" : "weekly";
    let duration = 2;

    const intervalStr = isMonthly
      ? formState.monthInterval
      : formState.weekInterval;
    const match = intervalStr.match(/Past (\d+)/);
    if (match) duration = parseInt(match[1]);

    switch (activeTab) {
      case "gsc":
        if (!isGscConnected) {
          toast({
            title: "Validation",
            description:
              "Connect Google Search Console to add GSC sheet.",
            variant: "destructive",
          });
          return;
        }
        if (formState.gscTypes.length === 0) {
          toast({
            title: "Validation",
            description: "Please select the Types.",
            variant: "destructive",
          });
          return;
        }
        if (formState.gscMetrics.length === 0) {
          toast({
            title: "Validation",
            description: "Please select the Metrics.",
            variant: "destructive",
          });
          return;
        }
        sheetType = formState.gscTypes[0];
        metrics = formState.gscMetrics;
        break;

      case "ga":
        if (!isGaConnected) {
          toast({
            title: "Validation",
            description: "Connect Google Analytics to add GA sheet.",
            variant: "destructive",
          });
          return;
        }
        sheetType =
          formState.gaType === "Landing Pages"
            ? "ga_landing_pages"
            : "ga_other_sources";
        break;

      case "rank":
        if (formState.rankMetrics.length < 2) {
          toast({
            title: "Validation",
            description: "Choose at least three keyword metrics.",
            variant: "destructive",
          });
          return;
        }
        sheetType = "keyword_ranking";
        metrics = ["keywords", ...formState.rankMetrics];
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
          ga_organic_traffic_breakup: "ga_organic_traffic_breakup",
        };
        const needsGa =
          formState.summaryMetric === "google_analytics" ||
          formState.summaryMetric === "ga_organic_traffic_breakup";
        if (needsGa && !isGaConnected) {
          toast({
            title: "Validation",
            description: "Connect Google Analytics to add GA sheet.",
            variant: "destructive",
          });
          return;
        }
        if (
          formState.summaryMetric === "google_search_console" &&
          !isGscConnected
        ) {
          toast({
            title: "Validation",
            description:
              "Connect Google Search Console to add GSC sheet.",
            variant: "destructive",
          });
          return;
        }
        sheetType = summaryMap[formState.summaryMetric] || "ga_overview";
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

      toast({
        title: "Success",
        description: `Report "${formState.sheetName}" added successfully.`,
      });
      resetForm();
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Failed to add report.",
        variant: "destructive",
      });
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

  if (!open) return null;

  return createPortal(
    <div
      className={`fixed inset-0 z-50 transition-opacity duration-200 ${
        isVisible ? "opacity-100" : "opacity-0"
      }`}
      style={{ paddingLeft: "60px" }}
    >
      {/* Full-page modal */}
      <div
        className={`relative w-full h-full flex flex-col transition-transform duration-200 ${
          isVisible ? "translate-y-0" : "translate-y-4"
        }`}
        style={{ backgroundColor: "#FBFDFF" }}
      >
        {/* ── Header ── */}
        <header className="flex items-center justify-between px-6 py-5 bg-white border-b flex-shrink-0 z-10">
          <div>
            <h2 className="text-[22px] font-bold leading-7 text-foreground">
              Configure Report
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Customize and control reports to fit your unique requirements.
            </p>
          </div>
          <button
            onClick={handleClose}
            className="rounded-full p-2 hover:bg-muted transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
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
          <div
            className="rounded-lg p-6 space-y-6"
            style={{ backgroundColor: "#f6f9fe" }}
          >
            {/* Report Name */}
            <div className="bg-white rounded-lg p-5">
              <Label className="text-sm font-semibold">
                Report Name <span className="text-destructive">*</span>
              </Label>
              <Input
                className="mt-2 max-w-sm"
                placeholder={placeholderMap[activeTab]}
                value={formState.sheetName}
                onChange={(e) =>
                  setFormState((p) => ({
                    ...p,
                    sheetName: e.target.value,
                  }))
                }
              />
            </div>

            {/* Tab-specific content */}
            {activeTab === "gsc" && (
              <GscForm
                formState={formState}
                toggleArrayItem={toggleArrayItem}
              />
            )}
            {activeTab === "ga" && (
              <GaForm
                formState={formState}
                setFormState={setFormState}
              />
            )}
            {activeTab === "rank" && (
              <RankForm
                formState={formState}
                toggleArrayItem={toggleArrayItem}
              />
            )}
            {activeTab === "base" && <BaseForm />}
            {activeTab === "overview" && (
              <OverviewForm
                formState={formState}
                setFormState={setFormState}
              />
            )}

            {/* Duration & Order By */}
            {activeTab !== "base" ? (
              <DurationOrderSection
                formState={formState}
                setFormState={setFormState}
                isMonthly={isMonthly}
              />
            ) : (
              <BaseDurationSection
                formState={formState}
                setFormState={setFormState}
              />
            )}

            {/* Comparison section */}
            {(activeTab === "gsc" ||
              (activeTab === "ga" &&
                formState.gaType === "Landing Pages") ||
              activeTab === "base") && (
              <ComparisonSection
                formState={formState}
                toggleArrayItem={toggleArrayItem}
              />
            )}
          </div>
        </div>

        {/* ── Fixed Footer ── */}
        <div
          className="fixed bottom-0 right-0 bg-white border-t flex items-center justify-center gap-5 py-4 z-10"
          style={{ left: "60px" }}
        >
          <Button
            variant="outline"
            className="min-w-[130px]"
            onClick={handleClose}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            className="min-w-[150px]"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading && (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            )}
            Add Report
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}

// ─── Section wrapper (white card inside light-blue area) ─────────────────────

function FormSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg p-5">
      <h3 className="text-sm font-semibold mb-3 pb-2 border-b">
        {title}
      </h3>
      {children}
    </div>
  );
}

// ─── GSC Form ────────────────────────────────────────────────────────────────

function GscForm({
  formState,
  toggleArrayItem,
}: {
  formState: ReturnType<typeof Object>;
  toggleArrayItem: (field: any, value: string) => void;
}) {
  const f = formState as any;
  return (
    <>
      <FormSection title="Types">
        <div className="grid grid-cols-3 gap-4">
          {[
            { value: "gsc_pages", label: "Pages" },
            {
              value: "gsc_branded_queries",
              label: "Branded Queries",
            },
            {
              value: "gsc_non_branded_queries",
              label: "Non Branded Queries",
            },
          ].map((item) => (
            <label
              key={item.value}
              className="flex items-center gap-2 cursor-pointer"
            >
              <Checkbox
                checked={f.gscTypes.includes(item.value)}
                onCheckedChange={() =>
                  toggleArrayItem("gscTypes", item.value)
                }
              />
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
            <label
              key={item.value}
              className="flex items-center gap-2 cursor-pointer"
            >
              <Checkbox
                checked={f.gscMetrics.includes(item.value)}
                onCheckedChange={() =>
                  toggleArrayItem("gscMetrics", item.value)
                }
              />
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
}: {
  formState: any;
  setFormState: React.Dispatch<React.SetStateAction<any>>;
}) {
  return (
    <FormSection title="Types">
      <Select
        value={formState.gaType}
        onValueChange={(v) =>
          setFormState((p: any) => ({ ...p, gaType: v }))
        }
      >
        <SelectTrigger className="w-[220px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Landing Pages">Landing Pages</SelectItem>
          <SelectItem value="Other Sources">Other Sources</SelectItem>
        </SelectContent>
      </Select>
    </FormSection>
  );
}

// ─── Rank Form ───────────────────────────────────────────────────────────────

function RankForm({
  formState,
  toggleArrayItem,
}: {
  formState: any;
  toggleArrayItem: (field: any, value: string) => void;
}) {
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
          <label
            key={item.value}
            className="flex items-center gap-2 cursor-pointer"
          >
            <Checkbox
              checked={formState.rankMetrics.includes(item.value)}
              onCheckedChange={() =>
                toggleArrayItem("rankMetrics", item.value)
              }
            />
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
          "Domain Authority (MOZ)",
          "Domain Rating (AHREF)",
          "Number of Backlinks (AHREF)",
          "Referring Domains (AHREF)",
          "Mobile Speed",
          "Desktop Speed",
          "Core Web Vital (Mobile)",
          "Mobile Friendliness",
        ].map((label) => (
          <label
            key={label}
            className="flex items-center gap-2 cursor-not-allowed opacity-70"
          >
            <Checkbox checked={true} disabled />
            <span className="text-sm">{label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

// ─── Overview (Summary) Form ─────────────────────────────────────────────────

function OverviewForm({
  formState,
  setFormState,
}: {
  formState: any;
  setFormState: React.Dispatch<React.SetStateAction<any>>;
}) {
  return (
    <FormSection title="Metrics">
      <div className="grid grid-cols-3 gap-4">
        {[
          { value: "google_analytics", label: "Google Analytics" },
          {
            value: "google_search_console",
            label: "Google Search Console",
          },
          { value: "keyword_ranking", label: "Keyword Ranking" },
          {
            value: "ga_organic_traffic_breakup",
            label: "GA Organic Traffic Breakup",
          },
        ].map((item) => (
          <label
            key={item.value}
            className="flex items-center gap-2 cursor-pointer"
          >
            <input
              type="radio"
              name="summaryMetric"
              value={item.value}
              checked={formState.summaryMetric === item.value}
              onChange={(e) =>
                setFormState((p: any) => ({
                  ...p,
                  summaryMetric: e.target.value,
                }))
              }
              className="h-4 w-4 accent-primary"
            />
            <span className="text-sm">{item.label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

// ─── Duration & Order By ─────────────────────────────────────────────────────

function DurationOrderSection({
  formState,
  setFormState,
  isMonthly,
}: {
  formState: any;
  setFormState: React.Dispatch<React.SetStateAction<any>>;
  isMonthly: boolean;
}) {
  return (
    <div className="bg-white rounded-lg p-5">
      <div className="flex flex-wrap gap-12">
        {/* Duration */}
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">
            Duration
          </h3>
          <Label className="text-xs text-muted-foreground">
            Schedule & Interval{" "}
            <span className="text-destructive">*</span>
          </Label>
          <div className="flex gap-3 mt-2">
            <Select
              value={formState.schedule}
              onValueChange={(v) =>
                setFormState((p: any) => ({ ...p, schedule: v }))
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Weekly Schedule">
                  Weekly Schedule
                </SelectItem>
                <SelectItem value="Monthly Schedule">
                  Monthly Schedule
                </SelectItem>
              </SelectContent>
            </Select>

            {isMonthly ? (
              <Select
                value={formState.monthInterval}
                onValueChange={(v) =>
                  setFormState((p: any) => ({
                    ...p,
                    monthInterval: v,
                  }))
                }
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MONTH_INTERVALS.map((i) => (
                    <SelectItem key={i} value={i}>
                      {i}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Select
                value={formState.weekInterval}
                onValueChange={(v) =>
                  setFormState((p: any) => ({
                    ...p,
                    weekInterval: v,
                  }))
                }
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WEEK_INTERVALS.map((i) => (
                    <SelectItem key={i} value={i}>
                      {i}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Order By */}
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">
            Order By
          </h3>
          <Label className="text-xs text-muted-foreground">
            Date Sort <span className="text-destructive">*</span>
          </Label>
          <div className="mt-2">
            <Select
              value={formState.orderBy}
              onValueChange={(v) =>
                setFormState((p: any) => ({ ...p, orderBy: v }))
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORDER_BY_VALS.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Base Duration Section (monthly only) ────────────────────────────────────

function BaseDurationSection({
  formState,
  setFormState,
}: {
  formState: any;
  setFormState: React.Dispatch<React.SetStateAction<any>>;
}) {
  return (
    <div className="bg-white rounded-lg p-5">
      <div className="flex flex-wrap gap-12">
        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">
            Duration
          </h3>
          <Label className="text-xs text-muted-foreground">
            Monthly Interval{" "}
            <span className="text-destructive">*</span>
          </Label>
          <div className="mt-2">
            <Select
              value={formState.monthInterval}
              onValueChange={(v) =>
                setFormState((p: any) => ({
                  ...p,
                  monthInterval: v,
                }))
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MONTH_INTERVALS.map((i) => (
                  <SelectItem key={i} value={i}>
                    {i}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold mb-3 pb-2 border-b">
            Order By
          </h3>
          <Label className="text-xs text-muted-foreground">
            Date Sort <span className="text-destructive">*</span>
          </Label>
          <div className="mt-2">
            <Select
              value={formState.orderBy}
              onValueChange={(v) =>
                setFormState((p: any) => ({ ...p, orderBy: v }))
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORDER_BY_VALS.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Comparison Section ──────────────────────────────────────────────────────

function ComparisonSection({
  formState,
  toggleArrayItem,
}: {
  formState: any;
  toggleArrayItem: (field: any, value: string) => void;
}) {
  return (
    <FormSection title="Comparison">
      <div className="flex gap-6">
        {[
          { value: "number", label: "Change in Number" },
          { value: "percentage", label: "Change in Percentage" },
        ].map((item) => (
          <label
            key={item.value}
            className="flex items-center gap-2 cursor-pointer"
          >
            <Checkbox
              checked={formState.changeUnits.includes(item.value)}
              onCheckedChange={() =>
                toggleArrayItem("changeUnits", item.value)
              }
            />
            <span className="text-sm">{item.label}</span>
          </label>
        ))}
      </div>
    </FormSection>
  );
}

export default ConfigureSeoReportDialog;
