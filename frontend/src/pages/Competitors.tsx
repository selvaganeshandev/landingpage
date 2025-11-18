import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimeFilter } from "@/components/TimeFilter";
import { TopBrandsList } from "@/components/TopBrandsList";
import { CompetitorHeatmap } from "@/components/CompetitorHeatmap";
import { useToast } from "@/hooks/use-toast";
import { useContentGeneration } from "@/hooks/useContentGeneration";
import { AddCompetitorDialog } from "@/components/AddCompetitorDialog";
import { PageLoader } from "@/components/PageLoader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  TrendingUp,
  TrendingDown,
  Target,
  FileText,
  Eye,
  MessageSquare,
  AlertCircle,
  Search,
  Sparkles
} from "lucide-react";
import { 
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  Cell,
  TooltipProps,
} from "recharts";
import type { LegendProps } from "recharts";
import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";

// Static data constants removed - all data now comes from APIs

type VisibilityLegendProps = LegendProps & {
  disabledBrands: string[];
  onToggle: (brand: string) => void;
};

const VisibilityLegend = ({ payload, disabledBrands, onToggle }: VisibilityLegendProps) => {
  if (!payload || !payload.length) return null;
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 mt-4 px-4">
      {payload.map((entry) => {
        const brand = String(entry.value);
        const active = !disabledBrands.includes(brand);
        return (
          <button
            key={brand}
            type="button"
            onClick={() => onToggle(brand)}
            className={`flex items-center gap-2 rounded-full px-3 py-1 transition border text-xs ${
              active ? 'border-primary/60 bg-primary/5 text-foreground' : 'border-border text-muted-foreground'
            }`}
          >
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: entry.color, opacity: active ? 1 : 0.35 }}
            />
            <span className="font-medium">{brand}</span>
          </button>
        );
      })}
    </div>
  );
};

type VisibilityTooltipProps = TooltipProps<ValueType, NameType> & {
  disabledBrands: string[];
};

