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
  Cell
} from "recharts";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";

// Static data constants removed - all data now comes from APIs

const Competitors = () => {
  const navigate = useNavigate();
  const [timePeriod, setTimePeriod] = useState("90");
  const [selectedTab, setSelectedTab] = useState("overview");
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const [addCompetitorDialogOpen, setAddCompetitorDialogOpen] = useState(false);
  const { user } = useAuth();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [sovLatest, setSovLatest] = useState<any>(null);
  const [sovSeries, setSovSeries] = useState<any[]>([]);
  const [platformMap, setPlatformMap] = useState<Record<string, Array<{ brand: string; mentions: number }>>>({});
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [topBrands, setTopBrands] = useState<any[]>([]);
  const [promptCards, setPromptCards] = useState<any[]>([]);
  const [competitiveMetrics, setCompetitiveMetrics] = useState<any[]>([]);
  const [competitiveInsights, setCompetitiveInsights] = useState<any[]>([]);
  const [answerGapData, setAnswerGapData] = useState<any[]>([]);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your competitor analysis report is being generated...",
    });
  };
  useEffect(() => {
    if (!user) return;
    // Use unified helper to get active domain ID (from localStorage, synced with server)
    const id = getActiveDomainId(user);
    if (id) setDomainId(id);
  }, [user]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      try {
        // Load main competitor data first
        const [list, latest, byDomain, compPromptAnalytics] = await Promise.all([
          apiClient.getEngineCompetitors({ domain_id: domainId }),
          apiClient.getShareOfVoiceLatestEngine({ domain_id: domainId }),
          apiClient.getShareOfVoiceByDomain({ domain_id: domainId, days: Number(timePeriod) }),
          apiClient.getCompetitorPromptAnalyticsEngine({ domain_id: domainId }),
        ] as any);

        // Load competitive analysis APIs separately with better error handling
        setIsLoadingAnalysis(true);
        let strengthAnalysis: any = undefined;
        let insights: any = undefined;
        let gaps: any = undefined;

        try {
          console.log('🔵 API CALL: Loading competitive strength analysis for domain:', domainId);
          const url = `/competitors/competitive-strength-analysis?domain_id=${domainId}`;
          console.log('🔵 API URL:', url);
          strengthAnalysis = await apiClient.getCompetitiveStrengthAnalysis({ domain_id: domainId });
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
          console.log('🔵 API CALL: Loading competitive insights for domain:', domainId);
          const url = `/competitors/competitive-insights?domain_id=${domainId}`;
          console.log('🔵 API URL:', url);
          insights = await apiClient.getCompetitiveInsights({ domain_id: domainId });
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
          console.log('🔵 API CALL: Loading answer gap analysis for domain:', domainId);
          const url = `/competitors/answer-gap-analysis?domain_id=${domainId}`;
          console.log('🔵 API URL:', url);
          gaps = await apiClient.getAnswerGapAnalysis({ domain_id: domainId });
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

        // Normalize competitor list
        const mapped = (Array.isArray(list) ? list : list?.results || []).map((c: any, idx: number) => {
          // Convert sentiment_score from -1 to 1 range to 0-100 percentage for display
          // Formula: (sentiment + 1) * 50 to normalize -1..1 to 0..100
          const rawSentiment = Number(c.sentiment_score || 0);
          const sentimentPercent = Math.round((rawSentiment + 1) * 50);
          
          return {
            id: c.id,
            name: c.name,
            url: c.url || (c.domain_name || '').toLowerCase(),
            mentions: c.total_mentions || 0,
            visibility: Math.round(Number(c.visibility_score || 0)),
            sentiment: sentimentPercent,
            avgPosition: Number(c.average_position || 0).toFixed ? Number(c.average_position).toFixed(1) : (c.average_position || 0),
            shareOfVoice: Math.round(Number(c.share_of_voice_percentage || 0)),
            trend: Number(c.trend_percentage || 0),
            color: idx === 0 ? 'hsl(var(--primary))' : idx === 1 ? 'hsl(var(--chart-2))' : 'hsl(var(--chart-3))',
            isYou: false, // Competitors are never "you" - "Your Brand" is shown separately in ShareOfVoice
          };
        });
        setCompetitors(mapped.length ? mapped : []);

        setSovLatest(latest);

        // Build mention history series from SoV by_domain (use mention_count)
        const rows = Array.isArray(byDomain) ? byDomain : byDomain?.results || [];
        const grouped: Record<string, Record<string, number>> = {};
        rows.forEach((r: any) => {
          const month = r.timestamp || r.date || '';
          if (!grouped[month]) grouped[month] = {};
          const brand = r.competitor?.name || 'Your Brand';
          grouped[month][brand] = (grouped[month][brand] || 0) + (Number(r.mention_count || 0));
        });
        const months = Object.keys(grouped).sort();
        const brands = new Set<string>();
        Object.values(grouped).forEach(m => Object.keys(m).forEach(b => brands.add(b)));
        const brandArray = Array.from(brands);
        
        // Build series dynamically based on actual brands
        const series = months.map(m => {
          const entry: any = { month: m };
          brandArray.forEach(brand => {
            entry[brand] = grouped[m][brand] || 0;
          });
          return entry;
        });
        setSovSeries(series);

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

        // Heatmap: competitor (row) vs platform percentage
        const platforms = Object.keys(platOut);
        const brandsSet = new Set<string>();
        Object.values(platOut).forEach(arr => arr.forEach(e => brandsSet.add(e.brand)));
        const brandsArr = Array.from(brandsSet);
        const heatArr = brandsArr.map(brand => ({
          competitor: brand,
          platforms: platforms.reduce((acc: any, p) => {
            const total = (platOut[p] || []).reduce((s, e) => s + e.mentions, 0) || 1;
            const item = (platOut[p] || []).find(e => e.brand === brand);
            acc[p] = item ? Number(((item.mentions / total) * 100).toFixed(1)) : 0;
            return acc;
          }, {}),
          isYou: brand.toLowerCase().includes('your')
        }));
        setHeatmap(heatArr);

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
      }
    };
    void load();
  }, [domainId, timePeriod]);

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
            const rawSentiment = Number(c.sentiment_score || 0);
            const sentimentPercent = Math.round((rawSentiment + 1) * 50);
            
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

  return (
    <div className="p-8 space-y-6">
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
          <TabsList className="bg-muted/50 p-1 border border-border">
            <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Overview</TabsTrigger>
            <TabsTrigger value="prompts" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Prompts</TabsTrigger>
            <TabsTrigger value="competitors" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Competitors</TabsTrigger>
            <TabsTrigger value="answer-gap" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Answer Gap</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6 mt-6">
            <div className="flex items-center justify-between">
              <TimeFilter selected={timePeriod} onSelect={setTimePeriod} />
              <Select defaultValue="all">
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All Competitors" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Competitors</SelectItem>
                  {competitors.length > 0 && competitors.map((comp) => (
                    <SelectItem key={comp.id} value={String(comp.id)}>
                      {comp.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Competitor Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {competitors.length > 0 ? (
                competitors.map((competitor, idx) => (
                <Card
                  key={competitor.id}
                  className={`p-6 transition-all duration-300 backdrop-blur-sm bg-card/80 ${
                    competitor.isYou
                      ? 'border-2 border-primary cursor-default'
                      : 'cursor-pointer border border-border hover:border-primary'
                  }`}
                  onClick={() => !competitor.isYou && navigate(`/competitors/${competitor.url.replace('.com', '')}`)}
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-xl font-semibold font-outfit">{competitor.name}</h3>
                          {competitor.isYou && (
                            <Badge variant="default" className="gradient-primary border-0">You</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{competitor.url}</p>
                      </div>
                      <div className="w-12 h-12 rounded-xl gradient-primary shadow-glow flex items-center justify-center font-bold text-white text-lg font-outfit">
                        #{idx + 1}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Mentions</p>
                        <p className="text-2xl font-bold font-outfit">{competitor.mentions}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Share</p>
                        <p className="text-2xl font-bold font-outfit">{competitor.shareOfVoice}%</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Visibility</p>
                        <p className="text-lg font-bold font-outfit">{competitor.visibility}%</p>
                        <Progress value={competitor.visibility} className="h-1.5 mt-2" />
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Sentiment</p>
                        <p className="text-lg font-bold font-outfit">{competitor.sentiment}%</p>
                        <Progress value={competitor.sentiment} className="h-1.5 mt-2" />
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
                        <Button variant="ghost" size="sm" className="text-primary">
                          View Details →
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
                ))
              ) : (
                <div className="col-span-full flex flex-col items-center justify-center py-12 space-y-2">
                  <p className="text-sm text-muted-foreground">No competitors data available yet.</p>
                  <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                </div>
              )}
            </div>

            {/* Brand Visibility Over Time */}
            <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
              <div className="space-y-6">
                <div className="pb-4 border-b border-border">
                  <h3 className="text-lg font-semibold flex items-center gap-2 font-outfit">
                    <TrendingUp className="h-5 w-5 text-primary" />
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
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Legend />
                      {Object.keys(sovSeries[0] || {}).filter(k => k !== 'month').map((brandKey, idx) => {
                        const colors = [
                          { stroke: "hsl(var(--primary))", fill: "hsl(var(--primary))", width: 3, r: 4 },
                          { stroke: "hsl(var(--chart-2))", fill: "hsl(var(--chart-2))", width: 2, r: 3 },
                          { stroke: "hsl(var(--chart-3))", fill: "hsl(var(--chart-3))", width: 2, r: 3 },
                        ];
                        const color = colors[idx] || colors[0];
                        return (
                          <Line 
                            key={brandKey}
                            type="monotone" 
                            dataKey={brandKey}
                            name={brandKey}
                            stroke={color.stroke}
                            strokeWidth={color.width}
                            dot={{ fill: color.fill, r: color.r }}
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

            {/* Heatmap and Top Brands */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <CompetitorHeatmap 
                  data={heatmapData} 
                  platforms={Object.keys(platformMap).length > 0 ? Object.keys(platformMap) : []} 
                />
              </div>
              <div>
                <TopBrandsList brands={topBrands} totalMentions={topBrands.length ? topBrands.reduce((s,b)=>s+b.mentions,0) : 0} />
              </div>
            </div>

            {/* Competitive Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold">Competitive Strength Analysis</h3>
                  {isLoadingAnalysis && (
                    <span className="text-xs text-muted-foreground">Loading...</span>
                  )}
                </div>
                {competitiveMetrics && competitiveMetrics.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <RadarChart data={competitiveMetrics}>
                      <PolarGrid stroke="hsl(var(--border))" />
                      <PolarAngleAxis 
                        dataKey="metric" 
                        stroke="hsl(var(--muted-foreground))"
                        fontSize={12}
                      />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
                      <Tooltip 
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "var(--radius)",
                        }}
                      />
                      <Legend />
                      {competitiveMetrics[0] && Object.keys(competitiveMetrics[0]).filter(k => k !== 'metric').map((brandKey, idx) => {
                        const colors = [
                          { stroke: "hsl(var(--primary))", fill: "hsl(var(--primary))", opacity: 0.3 },
                          { stroke: "hsl(var(--chart-2))", fill: "hsl(var(--chart-2))", opacity: 0.2 },
                          { stroke: "hsl(var(--chart-3))", fill: "hsl(var(--chart-3))", opacity: 0.2 },
                        ];
                        const color = colors[idx] || colors[0];
                        // Format brand name for display
                        const displayName = brandKey.charAt(0).toUpperCase() + brandKey.slice(1).replace(/([A-Z])/g, ' $1');
                        return (
                          <Radar 
                            key={brandKey}
                            name={displayName}
                            dataKey={brandKey}
                            stroke={color.stroke}
                            fill={color.fill}
                            fillOpacity={color.opacity}
                            strokeWidth={idx === 0 ? 2 : 1.5}
                          />
                        );
                      })}
                    </RadarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex flex-col items-center justify-center h-64 space-y-2">
                    <p className="text-sm text-muted-foreground">No competitive strength data available yet.</p>
                    <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                  </div>
                )}
              </Card>

              <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold font-outfit">Competitive Intelligence</h3>
                  {isLoadingAnalysis && (
                    <span className="text-xs text-muted-foreground">Loading...</span>
                  )}
                </div>
                <div className="space-y-3">
                  {competitiveInsights && competitiveInsights.length > 0 ? (
                    competitiveInsights.map((insight: any, idx: number) => (
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
                              <h4 className="font-semibold text-sm font-outfit">{insight.title}</h4>
                              <Badge variant={insight.impact === 'high' ? 'default' : 'secondary'} className="text-xs">
                                {insight.impact}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground leading-relaxed">{insight.description}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 space-y-2">
                      <p className="text-sm text-muted-foreground">No competitive insights available yet.</p>
                      <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            {/* Platform Breakdown */}
            <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
              <h3 className="text-lg font-semibold mb-6 font-outfit">Platform-Specific Competition</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {Object.keys(platformMap).length > 0 ? (
                  Object.entries(platformMap).map(([platform, data]) => (
                    <div key={platform} className="space-y-4">
                      <h4 className="font-medium text-center">{platform}</h4>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={data}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis 
                            dataKey="brand" 
                            stroke="hsl(var(--muted-foreground))" 
                            fontSize={10}
                            angle={-45}
                            textAnchor="end"
                            height={80}
                          />
                          <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} />
                          <Tooltip />
                          <Bar dataKey="mentions" radius={[8, 8, 0, 0]}>
                            <Cell fill="hsl(var(--primary))" />
                            <Cell fill="hsl(var(--chart-2))" />
                            <Cell fill="hsl(var(--chart-3))" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ))
                ) : (
                  <div className="col-span-full flex items-center justify-center py-8">
                    <p className="text-sm text-muted-foreground">No platform data available yet.</p>
                  </div>
                )}
              </div>
            </Card>
          </TabsContent>

          {/* Prompts Tab */}
          <TabsContent value="prompts" className="space-y-6 mt-6">
            <Card className="p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border">
                  <div>
                    <h3 className="text-lg font-semibold font-outfit">Prompt Performance Analysis</h3>
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

          {/* Competitors Tab */}
          <TabsContent value="competitors" className="space-y-6 mt-6">
            <div className="grid grid-cols-1 gap-6">
              {competitors.length > 0 ? (
                competitors.map((competitor) => (
                <Card key={competitor.id} className="p-6">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-2xl gradient-primary shadow-glow flex items-center justify-center">
                          <span className="text-2xl font-bold text-white font-outfit">
                            {competitor.name.substring(0, 1)}
                          </span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-2xl font-bold font-outfit">{competitor.name}</h3>
                            {competitor.isYou && (
                              <Badge className="gradient-primary border-0">You</Badge>
                            )}
                          </div>
                          <p className="text-muted-foreground">{competitor.url}</p>
                        </div>
                      </div>
                      {!competitor.isYou && (
                        <Button onClick={() => navigate(`/competitors/${competitor.url.replace('.com', '')}`)}>
                          View Full Analysis
                        </Button>
                      )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <div className="p-4 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Mentions</p>
                        <p className="text-3xl font-bold font-outfit">{competitor.mentions}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Visibility</p>
                        <p className="text-3xl font-bold font-outfit">{competitor.visibility}%</p>
                      </div>
                      <div className="p-4 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Sentiment</p>
                        <p className="text-3xl font-bold font-outfit">{competitor.sentiment}%</p>
                      </div>
                      <div className="p-4 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Position</p>
                        <p className="text-3xl font-bold font-outfit">{competitor.avgPosition}</p>
                      </div>
                      <div className="p-4 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wider">Share</p>
                        <p className="text-3xl font-bold font-outfit">{competitor.shareOfVoice}%</p>
                      </div>
                    </div>
                  </div>
                </Card>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-12 space-y-2">
                  <p className="text-sm text-muted-foreground">No competitors data available yet.</p>
                  <p className="text-xs text-muted-foreground">Check console for API response details.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Answer Gap Tab */}
          <TabsContent value="answer-gap" className="space-y-6 mt-6">
            <Card className="p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border">
                  <div>
                    <h3 className="text-lg font-semibold font-outfit">Answer Gap Analysis</h3>
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
