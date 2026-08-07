import { useState, useEffect, useCallback, useMemo } from "react";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { InfoHint, MetricHint } from "@/components/InfoHint";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Loader2, Trophy, Globe, Users, Eye, AlertCircle } from "lucide-react";

interface Competitor {
  domain: string;
  share: number;
  appearances: number;
  avg_position: number;
  best_position: number | null;
  beats_us: number;
  we_beat: number;
  we_are_absent: number;
  is_tracked: boolean;
  is_non_rival: boolean;
}

interface SovResponse {
  our_domain: string;
  our_share: number;
  our_share_vs_rivals: number;
  our_position: number;
  competitors: Competitor[];
  untracked_rivals: Competitor[];
  summary: {
    keywords_analysed: number;
    keywords_with_volume: number;
    volume_covered: number;
    rival_domains_seen: number;
    our_appearances: number;
    tracked_competitors: number;
  };
  method: string;
}

const fmt = (n: number) => n.toLocaleString();

/** Horizontal share bar. Width is relative to the leader, not to 100 — at
 *  single-digit shares every bar would otherwise be an invisible sliver. */
const ShareBar = ({ value, max, us }: { value: number; max: number; us?: boolean }) => (
  <div className="h-1.5 rounded-full bg-muted overflow-hidden w-full">
    <div
      className={`h-full rounded-full ${us ? "gradient-primary" : "bg-secondary"}`}
      style={{ width: `${max > 0 ? Math.max((value / max) * 100, 2) : 0}%` }}
    />
  </div>
);