const VisibilityTooltip = ({ active, label, payload, disabledBrands }: VisibilityTooltipProps) => {
  if (!active || !payload || payload.length === 0) return null;
  const filtered = payload.filter((entry) => !disabledBrands.includes(String(entry.name)));
  if (!filtered.length) return null;
  const yourBrandEntry = filtered.find((entry) => String(entry.name).toLowerCase() === 'your brand');
  const competitorEntries = filtered.filter((entry) => entry !== yourBrandEntry);
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2 shadow-lg">
      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">{label}</p>
      <div className="space-y-1.5">
        {yourBrandEntry && (
          <div className="pb-2 border-b border-border/50">
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: yourBrandEntry.color }} />
              <span className="font-semibold">{yourBrandEntry.name}</span>
              <span className="text-muted-foreground">{yourBrandEntry.value} mentions</span>
            </div>
          </div>
        )}
        {competitorEntries.map((entry) => (
          <div key={`${entry.name}-${entry.color}`} className="flex items-center gap-2 text-sm">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="font-medium">{entry.name}</span>
            <span className="text-muted-foreground">{entry.value} mentions</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const Competitors = () => {
  const navigate = useNavigate();
  const [timePeriod, setTimePeriod] = useState("7");
  const [selectedTab, setSelectedTab] = useState("overview");
  const [selectedLLM, setSelectedLLM] = useState("all");
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const [addCompetitorDialogOpen, setAddCompetitorDialogOpen] = useState(false);
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [loadedDomainId, setLoadedDomainId] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [sovLatest, setSovLatest] = useState<any>(null);
  const [sovSeries, setSovSeries] = useState<any[]>([]);
  const [platformMap, setPlatformMap] = useState<Record<string, Array<{ brand: string; mentions: number }>>>({});
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [heatmapPlatforms, setHeatmapPlatforms] = useState<string[]>([]);
  const [topBrands, setTopBrands] = useState<any[]>([]);
  const [promptCards, setPromptCards] = useState<any[]>([]);
  const [competitiveMetrics, setCompetitiveMetrics] = useState<any[]>([]);
  const [competitiveInsights, setCompetitiveInsights] = useState<any[]>([]);
  const [answerGapData, setAnswerGapData] = useState<any[]>([]);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [hasLoadedData, setHasLoadedData] = useState(false);
  const [disabledBrands, setDisabledBrands] = useState<string[]>([]);
  const [strengthDisabledBrands, setStrengthDisabledBrands] = useState<string[]>([]);

  const sortHeatmapRows = (rows: any[], platformKeys: string[]) => {
    if (!Array.isArray(rows) || rows.length === 0) return rows;
    return [...rows].sort((a, b) => {
      if (a.isYou && !b.isYou) return -1;
      if (!a.isYou && b.isYou) return 1;
      const sumPlatforms = (row: any) =>
        platformKeys.reduce((acc, plat) => acc + Number(row.platforms?.[plat] ?? 0), 0);
      return sumPlatforms(b) - sumPlatforms(a);
    });
  };

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your competitor analysis report is being generated...",
    });
  };
  
  // Sync domainId from selectedDomain (Zustand store) or server when domain changes
  useEffect(() => {
    if (!user) return;

    // Priority 1: Use selectedDomain from Zustand store (most up-to-date when user changes domain)
    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        // Clear all state when domain changes to prevent flash of old data
        setCompetitors([]);
        setSovLatest(null);
        setSovSeries([]);
        setPlatformMap({});
        setHeatmap([]);
        setHeatmapPlatforms([]);
        setTopBrands([]);
        setPromptCards([]);
        setCompetitiveMetrics([]);
        setCompetitiveInsights([]);
        setAnswerGapData([]);
        setHasLoadedData(false);
        setIsPageLoading(true);
        setLoadedDomainId(null); // Clear loaded domain ID to indicate we haven't loaded this domain yet

        setDomainId(newDomainId);
        return;
      }
    }
    
    // Priority 2: Fallback to localStorage (synced with server)
    const serverActiveDomain = getActiveDomainId(user);
    const serverDomainId = serverActiveDomain || '';
    
    if (serverDomainId !== domainId) {
      setDomainId(serverDomainId);
    }
  }, [user, selectedDomain?.id, domainId]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) {
        setHasLoadedData(false);
        setIsPageLoading(true);
        return;
      }
      setHasLoadedData(false);
      setIsPageLoading(true);
      try {
        // Load main competitor data first
        const platformParam = selectedLLM !== 'all' ? selectedLLM : undefined;
        const [list, latest, byDomain, compPromptAnalytics, snapshotHistory, heatmapResponse] = await Promise.all([
          apiClient.getEngineCompetitors({ domain_id: domainId, platform: platformParam }),
          apiClient.getShareOfVoiceLatestEngine({ domain_id: domainId }),
          apiClient.getShareOfVoiceByDomain({ domain_id: domainId, days: Number(timePeriod) }),
          apiClient.getCompetitorPromptAnalyticsEngine({ domain_id: domainId }),
          apiClient.getCompetitorMetricSnapshots({ domain_id: domainId, days: Number(timePeriod), platform: platformParam }),
          apiClient.getCompetitorHeatmap({ domain_id: domainId, days: Number(timePeriod), platform: platformParam }),
        ] as any);

        // Load competitive analysis APIs separately with better error handling
        setIsLoadingAnalysis(true);
        let strengthAnalysis: any = undefined;
        let insights: any = undefined;
        let gaps: any = undefined;

        try {
          console.log('🔵 API CALL: Loading competitive strength analysis for domain:', domainId, 'platform:', selectedLLM);
          const url = `/competitors/competitive-strength-analysis?domain_id=${domainId}${selectedLLM !== 'all' ? `&platform=${selectedLLM}` : ''}`;
          console.log('🔵 API URL:', url);
          strengthAnalysis = await apiClient.getCompetitiveStrengthAnalysis({
            domain_id: domainId,
            platform: selectedLLM !== 'all' ? selectedLLM : undefined
          });
          console.log('✅ Competitive strength analysis response:', strengthAnalysis);
          console.log('✅ Response type:', typeof strengthAnalysis, 'Is array:', Array.isArray(strengthAnalysis));
          // If API returns empty array, that's valid - we'll show empty state
          if (Array.isArray(strengthAnalysis) && strengthAnalysis.length === 0) {
            console.log('ℹ️ API returned empty array - will show empty state');
          }
        } catch (e: any) {
          console.error('❌ Failed to load competitive strength analysis:', e);
          console.error('❌ Error message:', e?.message);
          console.error('❌ Error stack:', e?.stack);
          // Don't set to empty array - leave as undefined to indicate API call failed
          strengthAnalysis = undefined;
        }

        try {
          console.log('🔵 API CALL: Loading competitive insights for domain:', domainId, 'platform:', selectedLLM);
          const url = `/competitors/competitive-insights?domain_id=${domainId}${selectedLLM !== 'all' ? `&platform=${selectedLLM}` : ''}`;
          console.log('🔵 API URL:', url);
          insights = await apiClient.getCompetitiveInsights({
            domain_id: domainId,
            platform: selectedLLM !== 'all' ? selectedLLM : undefined
          });
          console.log('✅ Competitive insights response:', insights);
          console.log('✅ Response type:', typeof insights, 'Is array:', Array.isArray(insights));
          // If API returns empty array, that's valid - we'll show empty state
          if (Array.isArray(insights) && insights.length === 0) {
            console.log('ℹ️ API returned empty array - will show empty state');
          }
        } catch (e: any) {
          console.error('❌ Failed to load competitive insights:', e);
          console.error('❌ Error message:', e?.message);
          console.error('❌ Error stack:', e?.stack);
          // Don't set to empty array - leave as undefined to indicate API call failed
          insights = undefined;
        }

        try {
          console.log('🔵 API CALL: Loading answer gap analysis for domain:', domainId, 'platform:', selectedLLM);
          const url = `/competitors/answer-gap-analysis?domain_id=${domainId}${selectedLLM !== 'all' ? `&platform=${selectedLLM}` : ''}`;
          console.log('🔵 API URL:', url);
          gaps = await apiClient.getAnswerGapAnalysis({
            domain_id: domainId,
            platform: selectedLLM !== 'all' ? selectedLLM : undefined
          });
          console.log('✅ Answer gap analysis response:', gaps);
          console.log('✅ Response type:', typeof gaps, 'Is array:', Array.isArray(gaps));
          // If API returns empty array, that's valid - we'll show empty state
          if (Array.isArray(gaps) && gaps.length === 0) {
            console.log('ℹ️ API returned empty array - will show empty state');
          }
        } catch (e: any) {
          console.error('❌ Failed to load answer gap analysis:', e);
          console.error('❌ Error message:', e?.message);
          console.error('❌ Error stack:', e?.stack);
          // Don't set to empty array - leave as undefined to indicate API call failed
          gaps = undefined;
        }
        
        setIsLoadingAnalysis(false);
        setHasLoadedData(true);
        setLoadedDomainId(domainId); // Mark this domain as loaded
        // Normalize competitor list
        const mapped = (Array.isArray(list) ? list : list?.results || []).map((c: any, idx: number) => {
          // Convert sentiment_score from -1 to 1 range to 0-100 percentage for display
          // Formula: (sentiment + 1) * 50 to normalize -1..1 to 0..100
          // Special case: -1 (no data) or 0 with no mentions should show 0%
          const rawSentiment = Number(c.sentiment_score || 0);
          const totalMentions = Number(c.total_mentions || 0);
          let sentimentPercent = 0;
          if (rawSentiment === -1 || (rawSentiment === 0 && totalMentions === 0)) {
            sentimentPercent = 0; // No data or unmentioned
          } else {
            sentimentPercent = Math.round((rawSentiment + 1) * 50);
          }
          
          return {
            id: c.id,
            name: c.name,
            url: c.url || (c.domain_name || '').toLowerCase(),
            mentions: c.total_mentions || 0,
            citations: c.total_citations || 0,
            visibility: Math.round(Number(c.visibility_score || 0)),
            sentiment: sentimentPercent,
            averagePosition: Number(c.average_position || 0),
            shareOfVoice: Math.round(Number(c.share_of_voice_percentage || 0)),
            trend: Number(c.trend_percentage || 0),
            color: idx === 0 ? 'hsl(var(--primary))' : idx === 1 ? 'hsl(var(--chart-2))' : 'hsl(var(--chart-3))',
            isYou: false, // Competitors are never "you" - "Your Brand" is shown separately in ShareOfVoice
          };
        });
        setCompetitors(mapped.length ? mapped : []);

        setSovLatest(latest);

        // Prepare Share of Voice rows for fallback/platform data
        const rows = Array.isArray(byDomain) ? byDomain : byDomain?.results || [];
        const groupedRows: Record<string, Record<string, number>> = {};
        rows.forEach((r: any) => {
          const month = r.timestamp || r.date || '';
          if (!groupedRows[month]) groupedRows[month] = {};
          const brand = r.competitor?.name || 'Your Brand';
          groupedRows[month][brand] = (groupedRows[month][brand] || 0) + (Number(r.mention_count || 0));
        });
        const months = Object.keys(groupedRows).sort();
        const fallbackBrandSet = new Set<string>();
        Object.values(groupedRows).forEach(m => Object.keys(m).forEach(b => fallbackBrandSet.add(b)));
        const fallbackBrands = Array.from(fallbackBrandSet);

        // Build mention history series from snapshots if available
        const snapshotRows = Array.isArray(snapshotHistory) ? snapshotHistory : snapshotHistory?.results || [];
        const apiHeatmapRows = Array.isArray(heatmapResponse?.rows) ? heatmapResponse.rows : [];
        const apiHeatmapPlatforms = Array.isArray(heatmapResponse?.platforms) ? heatmapResponse.platforms : [];
        const yourBrandLabel = 'Your Brand';
        if (snapshotRows.length > 0) {
          const groupedSnapshots: Record<string, Record<string, number>> = {};
          const brandNames = new Set<string>();
          snapshotRows.forEach((snap: any) => {
            const timestamp = snap.timestamp || snap.created_at || '';
            const label = timestamp ? new Date(timestamp).toISOString().split('T')[0] : `Snapshot ${snap.id}`;
            const brand = snap.competitor_name || snap.competitor?.name || 'Unknown';
            brandNames.add(brand);
            if (!groupedSnapshots[label]) groupedSnapshots[label] = {};
            groupedSnapshots[label][brand] = Number(snap.total_mentions || 0);
          });
          const sortedLabels = Object.keys(groupedSnapshots).sort();
          const brands = Array.from(brandNames);
          let series = sortedLabels.map((label) => {
            const entry: Record<string, number | string> = { month: label };
            brands.forEach((brand) => {
              entry[brand] = groupedSnapshots[label]?.[brand] || 0;
            });
            return entry;
          });
          let effectiveBrands = [...brands];
          if (!brands.includes(yourBrandLabel) && fallbackBrands.includes(yourBrandLabel)) {
            series = series.map((entry) => ({
              ...entry,
              [yourBrandLabel]: groupedRows[String(entry.month)]?.[yourBrandLabel] || 0,
            }));
            effectiveBrands.push(yourBrandLabel);
          }
          setSovSeries(series);
          setDisabledBrands((prev) => prev.filter((brand) => effectiveBrands.includes(brand)));
        } else {
          const fallbackSeries = months.map(m => {
            const entry: any = { month: m };
            fallbackBrands.forEach(brand => {
              entry[brand] = groupedRows[m]?.[brand] || 0;
            });
            return entry;
          });
          setSovSeries(fallbackSeries);
          setDisabledBrands((prev) => prev.filter((brand) => fallbackBrands.includes(brand)));
        }

        // Platform-specific share for latest month using byDomain rows
        const lastDate = months[months.length - 1];
        const latestRows = rows.filter((r: any) => (r.timestamp || r.date) === lastDate);
        const platMap: Record<string, Record<string, number>> = {};
        latestRows.forEach((r: any) => {
          const plat = r.platform || 'Overall';
          const brand = r.competitor?.name || 'Your Brand';
          if (!platMap[plat]) platMap[plat] = {};
          platMap[plat][brand] = (platMap[plat][brand] || 0) + (Number(r.mention_count || 0));
        });
        const platOut: Record<string, Array<{ brand: string; mentions: number }>> = {};
        Object.entries(platMap).forEach(([plat, counts]) => {
          platOut[plat] = Object.entries(counts)
            .map(([brand, m]) => ({ brand, mentions: Number(m) }))
            .sort((a, b) => b.mentions - a.mentions)
            .slice(0, 3);
        });
        setPlatformMap(platOut);

        // Map brand names to URLs for favicon usage
        const competitorUrlMap: Record<string, string> = {};
        mapped.forEach((comp: any) => {
          if (comp.name && comp.url) {
            competitorUrlMap[comp.name] = comp.url;
          }
        });
        if (selectedDomain?.name && selectedDomain?.url) {
          competitorUrlMap[selectedDomain.name] = selectedDomain.url;
        }
        competitorUrlMap[yourBrandLabel] = selectedDomain?.url || competitorUrlMap[yourBrandLabel] || '';

        // Heatmap: competitor (row) vs platform percentage
        const fallbackPlatforms = Object.keys(platOut);
        const brandsSet = new Set<string>();
        Object.values(platOut).forEach(arr => arr.forEach(e => brandsSet.add(e.brand)));
        const brands = Array.from(brandsSet);
        const fallbackHeatmap = brands.map((brand) => ({
          competitor: brand,
          platforms: fallbackPlatforms.reduce((acc: any, p) => {
            const total = (platOut[p] || []).reduce((s, e) => s + e.mentions, 0) || 1;
            const item = (platOut[p] || []).find((entry) => entry.brand === brand);
            acc[p] = item ? Number(((item.mentions / total) * 100).toFixed(1)) : 0;
            return acc;
          }, {}),
          isYou: brand.toLowerCase().includes('your'),
          url: competitorUrlMap[brand] || '',
        }));

        if (apiHeatmapRows.length && apiHeatmapPlatforms.length) {
          const formattedHeatmap = apiHeatmapRows.map((row: any) => ({
            competitor: row.name,
            platforms: apiHeatmapPlatforms.reduce((acc: any, platform: string) => {
              acc[platform] = Number(row.platforms?.[platform] ?? 0);
              return acc;
            }, {}),
            isYou: Boolean(row.isYou),
            url: row.url || competitorUrlMap[row.name] || (row.isYou ? competitorUrlMap[yourBrandLabel] : ''),
          }));
          setHeatmap(sortHeatmapRows(formattedHeatmap, apiHeatmapPlatforms));
          setHeatmapPlatforms(apiHeatmapPlatforms);
        } else {
          setHeatmap(sortHeatmapRows(fallbackHeatmap, fallbackPlatforms));
          setHeatmapPlatforms(fallbackPlatforms);
        }

        // Top brands list from latest snapshot
        const tb = (latest?.players || []).map((p: any) => ({
          name: p?.competitor?.name || 'Your Brand',
          url: '',
          mentions: p?.mention_count || 0,
          percentage: Number(p?.share_percentage || 0),
          isYou: !p?.competitor,
        })).sort((a: any, b: any) => b.mentions - a.mentions).slice(0, 5);
        if (tb.length) setTopBrands(tb);

        // Build dynamic prompt performance cards
        const displayBrands = (mapped.length ? mapped : [])
          .sort((a: any, b: any) => (b.isYou ? 1 : 0) - (a.isYou ? 1 : 0))
          .slice(0, 3)
          .map((c: any) => c.name);

        const compPromptRows = Array.isArray(compPromptAnalytics) ? compPromptAnalytics : compPromptAnalytics?.results || [];
        const pmap: Record<string, { counts: Record<string, number>; total: number }> = {};
        compPromptRows.forEach((row: any) => {
          const promptText = row?.prompt?.prompt || row?.prompt_text || `Prompt #${row?.prompt_id || ''}`;
          const brand = row?.competitor?.name || 'Your Brand';
          const count = Number(row?.mention_count || (row?.is_mentioned ? 1 : 0));
          if (!pmap[promptText]) pmap[promptText] = { counts: {}, total: 0 };
          pmap[promptText].counts[brand] = (pmap[promptText].counts[brand] || 0) + count;
          pmap[promptText].total += count;
        });
        const cards = Object.entries(pmap)
          .sort((a, b) => b[1].total - a[1].total)
          .map(([promptText, v], idx) => {
          const countsForDisplay = displayBrands.map((b) => v.counts[b] || 0);
          const winnerIdx = countsForDisplay.reduce((mi, val, i, arr) => (val > arr[mi] ? i : mi), 0);
          return {
            id: idx + 1,
            prompt: promptText,
            brands: displayBrands,
            counts: countsForDisplay,
            total: v.total,
            winner: displayBrands[winnerIdx],
          };
        });
        if (cards.length) setPromptCards(cards);

        // Set competitive strength analysis data - ALWAYS use API response (even if empty)
        if (strengthAnalysis !== undefined && strengthAnalysis !== null) {
          if (Array.isArray(strengthAnalysis)) {
            setCompetitiveMetrics(strengthAnalysis);
            console.log('✅ Competitive strength analysis loaded:', strengthAnalysis.length, 'metrics', strengthAnalysis);
          } else {
            console.warn('⚠️ Competitive strength analysis API returned non-array data:', strengthAnalysis);
            setCompetitiveMetrics([]);
          }
        } else {
          // API call failed - set to empty array (no fallback)
          console.warn('⚠️ Competitive strength analysis API call failed');
          setCompetitiveMetrics([]);
        }

        // Set competitive insights - ALWAYS use API response (even if empty)
        if (insights !== undefined && insights !== null) {
          if (Array.isArray(insights)) {
            setCompetitiveInsights(insights);
            console.log('✅ Competitive insights loaded:', insights.length, 'insights', insights);
          } else {
            console.warn('⚠️ Competitive insights API returned non-array data:', insights);
            setCompetitiveInsights([]);
          }
        } else {
          // API call failed - set to empty array (no fallback)
          console.warn('⚠️ Competitive insights API call failed');
          setCompetitiveInsights([]);
        }

        // Set answer gap data - ALWAYS use API response (even if empty)
        if (gaps !== undefined && gaps !== null) {
          if (Array.isArray(gaps)) {
            setAnswerGapData(gaps);
            console.log('✅ Answer gap analysis loaded:', gaps.length, 'gaps', gaps);
          } else {
            console.warn('⚠️ Answer gap analysis API returned non-array data:', gaps);
            setAnswerGapData([]);
          }
        } else {
          // API call failed - set to empty array (no fallback)
          console.warn('⚠️ Answer gap analysis API call failed');
          setAnswerGapData([]);
        }
      } catch (e: any) {
        toast({ title: 'Failed to load competitors', description: String(e.message || e), variant: 'destructive' });
        setHasLoadedData(true);
        setLoadedDomainId(domainId); // Mark as loaded even on error to stop infinite loading
      } finally {
        setIsPageLoading(false);
      }
    };
    void load();
  }, [domainId, timePeriod, selectedLLM]); // Removed selectedDomain?.url and selectedDomain?.name to prevent infinite loop

  const handleAddCompetitor = () => {
    setAddCompetitorDialogOpen(true);
  };

  const handleAddCompetitorSubmit = async (competitorData: any) => {
    if (!domainId) {
      toast({
        title: "Error",
        description: "No domain selected. Please select a domain first.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Ensure URL has protocol
      let websiteUrl = competitorData.website.trim();
      if (!websiteUrl.startsWith('http://') && !websiteUrl.startsWith('https://')) {
        websiteUrl = `https://${websiteUrl}`;
      }

      const payload = {
        domain: domainId,
        name: competitorData.name.trim(),
        url: websiteUrl,
      };

      const response = await apiClient.createCompetitor(payload);
      
      toast({
        title: "Competitor Added",
        description: `"${competitorData.name}" has been added to tracking. Analysis will begin shortly.`,
      });

      // Refresh the competitor list by reloading the main data
      // The useEffect will automatically reload all data when domainId changes
      // For immediate refresh, we'll reload just the competitor list
      try {
        const list = await apiClient.getEngineCompetitors({ domain_id: domainId });
        if (list && Array.isArray(list)) {
          const mapped = list.map((c: any) => {
            // Convert sentiment_score from -1 to 1 range to 0-100 percentage for display
            // Special case: -1 (no data) or 0 with no mentions should show 0%
            const rawSentiment = Number(c.sentiment_score || 0);
            const totalMentions = Number(c.total_mentions || 0);
            let sentimentPercent = 0;
            if (rawSentiment === -1 || (rawSentiment === 0 && totalMentions === 0)) {
              sentimentPercent = 0; // No data or unmentioned
            } else {
              sentimentPercent = Math.round((rawSentiment + 1) * 50);
            }
            
            return {
              id: c.id,
              name: c.name || 'Unknown',
              url: c.url || '',
              mentions: c.total_mentions || 0,
              visibility: Number(c.visibility_score || 0),
              sentiment: sentimentPercent,
              avgPosition: Number(c.average_position || 0),
              shareOfVoice: Number(c.share_of_voice_percentage || 0),
              trend: Number(c.trend_percentage || 0),
              isYou: false,
            };
          });
          setCompetitors(mapped);
        }
      } catch (e: any) {
        console.error('Failed to refresh competitors list:', e);
        // Don't show error toast here - the competitor was already added successfully
      }

      setAddCompetitorDialogOpen(false);
    } catch (error: any) {
      console.error('Failed to add competitor:', error);
      toast({
        title: "Failed to Add Competitor",
        description: error?.message || "An error occurred while adding the competitor. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleGenerateForGap = (gap: typeof answerGapData[0]) => {
    navigateToContentGeneration({
      topic: gap.query,
      keywords: gap.query.toLowerCase().split(' '),
      source: `Answer Gap - Competitor: ${gap.competitor}`,
      priority: gap.opportunity as any,
      articleType: "guide"
    });
  };

  const heatmapData = heatmap;

  // Show loading during initial load or when switching domains
  // Keep showing loader until we've loaded data for the current domain
  if (isPageLoading || !hasLoadedData || loadedDomainId !== domainId) {
    return <PageLoader sidebarOpen />;
  }

  // Check if all competitor details are showing zero values
  const allCompetitorsHaveZeroData = competitors.length > 0 && competitors.every(c => 
    c.mentions === 0 && 
    c.citations === 0 && 
    c.visibility === 0 && 
    c.shareOfVoice === 0 && 
    c.sentiment === 0
  );

  // Check if filtering by platform returns no data or only zero values
  // Also check if all competitors have zero data (even without filter)
  const hasNoDataForPlatform = (selectedLLM !== 'all' && (
    (competitors.length === 0 || competitors.every(c => c.mentions === 0 && c.citations === 0)) &&
    competitiveMetrics.length === 0 &&
    heatmap.length === 0 &&
    answerGapData.length === 0
  )) || allCompetitorsHaveZeroData;

  // Show empty state when filtering by platform returns no data or all competitors have zero data
  if (hasNoDataForPlatform) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground tracking-tight">Competitors</h1>
            <p className="text-muted-foreground mt-1">
              Track and analyze competitor performance across AI platforms
            </p>
          </div>
        </div>

        {/* Empty state for filtered platform with no data */}
        <div className="flex flex-col items-center justify-center py-32 space-y-6">
          <div className="w-24 h-24 rounded-full bg-muted/30 flex items-center justify-center mb-4">
            <Search className="h-12 w-12 text-muted-foreground" />
          </div>
          <h3 className="text-2xl font-semibold text-foreground">No Data for {selectedLLM !== 'all' ? selectedLLM.charAt(0).toUpperCase() + selectedLLM.slice(1) : 'Competitors'}</h3>
          <p className="text-sm text-muted-foreground max-w-md text-center">
            {selectedLLM !== 'all'
              ? "There is no competitor data available for the selected LLM platform. This could mean competitors haven't been analyzed on this platform yet, or no mentions were found."
              : "All competitor details are showing zero values. This could mean competitors haven't been analyzed yet, or no mentions were found."
            }
          </p>
          <div className="flex gap-3 mt-6">
            <Button
              onClick={() => setSelectedLLM('all')}
              className="gradient-primary"
              size="lg"
            >
              Clear Filter & View All LLMs
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Competitor Analysis</h1>
            <p className="text-muted-foreground mt-2">
              Compare your brand's AI visibility against competitors
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleExportReport}>
              <FileText className="h-4 w-4 mr-2" />
              Export Report
            </Button>
            <Button onClick={handleAddCompetitor} className="gradient-primary shadow-md shadow-primary/20">
              <Plus className="h-4 w-4 mr-2" />
              Add Competitor
            </Button>
          </div>
        </div>

        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
          {competitors.length > 0 && (
            <div className="flex items-center justify-between gap-4 mb-6">
              <TabsList className="bg-muted/50 p-1 border border-border">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Overview</TabsTrigger>
                <TabsTrigger value="prompts" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Prompts</TabsTrigger>
                <TabsTrigger value="answer-gap" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Answer Gap</TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-3">
                <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
                <Select value={selectedLLM} onValueChange={setSelectedLLM}>
                  <SelectTrigger className="w-[200px]">
                    <SelectValue placeholder="All LLMs" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All LLMs</SelectItem>
                    <SelectItem value="chatgpt">ChatGPT</SelectItem>
                    <SelectItem value="claude">Claude</SelectItem>
                    <SelectItem value="gemini">Gemini</SelectItem>
                    <SelectItem value="perplexity">Perplexity</SelectItem>
                    <SelectItem value="grok">Grok</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6 mt-0">

            {/* Competitor Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {competitors.length > 0 ? (
                competitors.map((competitor, idx) => (
                <Card
                  key={competitor.id}
                  className={`p-6 transition-all duration-300 backdrop-blur-sm bg-card/80 ${
                    competitor.isYou
                      ? 'border-2 border-primary'
                      : 'border border-border hover:border-primary'
                  }`}
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-xl font-semibold font-inter">{competitor.name}</h3>
                          {competitor.isYou && (
                            <Badge variant="default" className="gradient-primary border-0">You</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{competitor.url}</p>
                      </div>
                      <div className="w-12 h-12 rounded-xl gradient-primary shadow-glow flex items-center justify-center font-bold text-white text-lg font-inter">
                        #{idx + 1}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Mentions</p>
                        <p className="text-xl font-bold font-inter">{competitor.mentions}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Citations</p>
                        <p className="text-xl font-bold font-inter">{competitor.citations || 0}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Share</p>
                        <p className="text-xl font-bold font-inter">{competitor.shareOfVoice}%</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Avg Position</p>
                        <p className="text-lg font-bold font-inter">{competitor.averagePosition?.toFixed(1) || '0.0'}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Visibility</p>
                        <p className="text-lg font-bold font-inter">{competitor.visibility}%</p>
                        <Progress value={competitor.visibility} className="h-1.5 mt-1" />
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Sentiment</p>
                        <p className="text-lg font-bold font-inter">{competitor.sentiment}%</p>
                        <Progress value={competitor.sentiment} className="h-1.5 mt-1" />
                      </div>
                    </div>

                    <div className="pt-3 border-t flex items-center justify-between">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">Trend</span>
                        <div className="flex items-center gap-1">
                          {competitor.trend > 0 ? (
                            <TrendingUp className="h-4 w-4 text-success" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-destructive" />
                          )}
                          <span className={`font-semibold ${competitor.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                            {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
                          </span>
                        </div>
                      </div>
                      {!competitor.isYou && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-primary"
                          onClick={() => navigate(`/competitors/${competitor.id}`)}
                        >
                          View Details →
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
                ))
              ) : (
                <div className="col-span-full flex flex-col items-center justify-center py-32 space-y-4">
                  <div className="w-20 h-20 rounded-full bg-muted/30 flex items-center justify-center mb-2">
                    <Target className="h-10 w-10 text-muted-foreground" />
                  </div>
                  <h3 className="text-xl font-semibold text-foreground">No Competitors Added Yet</h3>
                  <p className="text-sm text-muted-foreground max-w-md text-center">
                    Track your competitors to see how your brand performs against them in AI search results.
                  </p>
                  <Button
                    onClick={() => setAddCompetitorDialogOpen(true)}
                    className="mt-4 gradient-primary"
                    size="lg"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Your Competitor
                  </Button>
                </div>
              )}
            </div>

            {/* Show rest of content only if there are competitors */}
            {competitors.length > 0 && (
              <>
            {/* Brand Visibility Over Time */}
            <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
              <div className="space-y-6">
                <div className="pb-4 border-b border-border">
                  <h3 className="text-lg font-semibold font-inter">
                    Brand Visibility Over Time
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Track how often each brand is mentioned by AI providers
                  </p>
                </div>
                {sovSeries.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                        <LineChart data={sovSeries}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                          <Tooltip 
                            content={(props) => (
                              <VisibilityTooltip {...props} disabledBrands={disabledBrands} />
                            )}
                          />
                          <Legend content={(props: LegendProps) => (
                            <VisibilityLegend
                              {...props}
                              disabledBrands={disabledBrands}
                              onToggle={(brand) => {
                                setDisabledBrands((prev) =>
                                  prev.includes(brand)
                                    ? prev.filter((b) => b !== brand)
                                    : [...prev, brand]
                                );
                              }}
                            />
                          )} />
                          {Object.keys(sovSeries[0] || {})
                            .filter(k => k !== 'month')
                            .map((brandKey, idx) => {
                              const disabled = disabledBrands.includes(brandKey);
                              const colors = [
                                "hsl(var(--primary))",
                                "hsl(var(--chart-2))",
                                "hsl(var(--chart-3))",
                                "hsl(var(--chart-4))",
                                "hsl(var(--chart-5))",
                                "#FF6B6B",
                                "#4ECDC4",
                              ];
                              const color = colors[idx % colors.length];
                              return (
                                <Line 
                                  key={brandKey}
                                  type="monotone" 
                                  dataKey={brandKey}
                                  name={brandKey}
                                  stroke={color}
                                  strokeWidth={2.5}
                                  strokeOpacity={disabled ? 0.25 : 1}
                                  strokeDasharray={disabled ? "6 6" : undefined}
                                  dot={
                                    disabled
                                      ? { r: 0 }
                                      : { fill: "hsl(var(--background))", stroke: color, strokeWidth: 2, r: 4 }
                                  }
                                  activeDot={
                                    disabled
                                      ? false
                                      : { r: 6, strokeWidth: 3, stroke: color, fill: "hsl(var(--background))" }
                                  }
                                />
                              );
                            })}
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-64">
                    <p className="text-sm text-muted-foreground">No mention history data available yet.</p>
                  </div>
                )}
              </div>
            </Card>

            {/* Heatmap full width */}
            <CompetitorHeatmap 
              data={heatmapData} 
              platforms={heatmapPlatforms.length ? heatmapPlatforms : Object.keys(platformMap)} 
            />

            {/* Competitive Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80 flex flex-col">
                <div className="space-y-1 mb-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold font-inter">Competitive Strength Analysis</h3>
                    {isLoadingAnalysis && (
                      <span className="text-xs text-muted-foreground">Loading...</span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Radar view of how each brand scores across visibility, sentiment, position, coverage, and growth.
                  </p>
                </div>
                {competitiveMetrics && competitiveMetrics.length > 0 ? (
                  <div className="flex-1 min-h-[360px] flex items-center justify-center">
                    <div className="w-full max-w-[520px] translate-y-[-20px]">
                      <ResponsiveContainer width="100%" height={420}>
                        <RadarChart data={competitiveMetrics} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                      <PolarGrid stroke="hsl(var(--border))" />
                      <PolarAngleAxis
                        dataKey="metric"
                        stroke="hsl(var(--muted-foreground))"
                        fontSize={12}
                      />
                      <PolarRadiusAxis
                        angle={90}
                        domain={[0, 100]}
                        stroke="hsl(var(--muted-foreground))"
                        tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Legend
                        content={(props: LegendProps) => (
                          <VisibilityLegend
                            {...props}
                            disabledBrands={strengthDisabledBrands}
                            onToggle={(brand) => {
                              setStrengthDisabledBrands((prev) =>
                                prev.includes(brand)
                                  ? prev.filter((b) => b !== brand)
                                  : [...prev, brand]
                              );
                            }}
                          />
                        )}
                      />
                      {competitiveMetrics[0] && Object.keys(competitiveMetrics[0]).filter(k => k !== 'metric').map((brandKey, idx) => {
                        const colors = [
                          { stroke: "hsl(var(--primary))", fill: "hsl(var(--primary))", opacity: 0.3 },
                          { stroke: "hsl(var(--chart-2))", fill: "hsl(var(--chart-2))", opacity: 0.2 },
                          { stroke: "hsl(var(--chart-3))", fill: "hsl(var(--chart-3))", opacity: 0.2 },
                        ];
                        const color = colors[idx] || colors[0];
                        // Format brand name for display
                        const displayName = brandKey.charAt(0).toUpperCase() + brandKey.slice(1).replace(/([A-Z])/g, ' $1');
                        const disabled = strengthDisabledBrands.includes(displayName);
                        return (
                          <Radar
                            key={brandKey}
                            name={displayName}
                            dataKey={brandKey}
                            stroke={color.stroke}
                            fill={color.fill}
                            fillOpacity={disabled ? 0.05 : color.opacity}
                            strokeWidth={idx === 0 ? 2 : 1.5}
                            strokeOpacity={disabled ? 0.25 : 1}
                            strokeDasharray={disabled ? "6 6" : undefined}
                          />
                        );
                      })}
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 space-y-2">
                    <p className="text-sm text-muted-foreground">No competitive strength data available yet.</p>
                    <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                  </div>
                )}
              </Card>

              <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
                <div className="space-y-1 mb-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold font-inter">Competitive Intelligence</h3>
                    {isLoadingAnalysis && (
                      <span className="text-xs text-muted-foreground">Loading...</span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    AI-generated callouts that summarize notable wins, risks, and opportunities for your domain.
                  </p>
                </div>
                <div className="space-y-3">
                  {competitiveInsights && competitiveInsights.length > 0 ? (
                    <>
                      {competitiveInsights.slice(0, 2).map((insight: any, idx: number) => (
                        <div key={idx} className="p-5 rounded-xl transition-all duration-300 border border-border hover:border-primary bg-card/50">
                          <div className="flex items-start gap-3">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md ${
                              insight.type === 'success' ? 'bg-success/10 text-success' :
                              insight.type === 'warning' ? 'bg-warning/10 text-warning' :
                              'gradient-primary text-white'
                            }`}>
                              <Target className="h-5 w-5" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="font-semibold text-sm font-inter">{insight.title}</h4>
                                <Badge variant={insight.impact === 'high' ? 'default' : 'secondary'} className="text-xs">
                                  {insight.impact}
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground leading-relaxed">{insight.description}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                      {competitiveInsights.length > 2 && (
                        <div className="flex justify-end pt-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-primary hover:text-primary/80"
                            onClick={() => {
                              // TODO: Implement view all insights modal or navigate to insights page
                              toast({
                                title: "View All Insights",
                                description: `Showing ${competitiveInsights.length} total insights`,
                              });
                            }}
                          >
                            View All ({competitiveInsights.length})
                          </Button>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 space-y-2">
                      <p className="text-sm text-muted-foreground">No competitive insights available yet.</p>
                      <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>
              </>
            )}
          </TabsContent>

          {/* Prompts Tab */}
          <TabsContent value="prompts" className="space-y-6 mt-6">
            <Card className="p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border">
                  <div>
                    <h3 className="text-lg font-semibold font-inter">Prompt Performance Analysis</h3>
                    <p className="text-sm text-muted-foreground mt-1">See which prompts competitors dominate</p>
                  </div>
                  <Badge variant="secondary">
                    <MessageSquare className="h-3 w-3 mr-1" />
                    {promptCards.length} Prompts Tracked
                  </Badge>
                </div>

                <div className="space-y-4">
                  {promptCards.length > 0 ? (
                    promptCards.map((prompt: any) => (
                    <Card key={prompt.id} className="p-5 transition-all duration-300 border border-border hover:border-primary">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium mb-2">{prompt.prompt}</h4>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Eye className="h-4 w-4" />
                              <span>{(prompt.total || (Array.isArray(prompt.counts) ? prompt.counts.reduce((s:number,v:number)=>s+v,0) : 0))} total mentions</span>
                              <span className="text-xs">•</span>
                              {prompt.winner && (
                                <Badge variant="outline" className="text-xs">
                                  Winner: {prompt.winner}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {(prompt.brands || []).map((brand: string, idx: number) => (
                            <div key={brand} className="space-y-2">
                              <div className="flex items-center justify-between text-sm">
                                <span className="font-medium">{brand}</span>
                                <span className="text-muted-foreground">{(prompt.counts && prompt.counts[idx]) || 0} mentions</span>
                              </div>
                              <Progress value={(() => {
                                const val = (prompt.counts && prompt.counts[idx]) || 0;
                                const denom = prompt.total || (Array.isArray(prompt.counts) ? prompt.counts.reduce((s:number,v:number)=>s+v,0) : 0);
                                return denom > 0 ? (val / denom) * 100 : 0;
                              })()} className="h-2" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </Card>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 space-y-2">
                      <p className="text-sm text-muted-foreground">No prompt performance data available yet.</p>
                      <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Answer Gap Tab */}
          <TabsContent value="answer-gap" className="space-y-6 mt-6">
            <Card className="p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border">
                  <div>
                    <h3 className="text-lg font-semibold font-inter">Answer Gap Analysis</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Queries where competitors appear but you don't
                    </p>
                  </div>
                  <Badge variant="destructive">
                    <AlertCircle className="h-3 w-3 mr-1" />
                    {answerGapData && answerGapData.length > 0 ? answerGapData.length : 0} Gaps Identified
                  </Badge>
                </div>

                <div className="space-y-4">
                  {answerGapData && answerGapData.length > 0 ? (
                    answerGapData.map((gap: any) => (
                      <Card key={gap.id} className="p-5 transition-all duration-300 border border-border hover:border-primary">
                        <div className="space-y-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <Search className="h-4 w-4 text-muted-foreground" />
                                <h4 className="font-medium">{gap.query}</h4>
                              </div>
                              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                <span>{gap.competitor} has {gap.mentions} mentions</span>
                                <span className="text-xs">•</span>
                                <span>You have {gap.yourMentions} mentions</span>
                              </div>
                            </div>
                            <Badge 
                              variant={gap.opportunity === 'high' ? 'destructive' : 'secondary'}
                              className="ml-4"
                            >
                              {gap.opportunity} opportunity
                            </Badge>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            <span className="text-xs text-muted-foreground">Platforms:</span>
                            {gap.platforms && gap.platforms.map((platform: string) => (
                              <Badge key={platform} variant="outline" className="text-xs">
                                {platform}
                              </Badge>
                            ))}
                          </div>

                          <div className="pt-3 border-t">
                            <Button 
                              variant="default" 
                              size="sm" 
                              className="w-full gradient-primary"
                              onClick={() => handleGenerateForGap(gap)}
                            >
                              <Sparkles className="h-3 w-3 mr-1" />
                              Generate Content
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 space-y-2">
                      <p className="text-sm text-muted-foreground">No answer gaps identified yet.</p>
                      <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Add Competitor Dialog */}
      <AddCompetitorDialog
        open={addCompetitorDialogOpen}
        onOpenChange={setAddCompetitorDialogOpen}
        onAdd={handleAddCompetitorSubmit}
      />
    </div>
  );
};

export default Competitors;
