import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InfoHint, MetricHint } from "@/components/InfoHint";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  ArrowLeft,
  Loader2,
  ExternalLink,
  PenLine,
  CheckCircle2,
  AlertTriangle,
  Info,
  MousePointerClick,
  Search,
  Layers,
} from "lucide-react";

interface Finding {
  stance: "supports" | "against" | "neutral";
  title: string;
  detail: string;
}

interface SerpEntry {
  rank: number;
  domain: string;
  url: string;
  title: string;
  content_type: string;
  content_type_label: string;
  is_platform: boolean;
  is_non_rival: boolean;
  gaps_held: number;
  avg_rank: number;
  beats_us: number;
  we_beat: number;
  context_volume: number;
}

interface CompetitorContext {
  domain: string;
  rank_here: number;
  positions_here: number;
  is_non_rival: boolean;
  is_platform: boolean;
  gaps_held: number;
  avg_rank: number;
  beats_us: number;
  we_beat: number;
  search_volume: number;
}

interface GapDetail {
  seo_keyword_rank_id: number;
  keyword: string;
  platform: string;
  our_rank: number;
  our_url: string;
  search_volume: number;
  competitors_on_page_one: number;
  competing_domains: string[];
  platform_results: number;
  leader: { domain: string; rank: number; url: string; title: string };
  content_type: string;
  content_type_label: string;
  content_type_mix: { type: string; label: string; count: number }[];
  leader_content_type: string;
  has_ads: boolean;
  intent: string;
  intent_label: string;
  recommended_format: string;
  action: "create" | "optimise";
  estimated_clicks: number;
  bucket: "quick_win" | "strategic_bet" | "backlog";
  serp: SerpEntry[];
  competitors: CompetitorContext[];
  history: { date: string; rank: number }[];
  findings: Finding[];
  serp_features: {
    featured_snippet: boolean;
    knowledge_panel: boolean;
    ads: boolean;
    reviews: boolean;
  };
  domain_id: number;
  domain_name: string;
  domain_url: string;
}

const fmt = (n: number) => n.toLocaleString();

const BUCKET_LABEL: Record<string, string> = {
  quick_win: "Quick win",
  strategic_bet: "Strategic bet",
  backlog: "Backlog",
};

/** Our content-type vocabulary mapped onto the generator's article types, so
 *  Create Content opens on the format that actually wins this results page
 *  rather than defaulting to a blog post every time. */
const TYPE_TO_ARTICLE_TYPE: Record<string, string> = {
  guide: "guide",
  faq: "guide",
  comparison: "comparison",
  review: "comparison",
  article: "blog",
  news: "blog",
  docs: "technical",
  tool: "landing_page",
  product: "product_page",
  category: "services_page",
  data: "resource_page",
  homepage: "landing_page",
  video: "blog",
  other: "blog",
};

// Findings are plain bordered blocks on the app's muted tint, the same
// treatment every other panel uses. The stance is carried by the section
// heading and its icon rather than by a coloured card — tinting whole cards
// green and red is not a pattern used anywhere else in the product.
const CARD_CLS = "p-4 border border-border bg-muted/30";

