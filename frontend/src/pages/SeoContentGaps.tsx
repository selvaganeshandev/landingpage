import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InfoHint, MetricHint } from "@/components/InfoHint";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Loader2,
  Download,
  FileSearch,
  Zap,
  Rocket,
  MousePointerClick,
  ExternalLink,
  Search,
} from "lucide-react";

interface GapLeader {
  domain: string;
  rank: number;
  url: string;
  title: string;
}

interface TypeMix {
  type: string;
  label: string;
  count: number;
}

interface GapRow {
  seo_keyword_rank_id: number;
  keyword: string;
  platform: string;
  our_rank: number;
  our_url: string;
  search_volume: number;
  competitors_on_page_one: number;
  competing_domains: string[];
  platform_results: number;
  leader: GapLeader;
  content_type: string;
  content_type_label: string;
  content_type_mix: TypeMix[];
  leader_content_type: string;
  has_ads: boolean;
  intent: string;
  intent_label: string;
  recommended_format: string;
  action: "create" | "optimise";
  estimated_clicks: number;
  bucket: "quick_win" | "strategic_bet" | "backlog";
  score: number;
}

interface GapSummary {
  gaps: number;
  keywords_analysed: number;
  keywords_without_serp: number;
  total_tracked: number;
  estimated_clicks: number;
  to_create: number;
  to_optimise: number;
  quick_wins: number;
  strategic_bets: number;
  backlog: number;
  by_content_type: { key: string; label: string; count: number }[];
  by_intent: { key: string; label: string; count: number }[];
  top_competitors: { domain: string; keywords: number }[];
}

interface GapResponse {
  domain_id: number;
  domain_name: string;
  summary: GapSummary;
  count: number;
  page: number;
  page_size: number;
  results: GapRow[];
}

const fmt = (n: number) => n.toLocaleString();

const BUCKET_LABEL: Record<string, string> = {
  quick_win: "Quick win",
  strategic_bet: "Strategic bet",
  backlog: "Backlog",
};

/** Quick wins and strategic bets are the two things worth acting on, so they
 *  carry colour; backlog stays quiet on purpose. */
const bucketVariant = (b: string) =>
  b === "quick_win" ? "default" : b === "strategic_bet" ? "secondary" : "outline";

