import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Crown,
  Loader2,
  Plus
} from "lucide-react";
import { 
  BarChart,
  Bar,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell
} from "recharts";
import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";

type SovRow = { domain: number; competitor: number | null; platform?: string | null; share_percentage: number; mention_count: number; market_position?: number | null; timestamp: string };
type LatestSov = { domain_id: number; timestamp: string; platform: string; players: Array<{ competitor: any | null; share_percentage: number; mention_count: number; market_position: number | null }>; };

// Fallback minimal radar/matrix will be computed from latest share (visibility proxy)

const ShareOfVoice = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [days, setDays] = useState<number>(30);

  const [latest, setLatest] = useState<LatestSov | null>(null);
  const [rows, setRows] = useState<SovRow[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [isLoadingCompetitors, setIsLoadingCompetitors] = useState(true);
  const [isStarting, setIsStarting] = useState(false);

  const handleExportReport = () => {
    toast({
      title: "Exporting Report",
      description: "Your market report is being generated...",
    });
  };

  useEffect(() => {
    if (!user) return;
    // Use unified helper to get active domain ID (from localStorage, synced with server)
    const id = getActiveDomainId(user);
    if (id) setDomainId(id);
  }, [user]);

  // Load competitors first to check if any exist
  useEffect(() => {
    const loadCompetitors = async () => {
      if (!domainId) return;
      setIsLoadingCompetitors(true);
      try {
        const response = await apiClient.getCompetitorsEngine({ domain_id: domainId });
        const competitorList = Array.isArray(response) ? response : response?.results || [];
        setCompetitors(competitorList);
      } catch (e: any) {
        console.error('Failed to load competitors:', e);
        setCompetitors([]);
      } finally {
        setIsLoadingCompetitors(false);
      }
    };
    void loadCompetitors();
  }, [domainId]);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      // Don't load share of voice data if no competitors
      if (competitors.length === 0) return;

      try {
        const [latestResp, byDomain, gaps] = await Promise.all([
          apiClient.getShareOfVoiceLatestEngine({ domain_id: domainId }),
          apiClient.getShareOfVoiceByDomain({ domain_id: domainId, days }),
          apiClient.getCompetitorGapsEngine({ domain_id: domainId })
        ]);
        setLatest(latestResp as any);
        setRows(byDomain as any);
        setOpportunities(Array.isArray(gaps) ? gaps : gaps?.results || []);
      } catch (e:any) {
        const errorMessage = String(e.message || e);
        // Only show error for actual errors, not empty data
        const isNetworkError = errorMessage.includes('fetch') || errorMessage.includes('network') || errorMessage.includes('Network');
        const isServerError = errorMessage.includes('500') || errorMessage.includes('503') || errorMessage.includes('502');

        // Only show error toast for actual errors, not for empty data (404 is normal for empty data)
        if (isNetworkError || isServerError || (!errorMessage.includes('404') && !errorMessage.includes('Not Found'))) {
          toast({ title: 'Failed to load share of voice', description: errorMessage, variant: 'destructive' });
        }
        // For empty data, set default empty values without showing error
        setLatest(null);
        setRows([]);
        setOpportunities([]);
      }
    };
    void load();
  }, [domainId, days, competitors.length]);

  const ownBrandName = useMemo(() => (latest?.players?.find(p => !p.competitor)?.competitor?.name) || 'Your Brand', [latest]);

  const overallShare = useMemo(() => {
    if (!latest || !latest.players || !Array.isArray(latest.players)) return [] as any[];
    const items = latest.players.map((p:any) => ({
      brand: p.competitor?.name || ownBrandName,
      share: Number(p.share_percentage),
      mentions: Number(p.mention_count) || 0,
      change: 0,
    }));
    return items;
  }, [latest, ownBrandName]);

  const shareHistory = useMemo(() => {
    if (!rows || rows.length === 0) return [] as any[];
    const byDate: Record<string, Record<string, number>> = {};
    rows.forEach((r) => {
      const brand = (r as any).competitor_name || (r.competitor ? String(r.competitor) : ownBrandName);
      const date = r.timestamp;
      if (!byDate[date]) byDate[date] = {};
      byDate[date][brand] = Number(r.share_percentage);
    });
    const brands = new Set<string>();
    Object.values(byDate).forEach(map => Object.keys(map).forEach(b => brands.add(b)));
    const [b1, b2, b3] = Array.from(brands).slice(0, 3);
    return Object.entries(byDate).sort((a,b)=>a[0].localeCompare(b[0])).map(([date, v]) => ({
      month: date,
      [b1 || 'BrandA']: v[b1 || ''] || 0,
      [b2 || 'BrandB']: v[b2 || ''] || 0,
      [b3 || 'BrandC']: v[b3 || ''] || 0,
    }));
  }, [rows, ownBrandName]);

  const platformShare = useMemo(() => {
    if (!rows || rows.length === 0) return {} as Record<string, Array<{ brand: string; share: number }>>;
    const latestDate = rows.map(r=>r.timestamp).sort().pop();
    const filtered = rows.filter(r => r.timestamp === latestDate);
    const byPlatform: Record<string, Record<string, number>> = {};
    filtered.forEach((r) => {
      const plat = r.platform || 'Overall';
      const brand = (r as any).competitor_name || (r.competitor ? String(r.competitor) : ownBrandName);
      if (!byPlatform[plat]) byPlatform[plat] = {};
      byPlatform[plat][brand] = Number(r.share_percentage);
    });
    const result: Record<string, Array<{ brand: string; share: number }>> = {};
    Object.entries(byPlatform).forEach(([plat, mp]) => {
      result[plat] = Object.entries(mp).map(([brand, share]) => ({ brand, share })).sort((a,b)=>b.share-a.share);
    });
    return result;
  }, [rows, ownBrandName]);

  const marketShareValue = useMemo(() => overallShare.find(b => b.brand === ownBrandName)?.share || 0, [overallShare, ownBrandName]);
  const marketPosition = useMemo(() => {
    if (!overallShare.length) return 0;
    const sorted = [...overallShare].sort((a,b)=>b.share-a.share);
    return Math.max(1, sorted.findIndex(x => x.brand === ownBrandName) + 1);
  }, [overallShare, ownBrandName]);
  const dominanceScore = useMemo(() => Math.round(marketShareValue), [marketShareValue]);

  // Filter out "You" competitor to check for real competitors
  const realCompetitors = competitors.filter(c => !c.isYou && c.name !== 'You');

  // Check if all competitors have zero data (still processing)
  const allCompetitorsHaveZeroData = competitors.length > 0 && competitors.every(c =>
    (c.mentions === 0 || !c.mentions) &&
    (c.citations === 0 || !c.citations) &&
    (c.visibility === 0 || !c.visibility)
  );

  // Show empty state when no competitors exist
  if (!isLoadingCompetitors && realCompetitors.length === 0) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
              <p className="text-muted-foreground mt-2">
                Competitive benchmarking and market position analysis
              </p>
            </div>
          </div>
        </div>

        <Card className="p-8 border border-border">
          <div className="flex flex-col items-center text-center space-y-6 max-w-2xl mx-auto">
            <div className="space-y-2">
              <h2 className="text-2xl font-bold">Analyze Your Market Share</h2>
              <p className="text-muted-foreground">
                Share of Voice shows how your brand compares to competitors across AI platforms. To get started, you need to add competitors first.
              </p>
            </div>

            <div className="space-y-4 w-full">
              <div className="p-4 bg-muted/50 rounded-lg text-left space-y-2">
                <h3 className="font-semibold text-sm">What you'll get:</h3>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Market share percentage across all AI platforms</li>
                  <li>Your competitive position and dominance score</li>
                  <li>Platform-specific share of voice breakdown</li>
                  <li>Trend analysis showing share changes over time</li>
                  <li>Market opportunities to increase your visibility</li>
                </ul>
              </div>
            </div>

            <Button
              onClick={async () => {
                if (!domainId) {
                  toast({
                    title: "Error",
                    description: "No domain selected. Please select a domain first.",
                    variant: "destructive",
                  });
                  return;
                }

                setIsStarting(true);

                try {
                  const response: any = await apiClient.startCompetitorAnalysis(parseInt(domainId));

                  if (response.success) {
                    toast({
                      title: "Competitor Discovery Started",
                      description: `We found your top ${response.created_count || 5} competitors! Processing their data now...`,
                    });

                    // Reload competitors after a short delay
                    setTimeout(() => {
                      window.location.reload();
                    }, 1500);
                  } else {
                    toast({
                      title: "Analysis Failed",
                      description: response.error || "Failed to start competitor analysis",
                      variant: "destructive",
                    });
                  }
                } catch (error: any) {
                  console.error('Error starting competitor analysis:', error);
                  toast({
                    title: "Error",
                    description: error?.message || "Failed to start competitor analysis. Please try again.",
                    variant: "destructive",
                  });
                } finally {
                  setIsStarting(false);
                }
              }}
              disabled={isStarting}
              size="lg"
              className="gradient-primary"
            >
              {isStarting ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Discovering Competitors...
                </>
              ) : (
                'Start Competitor Discovery'
              )}
            </Button>

            <p className="text-sm text-muted-foreground">
              We'll automatically discover your top 5 competitors and start analyzing their AI visibility. This typically takes 2-5 minutes.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  // Show processing state when competitors exist but have no data yet
  if (allCompetitorsHaveZeroData || isLoadingCompetitors) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
            <p className="text-muted-foreground mt-2">
              Competitive benchmarking and market position analysis
            </p>
          </div>
          <Button
            onClick={() => window.location.reload()}
            variant="outline"
            size="sm"
          >
            <Loader2 className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>

        <Card className="p-6 border-dashed border-primary/40 bg-card/70">
          <div className="flex flex-col md:flex-row gap-4 items-start">
            <div className="p-3 rounded-full bg-primary/10 text-primary">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
            <div className="flex-1 space-y-2">
              <h3 className="text-lg font-semibold">
                Processing competitor data...
              </h3>
              <p className="text-sm text-muted-foreground">
                Your competitors have been discovered and are currently being analyzed. Share of voice data will appear here once processing is complete.
              </p>
              <p className="text-xs text-muted-foreground">
                This typically takes 2-5 minutes. The page will update automatically, or you can click Refresh to check for updates.
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
                <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
                  Refresh Status
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
          <p className="text-muted-foreground mt-2">
            Competitive benchmarking and market position analysis
          </p>
        </div>
        <Button onClick={handleExportReport} className="gradient-primary shadow-md shadow-primary/20">
          <FileText className="h-4 w-4 mr-2" />
          Export Market Report
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Market Share</p>
              <h3 className="text-4xl font-bold text-primary mt-2">{marketShareValue}%</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Target className="h-6 w-6" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <ArrowUpRight className="h-4 w-4 text-success" />
            <span className="text-success font-medium">+15%</span>
            <span className="text-muted-foreground">vs last period</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Market Position</p>
              <h3 className="text-4xl font-bold text-primary mt-2">#{marketPosition}</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Crown className="h-6 w-6" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Market Leader</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Dominance Score</p>
              <h3 className="text-4xl font-bold text-primary mt-2">{dominanceScore}</h3>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
              <Award className="h-6 w-6" />
            </div>
          </div>
          <Progress value={dominanceScore} className="mt-2" />
        </Card>
      </div>

      {/* Market Share Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Overall Market Share</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={overallShare} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis 
                dataKey="brand" 
                type="category" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={12}
                width={120}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Bar dataKey="share" radius={[0, 8, 8, 0]}>
                <Cell fill="hsl(var(--primary))" />
                <Cell fill="hsl(var(--chart-2))" />
                <Cell fill="hsl(var(--chart-3))" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Share of Voice Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={shareHistory}>
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
              {/* First three dynamic brands */}
              <Line 
                type="monotone" 
                dataKey={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[0] : 'BrandA'} 
                name={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[0] : 'Brand A'}
                stroke="hsl(var(--primary))" 
                strokeWidth={3}
                dot={{ fill: "hsl(var(--primary))", r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[1] : 'BrandB'} 
                name={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[1] : 'Brand B'}
                stroke="hsl(var(--chart-2))" 
                strokeWidth={2}
                dot={{ fill: "hsl(var(--chart-2))", r: 3 }}
              />
              <Line 
                type="monotone" 
                dataKey={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[2] : 'BrandC'} 
                name={shareHistory[0] ? Object.keys(shareHistory[0]).filter(k=>k!=='month')[2] : 'Brand C'}
                stroke="hsl(var(--chart-3))" 
                strokeWidth={2}
                dot={{ fill: "hsl(var(--chart-3))", r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Competitive Positioning */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Competitive Strength Radar</h3>
          <ResponsiveContainer width="100%" height={350}>
            <RadarChart data={[{ category: 'Visibility', a: marketShareValue, b: 100-marketShareValue, c: 50 }]}>
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis 
                dataKey="category" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="hsl(var(--muted-foreground))" />
              <Radar 
                name={ownBrandName} 
                dataKey="a" 
                stroke="hsl(var(--primary))" 
                fill="hsl(var(--primary))" 
                fillOpacity={0.3}
                strokeWidth={2}
              />
              <Radar 
                name="Brand B" 
                dataKey="b" 
                stroke="hsl(var(--chart-2))" 
                fill="hsl(var(--chart-2))" 
                fillOpacity={0.2}
              />
              <Radar 
                name="Brand C" 
                dataKey="c" 
                stroke="hsl(var(--chart-3))" 
                fill="hsl(var(--chart-3))" 
                fillOpacity={0.2}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Brand Positioning Matrix</h3>
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid stroke="hsl(var(--border))" />
              <XAxis 
                type="number" 
                dataKey="visibility" 
                name="Visibility Score"
                domain={[70, 100]}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                label={{ value: "Visibility Score", position: "bottom", fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis 
                type="number" 
                dataKey="sentiment" 
                name="Sentiment %"
                domain={[60, 80]}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                label={{ value: "Sentiment %", angle: -90, position: "left", fill: "hsl(var(--muted-foreground))" }}
              />
              <ZAxis type="number" dataKey="mentions" range={[200, 1000]} />
              <Tooltip 
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
            <Scatter name="Brands" data={overallShare.map((b,idx)=>({ brand:b.brand, visibility:b.share, sentiment: b.share, mentions:b.mentions, color: idx===0?"hsl(var(--primary))":"hsl(var(--muted-foreground))" }))}>
                {overallShare.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={(entry as any).color} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {overallShare.map((brand:any) => (
              <div key={brand.brand} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: brand.brand===ownBrandName? 'hsl(var(--primary))': 'hsl(var(--muted-foreground))' }} />
                  <span className="font-medium">{brand.brand}</span>
                </div>
                <span className="text-muted-foreground">{brand.mentions} mentions</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Platform-Specific Share */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Platform-Specific Share of Voice</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(platformShare).map(([platform, data]) => (
            <div key={platform} className="space-y-4">
              <h4 className="font-medium text-center">{platform}</h4>
              <div className="space-y-3">
                {data.map((brand, idx) => (
                  <div key={brand.brand} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className={idx === 0 ? "font-medium" : "text-muted-foreground"}>
                        {brand.brand}
                      </span>
                      <span className="font-bold">{brand.share}%</span>
                    </div>
                    <Progress value={brand.share} className="h-2" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Market Opportunities */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Market Opportunities</h3>
        <div className="space-y-4">
          {opportunities && opportunities.length > 0 ? opportunities.map((opp:any, idx:number) => (
            <div key={`${opp.prompt_id||idx}`} className="p-4 rounded-lg transition-all duration-300 border border-border hover:border-primary">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <p className="font-mono text-sm mb-2">{opp.prompt?.prompt || opp.prompt_text || opp.prompt_id || 'Prompt'}</p>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{opp.mention_count || 0} avg mentions</span>
                    {typeof opp.current_share === 'number' && <span>Current share: {opp.current_share}%</span>}
                  </div>
                </div>
                <Badge 
                  variant="secondary"
                >
                  competitor: {opp.competitor?.name || opp.competitor_name || 'Unknown'}
                </Badge>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-muted-foreground">Platforms:</span>
                {(opp.platform ? [opp.platform] : (opp.citation_list || [])).slice(0,4).map((p:any,i:number)=>(
                  <Badge key={i} variant="outline" className="text-xs">{String(p||'AI')}</Badge>
                ))}
              </div>
            </div>
          )) : (
            <p className="text-sm text-muted-foreground">No opportunities detected yet.</p>
          )}
        </div>
      </Card>
    </div>
  );
};

export default ShareOfVoice;