export default function SeoContentGapDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [data, setData] = useState<GapDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generateOpen, setGenerateOpen] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setData((await apiClient.getSeoContentGapDetail(id)) as GapDetail);
    } catch (err: any) {
      setError(err?.message || "Could not load this keyword.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // Rank 0 means "not ranked", which on a chart would read as the best possible
  // position. Plotted as null so the line breaks instead of lying.
  const chartData = useMemo(
    () =>
      (data?.history ?? []).map((h) => ({
        date: h.date.slice(5),
        rank: h.rank > 0 ? h.rank : null,
      })),
    [data]
  );
  const everRanked = chartData.some((d) => d.rank !== null);

  const supports = data?.findings.filter((f) => f.stance === "supports") ?? [];
  const against = data?.findings.filter((f) => f.stance === "against") ?? [];
  const context = data?.findings.filter((f) => f.stance === "neutral") ?? [];

  const prefill = useMemo(() => {
    if (!data) return undefined;
    return {
      type: TYPE_TO_ARTICLE_TYPE[data.content_type] || "blog",
      title: data.keyword,
      targetKeywords: [data.keyword],
      wordCount: 1500,
      sourceType: "seo_content_gap",
      sourceId: data.seo_keyword_rank_id,
      sourceReference: `Content gap: ${data.keyword}`,
      priority: data.bucket === "backlog" ? "low" : "high",
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32">
        <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
        <span className="text-muted-foreground text-sm">Building the case...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 space-y-6">
        <Button variant="ghost" onClick={() => navigate("/seo-content-gaps")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to SEO Content Gaps
        </Button>
        <Card className="p-6 border border-border">
          <div className="flex flex-col items-center text-center py-16 gap-3">
            <div className="rounded-full bg-muted/50 p-3">
              <Search className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">Not a content gap</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {error ||
                "This keyword either has no stored results page, or you already hold a page-one position for it."}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Detail-view header, matching SeoOpportunityDetail and SeoKeywordDetail:
          an icon-only back button inline to the left of the title with a rule
          under the row. A full-width text button above a text-4xl title reads
          as a top-level page rather than a detail view. */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50 gap-4 flex-wrap">
        <div className="flex items-center gap-4 min-w-0">
          <Button
            variant="outline"
            size="icon"
            className="border-border/50 flex-shrink-0"
            onClick={() => navigate("/seo-content-gaps")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight">
                {data.keyword}
              </h1>
              <Badge
                variant={
                  data.bucket === "quick_win"
                    ? "default"
                    : data.bucket === "strategic_bet"
                    ? "secondary"
                    : "outline"
                }
              >
                {BUCKET_LABEL[data.bucket]}
              </Badge>
            </div>
            <p className="text-muted-foreground mt-0.5 text-sm">
              {data.domain_name} · {data.platform} ·{" "}
              {data.action === "create"
                ? "no page of yours ranks for this"
                : `your best page sits at position ${data.our_rank}`}
            </p>
          </div>
        </div>
        <Button onClick={() => setGenerateOpen(true)}>
          <PenLine className="h-4 w-4 mr-2" />
          Create Content
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Your Position</p>
              <p className="text-2xl font-bold mt-1 tabular-nums">
                {data.our_rank === 0 ? "—" : data.our_rank}
              </p>
            </div>
            <Search className="h-5 w-5 text-primary" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {data.our_rank === 0 ? "not in the top 30" : "page one starts at 10"}
          </p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Monthly Searches</p>
              <p className="text-2xl font-bold mt-1 tabular-nums">
                {fmt(data.search_volume)}
              </p>
            </div>
            <Layers className="h-5 w-5 text-secondary" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {data.competitors_on_page_one} competitors on page one
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
                    plain="Roughly how many extra visits a month this keyword could bring if you reached a realistic position."
                    formula="Search volume × published average click-through rate for the target position, minus what your current position earns. Target is position 5 if you already rank on page one, position 8 otherwise. Industry-average CTR, not this site's measured rates."
                  />
                </InfoHint>
              </p>
              <p className="text-2xl font-bold mt-1 tabular-nums">
                {data.estimated_clicks > 0 ? `+${fmt(data.estimated_clicks)}` : "—"}
              </p>
            </div>
            <MousePointerClick className="h-5 w-5 text-success" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">estimated, per month</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">What To Build</p>
              <p className="text-lg font-bold mt-1 leading-tight">
                {data.content_type_label}
              </p>
            </div>
            <PenLine className="h-5 w-5 text-destructive" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {data.intent_label} intent · {data.recommended_format.toLowerCase()}
          </p>
        </Card>
      </div>

      {/* The justification. Split three ways rather than presented as a single
          verdict — "201,000 searches" and "the tax authority holds #1" are both
          true, and which one wins is the user's call, not a rule's. */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Why this is a content gap</h2>
          <p className="text-sm text-muted-foreground mt-1">
            The evidence behind this keyword appearing on the list — including what argues
            against acting on it.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-3">
            <p className="text-sm font-medium text-success flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4" />
              The case for ({supports.length})
            </p>
            {supports.map((f, i) => (
              <Card key={i} className={CARD_CLS}>
                <p className="text-sm font-medium">{f.title}</p>
                <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
                  {f.detail}
                </p>
              </Card>
            ))}
          </div>

          <div className="space-y-3">
            {against.length > 0 && (
              <>
                <p className="text-sm font-medium text-destructive flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4" />
                  What argues against ({against.length})
                </p>
                {against.map((f, i) => (
                  <Card key={i} className={CARD_CLS}>
                    <p className="text-sm font-medium">{f.title}</p>
                    <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
                      {f.detail}
                    </p>
                  </Card>
                ))}
              </>
            )}

            {context.length > 0 && (
              <>
                <p className="text-sm font-medium text-muted-foreground flex items-center gap-1.5 pt-1">
                  <Info className="h-4 w-4" />
                  Worth knowing ({context.length})
                </p>
                {context.map((f, i) => (
                  <Card key={i} className={CARD_CLS}>
                    <p className="text-sm font-medium">{f.title}</p>
                    <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
                      {f.detail}
                    </p>
                  </Card>
                ))}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 border border-border lg:col-span-2">
          <h3 className="text-sm font-semibold mb-4">
            Your position over time
            <span className="font-normal text-muted-foreground ml-2">
              last {data.history.length} tracked days
            </span>
          </h3>
          {everRanked ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 15, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
                <XAxis
                  dataKey="date"
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  tickLine={{ stroke: "hsl(var(--border))" }}
                  minTickGap={24}
                />
                {/* Reversed: position 1 belongs at the top. */}
                <YAxis
                  reversed
                  domain={[1, "dataMax"]}
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={11}
                  width={40}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "var(--radius)",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
                  }}
                  labelStyle={{ fontWeight: 600, marginBottom: 4 }}
                  formatter={(v: any) => [v === null ? "Not ranked" : `#${v}`, "Position"]}
                />
                <Line
                  type="monotone"
                  dataKey="rank"
                  name="Position"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2.5}
                  dot={{ fill: "hsl(var(--primary))", r: chartData.length > 45 ? 2 : 3.5, strokeWidth: 0 }}
                  activeDot={{ r: 6, strokeWidth: 0 }}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex flex-col items-center justify-center text-center gap-2">
              <p className="text-sm text-muted-foreground">
                Never ranked in {data.history.length || "any"} days of tracking.
              </p>
              <p className="text-xs text-muted-foreground max-w-sm">
                A flat line at zero would read as position zero, so nothing is plotted. This is
                the strongest possible signal that no page of yours addresses this keyword.
              </p>
            </div>
          )}
        </Card>

        <Card className="p-6 border border-border space-y-3">
          <h3 className="text-sm font-semibold">Page one at a glance</h3>
          <div className="space-y-2">
            {data.content_type_mix.map((m) => (
              <div key={m.type} className="flex items-center gap-3">
                <span className="text-sm flex-1 min-w-0 truncate">{m.label}</span>
                <div className="h-1.5 rounded-full bg-muted overflow-hidden w-16">
                  <div
                    className="h-full rounded-full gradient-primary"
                    style={{
                      width: `${(m.count / data.content_type_mix[0].count) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-sm tabular-nums w-6 text-right text-muted-foreground">
                  {m.count}
                </span>
              </div>
            ))}
          </div>
          <div className="pt-2 border-t border-border space-y-1.5">
            {Object.entries({
              "Featured snippet": data.serp_features.featured_snippet,
              "Knowledge panel": data.serp_features.knowledge_panel,
              "Paid ads": data.serp_features.ads,
              "Review stars": data.serp_features.reviews,
            }).map(([label, present]) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className={present ? "text-foreground font-medium" : "text-muted-foreground"}>
                  {present ? "Yes" : "No"}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Who these domains are across the whole project, not just here. A rival
          sitting at #7 on this keyword while holding 36 of your others is a
          different problem from one that beat you once. */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Who you are up against</h2>
          <p className="text-sm text-muted-foreground mt-1">
            The domains holding page one here, and how much of the rest of this project each of
            them also takes from you.
          </p>
        </div>
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Competitor</TableHead>
                <TableHead className="w-[100px] text-right">Here</TableHead>
                <TableHead className="w-[130px] text-right">
                  <span className="inline-flex items-center gap-1.5">
                    Other Gaps
                    <InfoHint>
                      <MetricHint
                        title="Other Gaps"
                        plain="How many of this project's OTHER keywords this domain also takes from you."
                        formula="Tracked keywords, excluding the one on screen, where this domain holds a top-10 position and you are absent or at 11 or worse. A high number means a rival worth a strategy; a low one means they beat you here and nowhere else."
                      />
                    </InfoHint>
                  </span>
                </TableHead>
                <TableHead className="w-[110px] text-right">Their Avg</TableHead>
                <TableHead className="w-[150px] text-right">
                  <span className="inline-flex items-center gap-1.5">
                    Head To Head
                    <InfoHint>
                      <MetricHint
                        title="Head To Head"
                        plain="Across every tracked keyword where you both rank, who is higher."
                        formula="They beat you / you beat them, counted over all tracked keywords in this project. Keywords where you do not rank at all are excluded from both sides — those show up under Other Gaps instead."
                      />
                    </InfoHint>
                  </span>
                </TableHead>
                <TableHead className="w-[140px]">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.competitors.map((c) => (
                <TableRow key={c.domain} className="hover:bg-muted/30">
                  <TableCell className="font-medium">{c.domain}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    #{c.rank_here}
                    {c.positions_here > 1 && (
                      <span className="text-xs text-muted-foreground"> ×{c.positions_here}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {c.gaps_held > 0 ? (
                      <span className={c.gaps_held >= 10 ? "font-medium text-destructive" : ""}>
                        {fmt(c.gaps_held)}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">
                    {c.avg_rank > 0 ? `#${c.avg_rank}` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm tabular-nums">
                    {c.beats_us || c.we_beat ? (
                      <>
                        <span className="text-destructive">{c.beats_us}</span>
                        <span className="text-muted-foreground"> / </span>
                        <span className="text-success">{c.we_beat}</span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {c.is_non_rival && (
                      <Badge variant="outline" className="font-normal mr-1">
                        not a rival
                      </Badge>
                    )}
                    {c.is_platform && (
                      <Badge variant="outline" className="font-normal">
                        platform
                      </Badge>
                    )}
                    {!c.is_non_rival && !c.is_platform && c.gaps_held >= 10 && (
                      <Badge variant="destructive" className="font-normal">
                        serial threat
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground">
          "Other Gaps" and "Head To Head" are measured across this project's tracked keywords
          only — they describe what each domain takes from you, not everything it ranks for.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-baseline gap-2 flex-wrap">
          <h2 className="text-lg font-semibold">The results page you are entering</h2>
          <span className="text-sm text-muted-foreground">
            all {data.serp.length} stored positions
          </span>
        </div>
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[60px]">Pos</TableHead>
                <TableHead>Page</TableHead>
                <TableHead className="w-[170px]">Format</TableHead>
                <TableHead className="w-[190px]">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.serp.map((s) => (
                <TableRow
                  key={`${s.rank}-${s.url}`}
                  className="hover:bg-muted/30"
                >
                  <TableCell
                    className={`tabular-nums font-medium ${
                      s.rank > 10 ? "text-muted-foreground" : ""
                    }`}
                  >
                    {s.rank}
                  </TableCell>
                  <TableCell className="max-w-[520px]">
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium hover:underline flex items-center gap-1"
                    >
                      <span className="truncate">{s.domain}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0 text-muted-foreground" />
                    </a>
                    <div className="text-xs text-muted-foreground truncate">{s.title}</div>
                  </TableCell>
                  <TableCell className="text-sm">{s.content_type_label}</TableCell>
                  <TableCell>
                    {s.is_non_rival && (
                      <Badge variant="outline" className="font-normal mr-1">
                        not a rival
                      </Badge>
                    )}
                    {s.is_platform && (
                      <Badge variant="outline" className="font-normal">
                        platform
                      </Badge>
                    )}
                    {!s.is_non_rival && !s.is_platform && s.rank <= 10 && (
                      <span className="text-xs text-muted-foreground">winnable</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="text-xs text-muted-foreground">
          Captured on the last crawl of this keyword. "Not a rival" marks government, regulator
          and reference sites that hold their own subject matter; "platform" marks social and
          video results. Neither can be displaced by publishing a page, so the winnable
          positions are the ones without a label.
        </p>
      </div>

      <GenerateContentDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        existingContent={prefill}
      />
    </div>
  );
}