export default function SeoShareOfVoice() {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain ? String(selectedDomain.id) : "";

  const [data, setData] = useState<SovResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [rivalsOnly, setRivalsOnly] = useState(true);

  const load = useCallback(async () => {
    if (!activeDomainId) {
      setData(null);
      return;
    }
    setLoading(true);
    try {
      setData(
        (await apiClient.getSeoShareOfVoice({ domain_id: activeDomainId })) as SovResponse
      );
    } catch (err: any) {
      toast({
        title: "Could not load share of voice",
        description: err?.message || "Please try again.",
        variant: "destructive",
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [activeDomainId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const rows = useMemo(() => {
    if (!data) return [];
    return rivalsOnly ? data.competitors.filter((c) => !c.is_non_rival) : data.competitors;
  }, [data, rivalsOnly]);

  const maxShare = rows.length ? Math.max(rows[0].share, data?.our_share ?? 0) : 1;

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
        <p className="text-muted-foreground mt-2">
          How much of your tracked market's search results you actually own
        </p>
      </div>

      {!activeDomainId && (
        <div className="py-32 text-center text-muted-foreground">
          Select a domain to see its share of voice.
        </div>
      )}

      {activeDomainId && loading && (
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
          <span className="text-muted-foreground text-sm">Measuring visibility...</span>
        </div>
      )}

      {activeDomainId && !loading && data && data.summary.keywords_analysed === 0 && (
        <Card className="p-6 border border-border">
          <div className="flex flex-col items-center justify-center text-center py-16 gap-3">
            <div className="rounded-full bg-muted/50 p-3">
              <Globe className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No results pages stored yet</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Share of voice is measured from the full search results captured for each tracked
              keyword. Once this domain has keywords that have been crawled, its competitive
              picture appears here.
            </p>
          </div>
        </Card>
      )}

      {activeDomainId && !loading && data && data.summary.keywords_analysed > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5">
                    Your Share
                    <InfoHint>
                      <MetricHint
                        title="Your Share"
                        plain="How much of the visibility across your tracked keywords belongs to you, counting only genuine commercial rivals."
                        formula="Each domain scores search volume × a position weight, summed over every tracked keyword. Excludes search features, marketplaces and government sites — nobody outranks a tax authority on its own statute, so counting them would make the number advice-free. Position weights are published average click-through rates, not measured for this site."
                      />
                    </InfoHint>
                  </p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {data.our_share_vs_rivals}%
                  </p>
                </div>
                <Trophy className="h-5 w-5 text-primary" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {data.our_share}% of all results including non-rivals
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">League Position</p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">#{data.our_position}</p>
                </div>
                <Users className="h-5 w-5 text-secondary" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                of {fmt(data.summary.rival_domains_seen + 1)} domains seen
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">You Appear On</p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {fmt(data.summary.our_appearances)}
                  </p>
                </div>
                <Eye className="h-5 w-5 text-success" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                of {fmt(data.summary.keywords_analysed)} tracked searches
              </p>
            </Card>

            <Card className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Rival Domains</p>
                  <p className="text-2xl font-bold mt-1 tabular-nums">
                    {fmt(data.summary.rival_domains_seen)}
                  </p>
                </div>
                <Globe className="h-5 w-5 text-destructive" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {data.summary.tracked_competitors} tracked as competitors
              </p>
            </Card>
          </div>

          {data.untracked_rivals.length > 0 && (
            <Card className="p-6 border border-border">
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-warning/10 p-2 flex-shrink-0">
                  <AlertCircle className="h-5 w-5 text-warning" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold">
                    Rivals nobody has flagged
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    These domains take real visibility in your results but are not tracked as
                    competitors, so nothing in the product is watching them.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {data.untracked_rivals.map((c) => (
                      <Badge key={c.domain} variant="secondary" className="font-normal">
                        {c.domain}
                        <span className="ml-1.5 tabular-nums opacity-70">{c.share}%</span>
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}

          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <h2 className="text-lg font-semibold">Visibility league table</h2>
              <div className="flex items-center gap-2">
                <Switch id="rivalsOnly" checked={rivalsOnly} onCheckedChange={setRivalsOnly} />
                <Label htmlFor="rivalsOnly" className="cursor-pointer text-sm">
                  Commercial rivals only
                </Label>
              </div>
            </div>

            <div className="rounded-md border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">#</TableHead>
                    <TableHead>Domain</TableHead>
                    <TableHead className="w-[180px]">Share</TableHead>
                    <TableHead className="w-[110px] text-right">Appears On</TableHead>
                    <TableHead className="w-[100px] text-right">Avg Pos</TableHead>
                    <TableHead className="w-[190px]">
                      <span className="flex items-center gap-1.5">
                        Head to Head
                        <InfoHint>
                          <MetricHint
                            title="Head to Head"
                            plain="Across keywords where you both appear, who ranks higher."
                            formula="Beats you / you beat them, counted per keyword. 'Absent' counts keywords where they appear and you do not rank at all — those are the gaps, not losses."
                          />
                        </InfoHint>
                      </span>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {/* Our own row, pinned in place so the comparison is direct. */}
                  <TableRow className="bg-primary/5">
                    <TableCell className="tabular-nums font-medium">
                      {data.our_position}
                    </TableCell>
                    <TableCell className="font-medium">
                      {data.our_domain}
                      <Badge variant="secondary" className="ml-2">
                        You
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium tabular-nums w-12">
                          {data.our_share}%
                        </span>
                        <ShareBar value={data.our_share} max={maxShare} us />
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmt(data.summary.our_appearances)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      —
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">—</TableCell>
                  </TableRow>

                  {rows.map((c, i) => (
                    <TableRow key={c.domain}>
                      <TableCell className="tabular-nums text-muted-foreground">
                        {i + 1}
                      </TableCell>
                      <TableCell className="font-medium">
                        {c.domain}
                        {c.is_non_rival && (
                          <Badge variant="outline" className="ml-2 font-normal">
                            not a rival
                          </Badge>
                        )}
                        {c.is_tracked && (
                          <Badge variant="secondary" className="ml-2 font-normal">
                            tracked
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="text-sm tabular-nums w-12">{c.share}%</span>
                          <ShareBar value={c.share} max={maxShare} />
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmt(c.appearances)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {c.avg_position}
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="text-destructive tabular-nums">{c.beats_us}</span>
                        <span className="text-muted-foreground"> / </span>
                        <span className="text-success tabular-nums">{c.we_beat}</span>
                        {c.we_are_absent > 0 && (
                          <span className="text-muted-foreground">
                            {" "}
                            · {c.we_are_absent} absent
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <p className="text-xs text-muted-foreground">{data.method}</p>
          </div>
        </>
      )}
    </div>
  );
}
