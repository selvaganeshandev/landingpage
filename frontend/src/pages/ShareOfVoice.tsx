import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  ArrowUpRight,
  ArrowDownRight,
  Crown
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
import { PageLoader } from "@/components/PageLoader";
import { useDomainStore } from "@/stores/domainStore";

type SovRow = { domain: number; competitor: number | null; platform?: string | null; share_percentage: number; mention_count: number; market_position?: number | null; timestamp: string };
type LatestSov = { domain_id: number; timestamp: string; platform: string; players: Array<{ competitor: any | null; share_percentage: number; mention_count: number; market_position: number | null }>; };

// Fallback minimal radar/matrix will be computed from latest share (visibility proxy)

const ShareOfVoice = () => {
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [days, setDays] = useState<number>(30);

  const [latest, setLatest] = useState<LatestSov | null>(null);
  const [rows, setRows] = useState<SovRow[]>([]);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [isLoadingCompetitors, setIsLoadingCompetitors] = useState(true);

  // Sync domainId from selectedDomain (Zustand store) or localStorage when domain changes
  useEffect(() => {
    if (!user) return;

    // Priority 1: Use selectedDomain from Zustand store (most up-to-date when user changes domain)
    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
        return;
      }
    }

    // Priority 2: Fallback to localStorage (synced with server)
    const id = getActiveDomainId(user);
    if (id && id !== domainId) setDomainId(id);
  }, [user, selectedDomain?.id, domainId]);

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

  const [isLoadingData, setIsLoadingData] = useState(true);

  useEffect(() => {
    const load = async () => {
      if (!domainId) return;
      setIsLoadingData(true);

      try {
        const [latestResp, byDomain, gaps] = await Promise.all([
          apiClient.getShareOfVoiceLatestEngine({ domain_id: domainId }),
          apiClient.getShareOfVoiceByDomain({ domain_id: domainId, days }),
          apiClient.getCompetitorGapsEngine({ domain_id: domainId })
        ]);

        // Transform latestResp array into expected format with players
        const transformedLatest = Array.isArray(latestResp) && latestResp.length > 0
          ? {
              domain_id: Number(domainId),
              timestamp: latestResp[0].timestamp,
              platform: latestResp[0].platform || 'Overall',
              players: latestResp.map((item: any) => ({
                competitor: item.competitor ? { id: item.competitor, name: item.competitor_name || item.brand_name } : null,
                share_percentage: item.share_percentage,
                mention_count: item.mention_count,
                market_position: item.market_position,
                brand_name: item.brand_name,
                is_you: item.is_you || false
              }))
            }
          : null;

        setLatest(transformedLatest as any);
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
      } finally {
        setIsLoadingData(false);
      }
    };
    void load();
  }, [domainId, days]);

  const ownBrandName = useMemo(() => {
    if (!latest?.players) return 'Your Brand';
    const yourBrand = latest.players.find(p => p.is_you || !p.competitor);
    return yourBrand?.brand_name || 'Your Brand';
  }, [latest]);

  const overallShare = useMemo(() => {
    if (!latest || !latest.players || !Array.isArray(latest.players)) return [] as any[];
    const items = latest.players.map((p:any) => ({
      brand: p.brand_name || p.competitor?.name || ownBrandName,
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

  // Show loading state while data is being fetched
  if (isLoadingCompetitors || isLoadingData) {
    return <PageLoader />;
  }

  // Show empty state when no data is available yet
  if (!latest || (latest.players && latest.players.length === 0)) {
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Share of Voice</h1>
            <p className="text-muted-foreground mt-2">
              Competitive benchmarking and market position analysis
            </p>
          </div>
        </div>

        <Card className="p-6 border-dashed border-border bg-card/70">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="p-3 rounded-full bg-muted">
              <Target className="h-6 w-6 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">
                No share of voice data yet
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Competitors are being automatically discovered and analyzed. Share of voice data will appear here once processing is complete.
              </p>
              <p className="text-xs text-muted-foreground">
                This typically takes 2-5 minutes. Please check back soon.
              </p>
            </div>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Refresh
            </Button>
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
            <Scatter name="Brands" data={overallShare.map((b,idx)=>{
              // Assign consistent colors from chart palette
              const chartColors = [
                'hsl(var(--chart-1))',
                'hsl(var(--chart-2))',
                'hsl(var(--chart-3))',
                'hsl(var(--chart-4))',
                'hsl(var(--chart-5))',
              ];
              return {
                brand: b.brand,
                visibility: b.share,
                sentiment: b.share,
                mentions: b.mentions,
                color: chartColors[idx % chartColors.length]
              };
            })}>
                {overallShare.map((entry, index) => {
                  const chartColors = [
                    'hsl(var(--chart-1))',
                    'hsl(var(--chart-2))',
                    'hsl(var(--chart-3))',
                    'hsl(var(--chart-4))',
                    'hsl(var(--chart-5))',
                  ];
                  return (
                    <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                  );
                })}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {overallShare.map((brand:any, idx:number) => {
              const chartColors = [
                'hsl(var(--chart-1))',
                'hsl(var(--chart-2))',
                'hsl(var(--chart-3))',
                'hsl(var(--chart-4))',
                'hsl(var(--chart-5))',
              ];
              return (
                <div key={brand.brand} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: chartColors[idx % chartColors.length] }} />
                    <span className="font-medium">{brand.brand}</span>
                  </div>
                  <span className="text-muted-foreground">{brand.mentions} mentions</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Platform-Specific Share */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Platform-Specific Share of Voice</h3>
        <div className="space-y-6">
          {Object.entries(platformShare).map(([platform, data]) => (
            <div key={platform} className="space-y-4">
              <h4 className="font-medium">{platform}</h4>
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