export default function SeoContentGaps() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";

  const [data, setData] = useState<GapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(1);

  const [bucket, setBucket] = useState("all");
  const [intent, setIntent] = useState("all");
  const [contentType, setContentType] = useState("all");
  const [action, setAction] = useState("all");
  const [search, setSearch] = useState("");
  // The search box hits the server, so it is debounced rather than fired on
  // every keystroke.
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setSearchTerm(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  // Any filter change invalidates the page number — staying on page 4 of a
  // result set that now has one page shows an empty table.
  useEffect(() => {
    setPage(1);
  }, [bucket, intent, contentType, action, searchTerm, activeDomainId]);

  const load = useCallback(async () => {
    if (!activeDomainId) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      setData(
        (await apiClient.getSeoContentGaps({
          domain_id: activeDomainId,
          bucket,
          intent,
          content_type: contentType,
          action,
          search: searchTerm,
          page,
        })) as GapResponse
      );
    } catch (err: any) {
      toast({
        title: "Could not load content gaps",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [activeDomainId, bucket, intent, contentType, action, searchTerm, page, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleExport = async () => {
    if (!activeDomainId) return;
    setExporting(true);
    try {
      await apiClient.exportSeoContentGaps({
        domain_id: activeDomainId,
        filename: `seo-content-gaps-${(selectedDomain?.name || "project")
          .replace(/[^a-z0-9]+/gi, "-")
          .toLowerCase()}`,
      });
      toast({
        title: "Export ready",
        description: "Summary, every gap row, and the breakdowns — five sheets.",
      });
    } catch (err: any) {
      toast({
        title: "Export failed",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
    } finally {
      setExporting(false);
    }
  };

  const summary = data?.summary;
  const totalPages = data ? Math.max(1, Math.ceil(data.count / data.page_size)) : 1;

  // Coverage matters enough to state on the page: most projects carry keywords
  // imported without a stored results page, and those cannot be analysed.
  const coverage = useMemo(() => {
    if (!summary || !summary.total_tracked) return 100;
    return Math.round((summary.keywords_analysed / summary.total_tracked) * 100);
  }, [summary]);

  const filtersActive =
    bucket !== "all" || intent !== "all" || contentType !== "all" ||
    action !== "all" || searchTerm !== "";

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">SEO Content Gaps</h1>
          <p className="text-muted-foreground mt-2">
            Keywords where a competitor holds page one and you do not — and what they win with
          </p>
        </div>
        {activeDomainId && summary && summary.gaps > 0 && (
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            Export
          </Button>
        )}
      </div>

      {!activeDomainId && (
        <div className="py-32 text-center text-muted-foreground">
          Select a domain to see its content gaps.
        </div>
      )}

      {activeDomainId && loading && !data && (
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <span className="text-muted-foreground text-sm">Comparing results pages...</span>
        </div>
      )}

      {activeDomainId && !loading && summary && summary.keywords_analysed === 0 && (
        <Card className="p-6 border border-border">
          <div className="flex flex-col items-center justify-center text-center py-16 gap-3">
            <div className="rounded-full bg-muted/50 p-3">
              <FileSearch className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No results pages stored yet</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Content gaps are read from the full search results captured on each crawl. None of
              this domain's {fmt(summary.total_tracked)} tracked keywords has one yet, so there is
              nothing to compare against.
            </p>
          </div>
        </Card>
      )}

      {activeDomainId && summary && summary.keywords_analysed > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Content Gaps
                    <InfoHint>
                      <MetricHint
                        title="Content Gaps"
                        plain="Tracked keywords where at least one competitor holds a page-one position and you do not."
                        formula="Counted where your position is 0 (not ranked) or 11 or worse, AND a competitor sits in the top 10. Only keywords with a stored results page can be judged — see Coverage."
                      />
                    </InfoHint>
                  </p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">{fmt(summary.gaps)}</p>
                </div>
                <FileSearch className="h-5 w-5 text-primary" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {fmt(summary.to_create)} to create · {fmt(summary.to_optimise)} to improve
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Quick Wins
                    <InfoHint>
                      <MetricHint
                        title="Quick Wins"
                        plain="Gaps where you already rank somewhere in the top 30 — a page that needs improving, not writing."
                        formula="Gaps with a current position between 11 and 30. The page already exists and Google already knows it; closing these is editing work rather than a build."
                      />
                    </InfoHint>
                  </p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {fmt(summary.quick_wins)}
                  </p>
                </div>
                <Zap className="h-5 w-5 text-success" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                already ranking, position 11–30
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Strategic Bets
                    <InfoHint>
                      <MetricHint
                        title="Strategic Bets"
                        plain="High-volume keywords you do not rank for at all — worth building a page for from nothing."
                        formula="Gaps with no current ranking and at least 1,000 monthly searches. These take longer than quick wins and are where the volume is."
                      />
                    </InfoHint>
                  </p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {fmt(summary.strategic_bets)}
                  </p>
                </div>
                <Rocket className="h-5 w-5 text-secondary" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {fmt(summary.backlog)} more in backlog
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Clicks At Stake
                    <InfoHint>
                      <MetricHint
                        title="Clicks At Stake"
                        plain="Roughly how many extra visits a month closing every gap could bring."
                        formula="Search volume × the published average click-through rate for the target position, minus what the current position earns. Target is position 5 where you already rank on page one, position 8 otherwise. An estimate for ordering work — it uses industry-average CTR, not this site's measured rates."
                      />
                    </InfoHint>
                  </p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {fmt(summary.estimated_clicks)}
                  </p>
                </div>
                <MousePointerClick className="h-5 w-5 text-destructive" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">estimated extra clicks / month</p>
            </Card>
          </div>

          {/* Coverage is stated rather than buried: imported keywords carry no
              stored results page, so on most projects this analyses a slice.
              Showing gap counts without it would read as the whole project. */}
          {summary.keywords_without_serp > 0 && (
            <Card className="p-4 border border-border bg-muted/30">
              <p className="text-sm text-muted-foreground">
                Analysed{" "}
                <span className="font-medium text-foreground tabular-nums">
                  {fmt(summary.keywords_analysed)}
                </span>{" "}
                of{" "}
                <span className="font-medium text-foreground tabular-nums">
                  {fmt(summary.total_tracked)}
                </span>{" "}
                tracked keywords ({coverage}%).{" "}
                {fmt(summary.keywords_without_serp)} have no stored results page yet — they are
                excluded from every number above and will appear once they have been crawled.
              </p>
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="p-6 border border-border space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-1.5">
                What wins these searches
                <InfoHint>
                  <MetricHint
                    title="Winning content type"
                    plain="The kind of page that dominates page one for your gap keywords."
                    formula="Every page-one result is classified from its URL and title — a guide, a comparison, a product page and so on — and the most common type on each results page wins the vote. Classified by URL structure, so an unusual site may be mislabelled."
                  />
                </InfoHint>
              </h3>
              {summary.by_content_type.slice(0, 6).map((t) => (
                <div key={t.key} className="flex items-center gap-3">
                  <span className="text-sm flex-1 min-w-0 truncate">{t.label}</span>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden w-24">
                    <div
                      className="h-full rounded-full gradient-primary"
                      style={{
                        width: `${Math.max(
                          (t.count / summary.by_content_type[0].count) * 100,
                          3
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm tabular-nums w-10 text-right text-muted-foreground">
                    {t.count}
                  </span>
                </div>
              ))}
            </Card>

            <Card className="p-6 border border-border space-y-3">
              <h3 className="text-sm font-semibold flex items-center gap-1.5">
                Where they sit in the journey
                <InfoHint>
                  <MetricHint
                    title="Search intent"
                    plain="Which stage of the buying journey each gap keyword belongs to."
                    formula="Read from the keyword's own wording first (buy, best, how to). When the keyword gives no signal, the format Google chose to rank decides it — product pages mean decision, guides mean awareness. Paid ads on the results page are treated as a commercial signal."
                  />
                </InfoHint>
              </h3>
              {summary.by_intent.map((t) => (
                <div key={t.key} className="flex items-center gap-3">
                  <span className="text-sm flex-1 min-w-0 truncate">{t.label}</span>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden w-24">
                    <div
                      className="h-full rounded-full bg-secondary"
                      style={{
                        width: `${Math.max(
                          (t.count / summary.by_intent[0].count) * 100,
                          3
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-sm tabular-nums w-10 text-right text-muted-foreground">
                    {t.count}
                  </span>
                </div>
              ))}
            </Card>

            <Card className="p-6 border border-border space-y-2">
              <h3 className="text-sm font-semibold">Who is taking these</h3>
              {summary.top_competitors.slice(0, 8).map((c, i) => (
                <div
                  key={c.domain}
                  className="flex items-center gap-3 py-1 border-b border-border/50 last:border-0"
                >
                  <span className="text-xs text-muted-foreground tabular-nums w-4 flex-shrink-0">
                    {i + 1}
                  </span>
                  <span className="text-sm truncate flex-1 min-w-0">{c.domain}</span>
                  <span className="text-sm tabular-nums text-muted-foreground flex-shrink-0">
                    {c.keywords}
                  </span>
                </div>
              ))}
            </Card>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <h2 className="text-lg font-semibold">
                Gap keywords
                {filtersActive && data && (
                  <span className="text-sm font-normal text-muted-foreground ml-2 tabular-nums">
                    {fmt(data.count)} of {fmt(summary.gaps)}
                  </span>
                )}
              </h2>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search keyword or domain"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-8 w-[220px]"
                  />
                </div>
                <Select value={bucket} onValueChange={setBucket}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All priorities</SelectItem>
                    <SelectItem value="quick_win">Quick wins</SelectItem>
                    <SelectItem value="strategic_bet">Strategic bets</SelectItem>
                    <SelectItem value="backlog">Backlog</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={intent} onValueChange={setIntent}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Intent" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All intents</SelectItem>
                    {summary.by_intent.map((t) => (
                      <SelectItem key={t.key} value={t.key}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={contentType} onValueChange={setContentType}>
                  <SelectTrigger className="w-[170px]">
                    <SelectValue placeholder="Format" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All formats</SelectItem>
                    {summary.by_content_type.map((t) => (
                      <SelectItem key={t.key} value={t.key}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={action} onValueChange={setAction}>
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="Action" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Any action</SelectItem>
                    <SelectItem value="create">Create new</SelectItem>
                    <SelectItem value="optimise">Improve existing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="rounded-md border border-border relative">
              {loading && (
                <div className="absolute inset-0 z-10 flex items-center justify-center rounded-md bg-background/80 backdrop-blur-sm">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Keyword</TableHead>
                    <TableHead className="w-[90px] text-right">Our Pos</TableHead>
                    <TableHead className="w-[100px] text-right">Volume</TableHead>
                    <TableHead className="w-[130px]">Intent</TableHead>
                    <TableHead className="w-[170px]">
                      <span className="flex items-center gap-1.5">
                        Winning Format
                        <InfoHint>
                          <MetricHint
                            title="Winning Format"
                            plain="The kind of page most of page one uses for this keyword."
                            formula="All ten page-one results are classified and the most common type shown. The count beside it is how many of the ten share that format — a high count means the format is settled, a low one means the results page is mixed."
                          />
                        </InfoHint>
                      </span>
                    </TableHead>
                    <TableHead>Leading Competitor</TableHead>
                    <TableHead className="w-[130px]">Priority</TableHead>
                    <TableHead className="w-[110px] text-right">Clicks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data && data.results.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                        No gaps match these filters.
                      </TableCell>
                    </TableRow>
                  )}
                  {data?.results.map((r) => {
                    const dominant = r.content_type_mix.find(
                      (m) => m.type === r.content_type
                    );
                    return (
                      <TableRow key={r.seo_keyword_rank_id} className="hover:bg-muted/30">
                        <TableCell className="font-medium max-w-[280px]">
                          <button
                            type="button"
                            onClick={() => navigate(`/seo-content-gaps/${r.seo_keyword_rank_id}`)}
                            className="truncate text-left hover:text-primary hover:underline w-full"
                          >
                            {r.keyword}
                          </button>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {r.platform}
                            {r.has_ads && " · ads"}
                            {r.platform_results > 0 &&
                              ` · ${r.platform_results} social/video results`}
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {r.our_rank === 0 ? (
                            <span className="text-muted-foreground">—</span>
                          ) : (
                            r.our_rank
                          )}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {fmt(r.search_volume)}
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{r.intent_label}</div>
                          <div className="text-xs text-muted-foreground truncate max-w-[120px]">
                            {r.recommended_format}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{r.content_type_label}</div>
                          {dominant && (
                            <div className="text-xs text-muted-foreground">
                              {dominant.count} of {r.competitors_on_page_one} results
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="max-w-[240px]">
                          <a
                            href={r.leader.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm hover:underline flex items-center gap-1 truncate"
                          >
                            <span className="truncate">{r.leader.domain}</span>
                            <ExternalLink className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
                          </a>
                          <div className="text-xs text-muted-foreground truncate">
                            #{r.leader.rank} · {r.leader.title}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={bucketVariant(r.bucket)} className="font-normal">
                            {BUCKET_LABEL[r.bucket]}
                          </Badge>
                          <div className="text-xs text-muted-foreground mt-1">
                            {r.action === "create" ? "create new" : "improve existing"}
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {r.estimated_clicks > 0 ? (
                            `+${fmt(r.estimated_clicks)}`
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {data && totalPages > 1 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground tabular-nums">
                  Page {data.page} of {totalPages} · {fmt(data.count)} keywords
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1 || loading}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages || loading}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}

            <p className="text-xs text-muted-foreground">
              A gap is a tracked keyword where a competitor holds a top-10 position and you sit at
              11 or worse, or do not rank at all. Formats are classified from URL structure and
              page titles; intent from the keyword, falling back to what the results page contains.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
