import { useEffect, useMemo, useRef, useState } from "react";
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
import { ProcessingStateCard } from "@/components/ProcessingStateCard";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
import { isDomainProcessing, isCompetitorProcessing } from "@/utils/processingStatus";
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
  Sparkles,
  Loader2,
  ExternalLink
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
  const [promptsLLMFilter, setPromptsLLMFilter] = useState("all");
  const { toast } = useToast();
  const { navigateToContentGeneration } = useContentGeneration();
  const [addCompetitorDialogOpen, setAddCompetitorDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState<any>(null);
  const { user } = useAuth();
  const { selectedDomain, loadDomains } = useDomainStore();
  const [domainId, setDomainId] = useState<string | null>(null);
  const [loadedDomainId, setLoadedDomainId] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [sovLatest, setSovLatest] = useState<any>(null);
  const [sovSeries, setSovSeries] = useState<any[]>([]);
  const [platformMap, setPlatformMap] = useState<Record<string, Array<{ brand: string; mentions: number }>>>({});
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [heatmapPlatforms, setHeatmapPlatforms] = useState<string[]>([]);
  const [topBrands, setTopBrands] = useState<any[]>([]);
  const [promptRows, setPromptRows] = useState<any[]>([]);
  const [promptCompetitorFilter, setPromptCompetitorFilter] = useState<string>("all");
  const [promptsCurrentPage, setPromptsCurrentPage] = useState(1);
  const [promptsTotalPages, setPromptsTotalPages] = useState(0);
  const [promptsTotalCount, setPromptsTotalCount] = useState(0);
  const [competitiveMetrics, setCompetitiveMetrics] = useState<any[]>([]);
  const [competitiveInsights, setCompetitiveInsights] = useState<any[]>([]);
  const [answerGapData, setAnswerGapData] = useState<any[]>([]);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [hasLoadedData, setHasLoadedData] = useState(false);
  const [disabledBrands, setDisabledBrands] = useState<string[]>([]);
  const [strengthDisabledBrands, setStrengthDisabledBrands] = useState<string[]>([]);
  const loadAbortRef = useRef<AbortController | null>(null);
  const domainProcessingStatus = selectedDomain?.processing_status || null;
  // Use utility function to check if domain or competitor analysis is processing
  const isProcessing = isDomainProcessing(selectedDomain) || isCompetitorProcessing(selectedDomain);

  // Persistent analysis state - stored in localStorage
  const [isAnalysisInProgress, setIsAnalysisInProgress] = useState<boolean>(false);
  const [analysisStartTime, setAnalysisStartTime] = useState<number>(0);
  const [isStarting, setIsStarting] = useState<boolean>(false);
  const [analysisProgress, setAnalysisProgress] = useState<{ completed: number; total: number }>({ completed: 0, total: 0 });

  // Load analysis state from localStorage when domainId changes
  useEffect(() => {
    if (!domainId) return;

    const storedProgress = localStorage.getItem(`competitor_analysis_progress_${domainId}`);
    const storedStartTime = localStorage.getItem(`competitor_analysis_start_${domainId}`);

    setIsAnalysisInProgress(storedProgress === 'true');
    setAnalysisStartTime(storedStartTime ? parseInt(storedStartTime) : 0);
  }, [domainId]);
  
  // Competitor colors for consistent styling
  const competitorColors = [
    'hsl(var(--primary))',
    'hsl(var(--chart-2))',
    'hsl(var(--chart-3))',
    'hsl(var(--chart-4))',
    'hsl(var(--chart-5))',
    'hsl(var(--success))',
    'hsl(var(--warning))',
    'hsl(var(--destructive))',
  ];

  // Poll for status updates every 10 seconds when domain or competitor analysis is processing
  useEffect(() => {
    if (!isProcessing) return;

    const interval = setInterval(() => {
      loadDomains(); // Refresh domain status from server
    }, 10000); // Poll every 10 seconds

    return () => clearInterval(interval);
  }, [isProcessing, loadDomains]);

  // Poll for competitor analysis completion when analysis is in progress
  useEffect(() => {
    if (!isAnalysisInProgress || !domainId) return;

    const checkAnalysisStatus = async () => {
      try {
        console.log('🔄 [COMPETITOR ANALYSIS] Polling for completion status...');

        const list: any = await apiClient.getEngineCompetitors({ domain_id: domainId });
        const competitorList = Array.isArray(list) ? list : list?.results || [];

        // Check if we have real competitors (not just "You") with data
        const realCompetitors = competitorList.filter((c: any) => !c.is_you);

        const competitorStatus = realCompetitors.map((c: any) => ({
          name: c.name,
          track_status: c.track_status,
          mentions: c.total_mentions || 0,
          citations: c.total_citations || 0
        }));
        console.log('📈 [COMPETITOR ANALYSIS] Current status:', competitorStatus);

        // Check if ALL competitors have reached COMP status
        const allCompetitorsCompleted = realCompetitors.length > 0 && realCompetitors.every((c: any) => c.track_status === 'COMP');

        // Count how many are in each status
        const statusCounts = realCompetitors.reduce((acc: any, c: any) => {
          const status = c.track_status || 'UNKNOWN';
          acc[status] = (acc[status] || 0) + 1;
          return acc;
        }, {});
        console.log('📊 [COMPETITOR ANALYSIS] Status summary:', statusCounts);

        if (allCompetitorsCompleted) {
          const elapsedTime = ((Date.now() - analysisStartTime) / 1000).toFixed(0);
          console.log(`✅ [COMPETITOR ANALYSIS] All ${realCompetitors.length} competitors completed! Time elapsed: ${elapsedTime}s`);
          console.log('🔄 [COMPETITOR ANALYSIS] Reloading page to display results...');

          // Analysis complete - clear localStorage and stop polling
          localStorage.removeItem(`competitor_analysis_progress_${domainId}`);
          localStorage.removeItem(`competitor_analysis_start_${domainId}`);
          setIsAnalysisInProgress(false);
          setAnalysisStartTime(0);
          setAnalysisProgress({ completed: 0, total: 0 });

          // Reload the page data to show the results
          setHasLoadedData(false);
          setIsPageLoading(true);
        } else {
          const completedCount = statusCounts['COMP'] || 0;
          const totalCount = realCompetitors.length;

          // Update progress state for UI display
          setAnalysisProgress({ completed: completedCount, total: totalCount });

          console.log(`⏳ [COMPETITOR ANALYSIS] Still processing - ${completedCount}/${totalCount} completed. Waiting for all to reach COMP status...`);
        }
      } catch (error) {
        console.error('❌ [COMPETITOR ANALYSIS] Error checking status:', error);
      }
    };

    // Poll every 10 seconds
    const interval = setInterval(checkAnalysisStatus, 10000);

    // Also check immediately
    checkAnalysisStatus();

    return () => clearInterval(interval);
  }, [isAnalysisInProgress, domainId, toast]);

  // Auto-refresh competitors data when competitors exist but have no data (processing state)
  useEffect(() => {
    const allCompetitorsHaveZeroData = competitors.length > 0 && competitors.every(c => 
      c.mentions === 0 && 
      c.citations === 0 && 
      c.visibility === 0 && 
      c.shareOfVoice === 0 && 
      c.sentiment === 0
    );

    if (allCompetitorsHaveZeroData && hasLoadedData && !isPageLoading) {
      // Auto-refresh every 15 seconds when competitors are being processed
      const interval = setInterval(() => {
        if (domainId) {
          // Trigger a reload by updating a dependency that causes useEffect to re-run
          setDomainId(domainId);
        }
      }, 15000); // Poll every 15 seconds

      return () => clearInterval(interval);
    }
  }, [competitors, hasLoadedData, isPageLoading, domainId]);

  const promptCards = useMemo(() => {
    if (!promptRows.length) return [];

    // No need for client-side filtering - backend already filters by platform
    const filteredRows = promptRows;

    if (!filteredRows.length) {
      return [];
    }

    type PromptAggregate = {
      prompt: string;
      brandCounts: Record<string, number>;
      brandCitationCounts: Record<string, number>;
      total: number;
      platformCounts: Record<string, number>;
      citationTotal: number;
    };

    const brandTotals = new Map<string, number>();
    const promptMap = new Map<string, PromptAggregate>();

    // First, initialize all competitors in all prompts to ensure they appear even with 0 mentions
    const allCompetitorNames = new Set(competitors.map(c => c.name));
    filteredRows.forEach((row) => {
      const brandName = row.competitorName || 'Unknown';
      if (brandName !== 'Unknown') {
        allCompetitorNames.add(brandName);
      }
    });

    filteredRows.forEach((row) => {
      const brandName = row.competitorName || 'Unknown';
      brandTotals.set(brandName, (brandTotals.get(brandName) || 0) + row.mentionCount);

      const key = row.promptText;
      const aggregate =
        promptMap.get(key) ||
        {
          prompt: row.promptText,
          brandCounts: {},
          brandCitationCounts: {},
          total: 0,
          platformCounts: {},
          citationTotal: 0,
        };

      // Initialize all competitors in this prompt aggregate to 0 if not already set
      allCompetitorNames.forEach(compName => {
        if (aggregate.brandCounts[compName] === undefined) {
          aggregate.brandCounts[compName] = 0;
          aggregate.brandCitationCounts[compName] = 0;
        }
      });

      aggregate.brandCounts[brandName] = (aggregate.brandCounts[brandName] || 0) + row.mentionCount;
      aggregate.brandCitationCounts[brandName] = (aggregate.brandCitationCounts[brandName] || 0) + (row.citationCount || 0);
      aggregate.total += row.mentionCount;
      aggregate.platformCounts[row.platform] = (aggregate.platformCounts[row.platform] || 0) + row.mentionCount;
      aggregate.citationTotal += row.citationCount || 0;

      promptMap.set(key, aggregate);
    });

    // For prompts that don't have any rows but should show all competitors with 0
    // This ensures prompts with only "You" brand still show all competitors
    const promptsInRows = new Set(filteredRows.map(row => row.promptText));
    promptMap.forEach((aggregate, promptText) => {
      allCompetitorNames.forEach(compName => {
        if (aggregate.brandCounts[compName] === undefined) {
          aggregate.brandCounts[compName] = 0;
          aggregate.brandCitationCounts[compName] = 0;
        }
      });
    });

    // Filter out prompts where no competitor has any mentions (total is 0)
    const promptsWithMentions = Array.from(promptMap.entries()).filter(([_, aggregate]) => aggregate.total > 0);

    if (!promptsWithMentions.length) return [];

    const sortedBrandNames = Array.from(brandTotals.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([name]) => name);

    // Create a map of competitor names to their colors
    const competitorColorMap = new Map<string, string>();
    competitors.forEach((comp, idx) => {
      competitorColorMap.set(comp.name, comp.color || competitorColors[idx % competitorColors.length]);
    });

    // Always include "You" brand if it exists in competitors, even if it has no mentions for this filter
    const youBrand = competitors.find((c) => c.isYou);
    const fallbackBrands = competitors.map((c) => c.name);
    
    // Build brand priority: include "You" first if it exists, then sorted by mentions
    let brandPriority: string[] = [];
    if (youBrand && !sortedBrandNames.includes(youBrand.name)) {
      brandPriority.push(youBrand.name);
    }
    brandPriority = [...brandPriority, ...sortedBrandNames];
    
    // If no sorted brands, use fallback
    if (brandPriority.length === 0) {
      brandPriority = fallbackBrands;
    }
    
    // Show ALL competitors that have mentions OR are in the competitors list
    // Include "You" first, then others sorted by mentions
    const allBrandsWithMentions = new Set(brandPriority);
    // Add all competitors that might not have mentions yet
    competitors.forEach((comp) => {
      allBrandsWithMentions.add(comp.name);
    });
    
    // Build final list: "You" first, then others sorted by mentions
    const brandsToDisplay: string[] = [];
    if (youBrand) {
      brandsToDisplay.push(youBrand.name);
    }
    // Add other brands sorted by mentions (excluding "You" if already added)
    brandPriority.forEach((brand) => {
      if (brand !== youBrand?.name) {
        brandsToDisplay.push(brand);
      }
    });
    // Add any remaining competitors that weren't in brandPriority
    competitors.forEach((comp) => {
      if (!brandsToDisplay.includes(comp.name)) {
        brandsToDisplay.push(comp.name);
      }
    });

    const cards = promptsWithMentions
      .map(([_, aggregate]) => aggregate)
      .sort((a, b) => b.total - a.total)
      .map((aggregate, idx) => {
        // Find winner - only consider brands with mentions > 0
        const brandsWithMentions = Object.entries(aggregate.brandCounts).filter(([_, count]) => count > 0);
        const winnerEntry = brandsWithMentions.sort((a, b) => b[1] - a[1])[0];

        // Add winner's citation count to the winner display
        let winner = 'N/A';
        let isYouWinner = false;
        if (winnerEntry) {
          const winnerBrand = winnerEntry[0];
          const winnerMentions = winnerEntry[1];
          const winnerCitations = aggregate.brandCitationCounts[winnerBrand] || 0;

          // Check if the winner is "You" brand
          isYouWinner = youBrand && winnerBrand === youBrand.name;

          winner = winnerCitations > 0
            ? `${winnerBrand} (${winnerMentions} mentions, ${winnerCitations} citations)`
            : `${winnerBrand} (${winnerMentions} mentions)`;
        }

        const topPlatformEntry = Object.entries(aggregate.platformCounts).sort((a, b) => b[1] - a[1])[0];
        const topPlatform = topPlatformEntry ? `${topPlatformEntry[0]} (${topPlatformEntry[1]} mentions)` : null;

        // Use the actual brands from the aggregate data (not forced from competitors list)
        // This ensures we display all brands that have data, with correct counts
        const aggregateBrands = Object.keys(aggregate.brandCounts);

        // Sort brands: "You" brand first, then by mention count
        const sortedAggregateBrands = aggregateBrands.sort((a, b) => {
          const aIsYou = youBrand && a === youBrand.name;
          const bIsYou = youBrand && b === youBrand.name;
          if (aIsYou && !bIsYou) return -1;
          if (!aIsYou && bIsYou) return 1;
          return (aggregate.brandCounts[b] || 0) - (aggregate.brandCounts[a] || 0);
        });

        // Use a single theme color for all brands instead of multiple colors
        const brandColors = sortedAggregateBrands.map(() => 'hsl(var(--primary))');

        return {
          id: idx + 1,
          prompt: aggregate.prompt,
          brands: sortedAggregateBrands,
          counts: sortedAggregateBrands.map((brand) => aggregate.brandCounts[brand] || 0),
          citationCounts: sortedAggregateBrands.map((brand) => aggregate.brandCitationCounts[brand] || 0),
          colors: brandColors,
          total: aggregate.total,
          winner,
          isYouWinner,
          topPlatform,
          citationTotal: aggregate.citationTotal,
        };
      });

    return cards;
  }, [promptRows, competitors]);

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
        setPromptRows([]);
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
    const controller = new AbortController();
    if (loadAbortRef.current) {
      loadAbortRef.current.abort();
    }
    loadAbortRef.current = controller;
    let didAbort = false;

    const load = async () => {
      if (!domainId) {
        setHasLoadedData(false);
        setIsPageLoading(true);
        return;
      }

      // Don't load data if analysis is in progress - show progress card instead
      if (isAnalysisInProgress) {
        setHasLoadedData(true);
        setIsPageLoading(false);
        setLoadedDomainId(domainId);
        return;
      }

      if (domainProcessingStatus && domainProcessingStatus !== 'COMP') {
        setHasLoadedData(true);
        setLoadedDomainId(domainId);
        setIsPageLoading(false);
        setIsLoadingAnalysis(false);
        setCompetitors([]);
        setTopBrands([]);
        setPromptRows([]);
        setPlatformMap({});
        setSovSeries([]);
        setHeatmap([]);
        setHeatmapPlatforms([]);
        setAnswerGapData([]);
        return;
      }
      // Clear data immediately when platform filter changes to show empty state faster
      if (loadedDomainId !== domainId || !hasLoadedData) {
        setHasLoadedData(false);
        setIsPageLoading(true);
      } else {
        // When just filtering by platform, clear data immediately so empty state shows instantly
        setIsLoadingAnalysis(true);
        setCompetitors([]);
        setTopBrands([]);
        setPromptRows([]);
        setCompetitiveMetrics([]);
        setCompetitiveInsights([]);
        setAnswerGapData([]);
        setHeatmap([]);
        setHeatmapPlatforms([]);
        setSovSeries([]);
        // Reset pagination when filtering
        setPromptsCurrentPage(1);
      }

      const startTime = performance.now();

      try {
        // Load main competitor data first (in parallel)
        const batchStartTime = performance.now();
        const [list, latest, byDomain, snapshotHistory, heatmapResponse] = await Promise.all([
          apiClient.getEngineCompetitors({ domain_id: domainId }, { signal: controller.signal }),
          apiClient.getShareOfVoiceLatestEngine({ domain_id: domainId }, { signal: controller.signal }),
          apiClient.getShareOfVoiceByDomain({ domain_id: domainId, days: Number(timePeriod) }, { signal: controller.signal }),
          apiClient.getCompetitorMetricSnapshots({ domain_id: domainId, days: Number(timePeriod) }, { signal: controller.signal }),
          apiClient.getCompetitorHeatmap({ domain_id: domainId, days: Number(timePeriod) }, { signal: controller.signal }),
        ] as any);

        // Prompts are now loaded separately by the pagination useEffect

        // Load competitive analysis APIs IN PARALLEL with better error handling
        setIsLoadingAnalysis(true);
        const analysisStartTime = performance.now();

        const [strengthAnalysis, insights, gaps] = await Promise.all([
          apiClient.getCompetitiveStrengthAnalysis({
            domain_id: domainId
          }, { signal: controller.signal }).catch((e: any) => {
            console.error('❌ Failed to load competitive strength analysis:', e?.message);
            return undefined;
          }),

          apiClient.getCompetitiveInsights({
            domain_id: domainId
          }, { signal: controller.signal }).catch((e: any) => {
            console.error('❌ Failed to load competitive insights:', e?.message);
            return undefined;
          }),

          apiClient.getAnswerGapAnalysis({
            domain_id: domainId,
            competitor_id: promptCompetitorFilter !== 'all' ? promptCompetitorFilter : undefined
          }, { signal: controller.signal }).catch((e: any) => {
            console.error('❌ Failed to load answer gap analysis:', e?.message);
            return undefined;
          }),
        ]);

        setHasLoadedData(true);
        setLoadedDomainId(domainId); // Mark this domain as loaded
        // Normalize competitor list
        let mapped = (Array.isArray(list) ? list : list?.results || []).map((c: any, idx: number) => {
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
          
          const isYou = c.is_you === true || c.name === 'You';
          
          // Format name: "Brand Name (You)" for your brand, otherwise just the name
          const displayName = isYou && c.domain_name 
            ? `${c.domain_name} (You)`
            : (c.name || 'Unknown');
          
          return {
            id: c.id,
            name: displayName,
            originalName: c.name || 'Unknown', // Keep original for reference
            domainName: c.domain_name || c.name || 'Unknown', // Domain name for "You"
            url: c.url || (c.domain_name || '').toLowerCase(),
            mentions: c.total_mentions || 0,
            citations: c.total_citations || 0,
            visibility: Math.round(Number(c.visibility_score || 0)),
            sentiment: sentimentPercent,
            averagePosition: Number(c.average_position || 0),
            shareOfVoice: Math.round(Number(c.share_of_voice_percentage || 0)),
            trend: Number(c.trend_percentage || 0),
            color: competitorColors[idx % competitorColors.length], // Different color for each competitor
            isYou: isYou, // "You" is now included in the list
          };
        });
        
        // Ensure "You" is always included, even if API doesn't return it (e.g., when filtering by platform with zero mentions)
        const hasYou = mapped.some((c: any) => c.isYou);
        if (!hasYou && selectedDomain) {
          const youCompetitor = {
            id: -1, // Use -1 as a placeholder ID
            name: `${selectedDomain.name} (You)`,
            originalName: 'You',
            domainName: selectedDomain.name || 'You',
            url: selectedDomain.url || '',
            mentions: 0,
            citations: 0,
            visibility: 0,
            sentiment: 0,
            averagePosition: 0,
            shareOfVoice: 0,
            trend: 0,
            color: competitorColors[0], // Use first color for "You"
            isYou: true,
          };
          // Add "You" at the beginning of the list
          mapped = [youCompetitor, ...mapped];
        }
        
        setCompetitors(mapped.length ? mapped : []);

        setSovLatest(latest);

        // Prepare Share of Voice rows for fallback/platform data
        const rows = Array.isArray(byDomain) ? byDomain : byDomain?.results || [];
        const groupedRows: Record<string, Record<string, number>> = {};

        // Get user's brand name for consistent naming
        const userBrandForSeries = mapped.find((c: any) => c.isYou);
        const userBrandName = userBrandForSeries?.name || (selectedDomain?.name ? `${selectedDomain.name} (You)` : 'Your Brand');

        rows.forEach((r: any) => {
          const month = r.timestamp || r.date || '';
          if (!groupedRows[month]) groupedRows[month] = {};
          // Use consistent brand naming - map "You" to the actual brand name
          let brand = r.competitor?.name || 'Your Brand';
          if (r.is_you || brand === 'You' || brand === 'Your Brand') {
            brand = userBrandName;
          }
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
            // Use consistent brand naming - map to the actual brand name
            let brand = snap.competitor_name || snap.competitor?.name || 'Unknown';
            const snapCompetitorId = snap.competitor_id || snap.competitor?.id;

            // Map brand name to the display name from mapped competitors
            if (brand === 'You' || brand === 'Your Brand' || brand === yourBrandLabel) {
              brand = userBrandName;
            } else {
              // Try to find the competitor in mapped list by ID or name
              const matchedCompetitor = mapped.find((c: any) =>
                c.id === snapCompetitorId ||
                c.originalName === brand ||
                c.domainName === brand ||
                c.name === brand
              );
              if (matchedCompetitor) {
                brand = matchedCompetitor.name;
              }
            }

            brandNames.add(brand);
            if (!groupedSnapshots[label]) groupedSnapshots[label] = {};
            groupedSnapshots[label][brand] = Number(snap.total_mentions || 0);
          });
          const sortedLabels = Object.keys(groupedSnapshots).sort();
          const brands = Array.from(brandNames);

          // Always ensure user's brand is included in the series
          if (!brands.includes(userBrandName)) {
            brands.unshift(userBrandName);
          }

          let series = sortedLabels.map((label) => {
            const entry: Record<string, number | string> = { month: label };
            brands.forEach((brand) => {
              entry[brand] = groupedSnapshots[label]?.[brand] || 0;
            });
            return entry;
          });

          setSovSeries(series);
          setDisabledBrands((prev) => prev.filter((brand) => brands.includes(brand)));
        } else {
          // Always ensure user's brand is included in fallback series
          const effectiveBrands = [...fallbackBrands];
          if (!effectiveBrands.includes(userBrandName)) {
            effectiveBrands.unshift(userBrandName);
          }

          const fallbackSeries = months.map(m => {
            const entry: any = { month: m };
            effectiveBrands.forEach(brand => {
              entry[brand] = groupedRows[m]?.[brand] || 0;
            });
            return entry;
          });
          setSovSeries(fallbackSeries);
          setDisabledBrands((prev) => prev.filter((brand) => effectiveBrands.includes(brand)));
        }

        // Platform-specific share for latest month using byDomain rows
        const lastDate = months[months.length - 1];
        const latestRows = rows.filter((r: any) => (r.timestamp || r.date) === lastDate);
        const platMap: Record<string, Record<string, number>> = {};
        latestRows.forEach((r: any) => {
          const plat = r.platform || 'Overall';
          // Use consistent brand naming
          let brand = r.brand_name || r.competitor?.name || 'Your Brand';
          if (r.is_you || brand === 'You' || brand === 'Your Brand') {
            brand = userBrandName;
          }
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
        // Map user brand name to URL
        competitorUrlMap[yourBrandLabel] = selectedDomain?.url || competitorUrlMap[yourBrandLabel] || '';
        competitorUrlMap[userBrandName] = selectedDomain?.url || '';

        // Heatmap: competitor (row) vs platform percentage
        const fallbackPlatforms = Object.keys(platOut);
        const brandsSet = new Set<string>();
        Object.values(platOut).forEach(arr => arr.forEach(e => brandsSet.add(e.brand)));

        // Always ensure user's brand is included, even with zero mentions
        const userBrand = mapped.find((c: any) => c.isYou);
        if (userBrand && !brandsSet.has(userBrand.name)) {
          brandsSet.add(userBrand.name);
        }

        const brands = Array.from(brandsSet);
        const fallbackHeatmap = brands.map((brand) => ({
          competitor: brand,
          platforms: fallbackPlatforms.reduce((acc: any, p) => {
            const total = (platOut[p] || []).reduce((s, e) => s + e.mentions, 0) || 1;
            const item = (platOut[p] || []).find((entry) => entry.brand === brand);
            acc[p] = item ? Number(((item.mentions / total) * 100).toFixed(1)) : 0;
            return acc;
          }, {}),
          isYou: brand === userBrand?.name || brand.toLowerCase().includes('your'),
          url: competitorUrlMap[brand] || (brand === userBrand?.name ? userBrand.url : ''),
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

          // Always ensure user's brand is included in API heatmap
          const hasUserBrand = formattedHeatmap.some((row: any) => row.isYou);
          if (!hasUserBrand && userBrand) {
            const userHeatmapRow = {
              competitor: userBrand.name,
              platforms: apiHeatmapPlatforms.reduce((acc: any, platform: string) => {
                acc[platform] = 0;
                return acc;
              }, {}),
              isYou: true,
              url: userBrand.url,
            };
            formattedHeatmap.unshift(userHeatmapRow); // Add at the beginning
          }

          setHeatmap(sortHeatmapRows(formattedHeatmap, apiHeatmapPlatforms));
          setHeatmapPlatforms(apiHeatmapPlatforms);
        } else {
          setHeatmap(sortHeatmapRows(fallbackHeatmap, fallbackPlatforms));
          setHeatmapPlatforms(fallbackPlatforms);
        }

        // Top brands list - use mapped competitors which already has correct data and formatting
        // This data comes from the backend API and includes all necessary metrics
        const tb = mapped
          .map((c: any) => ({
            name: c.name,
            url: c.url || '',
            mentions: c.mentions || 0,
            percentage: c.shareOfVoice || 0,
            isYou: c.isYou || false,
          }))
          .sort((a: any, b: any) => {
            // Sort "You" first, then by mentions (descending)
            if (a.isYou && !b.isYou) return -1;
            if (!a.isYou && b.isYou) return 1;
            return b.mentions - a.mentions;
          })
          .slice(0, 5); // Top 5 brands
        
        if (tb.length) setTopBrands(tb);

        // Build dynamic prompt performance cards
        const displayBrands = (mapped.length ? mapped : [])
          .sort((a: any, b: any) => (b.isYou ? 1 : 0) - (a.isYou ? 1 : 0))
          .slice(0, 3);
        
        // Create a mapping from original names to display names for prompt analytics
        const brandNameMap = new Map<string, string>();
        displayBrands.forEach((c: any) => {
          brandNameMap.set(c.originalName || c.name, c.name);
          brandNameMap.set(c.domainName || c.name, c.name);
        });

        // Prompts are now loaded by separate pagination useEffect

        // Set competitive strength analysis data - ALWAYS use API response (even if empty)
        if (strengthAnalysis !== undefined && strengthAnalysis !== null) {
          if (Array.isArray(strengthAnalysis)) {
            setCompetitiveMetrics(strengthAnalysis);
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
        if (controller.signal.aborted || didAbort || e?.name === 'AbortError') {
          console.info('ℹ️ Competitors load aborted');
          return;
        }
        // Only show error toast for actual errors, not for empty data
        if (e?.response?.status !== 404 && e?.response?.status !== 200) {
          console.error('Failed to load competitors:', e);
          // Don't show toast for empty data - just log and continue
        }
        setHasLoadedData(true);
        setLoadedDomainId(domainId); // Mark as loaded even on error to stop infinite loading
      } finally {
        if (!controller.signal.aborted && !didAbort) {
          const totalTime = ((performance.now() - startTime) / 1000).toFixed(2);
          console.log(`🎉 [COMPETITOR ANALYSIS] All data loaded in ${totalTime}s - Page ready to display`);

          // Always set loading to false after data loads, even when filtering
          setIsPageLoading(false);
          setIsLoadingAnalysis(false);
          setHasLoadedData(true);
          setLoadedDomainId(domainId);
        } else {
          // Still clear loading states even if aborted
          setIsLoadingAnalysis(false);
        }
      }
    };
    void load();

    return () => {
      didAbort = true;
      controller.abort();
    };
  }, [domainId, timePeriod, promptCompetitorFilter, domainProcessingStatus, toast, isAnalysisInProgress]);

  // Separate useEffect for prompt pagination - only reload prompts when page changes
  useEffect(() => {
    const controller = new AbortController();
    let didAbort = false;

    const loadPrompts = async () => {
      if (!domainId || !hasLoadedData) return; // Only run if initial data is loaded

      try {
        // Map filter values to actual platform names for API
        const platformMapping: Record<string, string> = {
          'chatgpt': 'ChatGPT',
          'gemini': 'Google Gemini',
          'perplexity': 'Perplexity',
          'claude': 'Claude'
        };

        const platformParam = promptsLLMFilter !== 'all'
          ? platformMapping[promptsLLMFilter.toLowerCase()] || promptsLLMFilter
          : undefined;

        const compPromptAnalytics = await apiClient.getCompetitorPromptAnalyticsEngine({
          domain_id: domainId,
          page_size: '20',
          page: promptsCurrentPage,
          ...(platformParam && { platform: platformParam })
        }, { signal: controller.signal });

        if (didAbort || controller.signal.aborted) return;

        // Handle new grouped response structure
        // Each result is a prompt with nested analytics array
        const promptGroups = Array.isArray(compPromptAnalytics) ? compPromptAnalytics : compPromptAnalytics?.results || [];
        const paginationInfo = !Array.isArray(compPromptAnalytics) ? compPromptAnalytics : null;

        // Store pagination info
        if (paginationInfo) {
          setPromptsTotalPages(paginationInfo.total_pages || 0);
          setPromptsTotalCount(paginationInfo.count || 0);
        }

        // Get current competitors for name mapping
        const youBrandName = competitors.find((c: any) => c.isYou)?.name || (selectedDomain?.name ? `${selectedDomain.name} (You)` : 'Your Brand');

        // Flatten grouped structure: each prompt has multiple analytics (one per competitor)
        // Transform to flat array of rows for existing UI logic
        const normalizedPromptRows: any[] = [];

        promptGroups.forEach((promptGroup: any) => {
          const promptId = promptGroup.prompt_id;
          const promptText = promptGroup.prompt_text;

          // Each analytics entry in the group becomes a separate row
          promptGroup.analytics.forEach((analytics: any) => {
            let competitorName = analytics.competitor_name;

            if (!competitorName) {
              competitorName = youBrandName;
            } else {
              const competitor = competitors.find((c: any) =>
                c.originalName === competitorName ||
                c.name === competitorName ||
                c.domainName === competitorName
              );
              competitorName = competitor?.name || competitorName;
            }

            normalizedPromptRows.push({
              id: analytics.id,
              promptId: promptId,
              promptText: promptText,
              competitorId: analytics.competitor_id,
              competitorName: competitorName,
              mentionCount: analytics.mention_count !== null && analytics.mention_count !== undefined
                ? Number(analytics.mention_count)
                : (analytics.is_mentioned ? 1 : 0),
              platform: analytics.platform || 'unknown',
              trackedAt: analytics.tracked_at,
              sentiment: analytics.sentiment_category || 'neutral',
              citationCount: Array.isArray(analytics.citation_list) ? analytics.citation_list.length : 0,
            });
          });
        });

        setPromptRows(normalizedPromptRows);
      } catch (e: any) {
        if (controller.signal.aborted || didAbort || e?.name === 'AbortError') {
          return;
        }
        console.error('Failed to load prompts page:', e);
      }
    };

    void loadPrompts();

    return () => {
      didAbort = true;
      controller.abort();
    };
  }, [promptsCurrentPage, domainId, hasLoadedData, competitors, selectedDomain, promptsLLMFilter]);

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
      // For immediate refresh, we'll reload just the competitor list - use backend API which includes "You"
      try {
        const list: any = await apiClient.get(`/competitors/competitors/by_domain/?domain_id=${domainId}`);
        if (list && Array.isArray(list)) {
          const mapped = list.map((c: any, idx: number) => {
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
            
            const isYou = c.is_you === true || c.name === 'You';
            
            // Format name: "Brand Name (You)" for your brand, otherwise just the name
            const displayName = isYou && c.domain_name 
              ? `${c.domain_name} (You)`
              : (c.name || 'Unknown');
            
            return {
              id: c.id,
              name: displayName,
              originalName: c.name || 'Unknown',
              domainName: c.domain_name || c.name || 'Unknown',
              url: c.url || '',
              mentions: c.total_mentions || 0,
              visibility: Number(c.visibility_score || 0),
              sentiment: sentimentPercent,
              avgPosition: Number(c.average_position || 0),
              shareOfVoice: Number(c.share_of_voice_percentage || 0),
              trend: Number(c.trend_percentage || 0),
              isYou: isYou,
              color: competitorColors[idx % competitorColors.length],
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
    setSelectedGap(gap);
    setGenerateDialogOpen(true);
  };

  const heatmapData = heatmap;

  // Show loading during initial load or when switching domains
  // Keep showing loader until we've loaded data for the current domain
  // BUT if analysis is in progress, show the progress card instead
  // ALSO show loader when filtering by platform (isLoadingAnalysis but competitors exist)
  if ((isPageLoading || !hasLoadedData || loadedDomainId !== domainId || (isLoadingAnalysis && competitors.length === 0)) && !isAnalysisInProgress) {
    return <PageLoader sidebarOpen />;
  }

  // Show ProcessingStateCard when domain or competitor analysis is processing
  if (isProcessing && selectedDomain) {
    return <ProcessingStateCard domain={selectedDomain} />;
  }

  // Check if we should show "You" as a competitor or filter it out
  // If the only competitor is "You" with no data, treat it as no competitors
  const realCompetitors = competitors.filter(c => !c.isYou);
  const youCompetitor = competitors.find(c => c.isYou);
  const hasOnlyYouWithNoData = competitors.length === 1 && youCompetitor &&
    youCompetitor.mentions === 0 && youCompetitor.citations === 0;

  // Show "Start Analysis" state when there are no real competitors (excluding "You")
  // BUT NOT if analysis is currently in progress
  if ((realCompetitors.length === 0 || hasOnlyYouWithNoData) && !isPageLoading && hasLoadedData && !isAnalysisInProgress) {
    const isDomainCompleted = domainProcessingStatus === 'COMP';
    const isDomainProcessing = domainProcessingStatus && domainProcessingStatus !== 'COMP';
    
    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight">Competitor Analysis</h1>
              <p className="text-muted-foreground mt-2">
                Compare your brand's AI visibility against competitors
              </p>
            </div>
          </div>
        </div>

        <Card className="p-8 border border-border">
          <div className="flex flex-col items-center text-center space-y-6 max-w-2xl mx-auto">
            <div className="space-y-2">
              <h2 className="text-2xl font-bold">Discover Your Top Competitors</h2>
              <p className="text-muted-foreground">
                Our AI will analyze your brand and automatically identify your top 5 competitors across AI platforms, plus discover related content and mentions.
              </p>
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
                  console.log('🚀 [COMPETITOR ANALYSIS] Starting competitor discovery...');

                  // Call the API to start competitor analysis
                  const response: any = await apiClient.startCompetitorAnalysis(parseInt(domainId));

                  if (response.success) {
                    console.log(`✅ [COMPETITOR ANALYSIS] Discovery initiated - ${response.created_count || 5} competitors found`);

                    // Set analysis in progress state and save to localStorage
                    const startTime = Date.now();
                    setIsAnalysisInProgress(true);
                    setAnalysisStartTime(startTime);
                    setAnalysisProgress({ completed: 0, total: response.created_count || 5 });
                    localStorage.setItem(`competitor_analysis_progress_${domainId}`, 'true');
                    localStorage.setItem(`competitor_analysis_start_${domainId}`, String(startTime));

                    console.log('📊 [COMPETITOR ANALYSIS] Progress card will be displayed - polling every 10s for completion');

                    toast({
                      title: "Competitor Discovery Started",
                      description: `We found your top ${response.created_count || 5} competitors! Processing their data now...`,
                    });
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
                  Starting Analysis...
                </>
              ) : (
                'Start Analysis'
              )}
            </Button>

            <p className="text-sm text-muted-foreground">
              Analysis typically takes 2-5 minutes. You'll be notified once complete.
            </p>
          </div>
        </Card>

        <AddCompetitorDialog
          open={addCompetitorDialogOpen}
          onOpenChange={setAddCompetitorDialogOpen}
          onAdd={handleAddCompetitorSubmit}
        />
      </div>
    );
  }

  // Check if all competitor details are showing zero values (processing state)
  const allCompetitorsHaveZeroData = competitors.length > 0 && competitors.every(c => 
    c.mentions === 0 && 
    c.citations === 0 && 
    c.visibility === 0 && 
    c.shareOfVoice === 0 && 
    c.sentiment === 0
  );

  // Empty state logic is now handled at the tab level (Overview, Prompts, Answer Gap)
  // Each tab checks if data exists for the selected platform and shows appropriate empty state

  // Calculate elapsed time for progress card
  const elapsedMinutes = analysisStartTime > 0 ? Math.floor((Date.now() - analysisStartTime) / 60000) : 0;

  // Show processing state when competitors exist but have no data yet OR when analysis is in progress
  // Don't show processing state when filtering by specific platform (let tabs show their empty states)
  if (allCompetitorsHaveZeroData || isAnalysisInProgress) {
    console.log('📊 [COMPETITOR ANALYSIS] Progress card is now visible - showing processing status');

    // Use analysisProgress state for dynamic count
    const { completed, total } = analysisProgress;
    const displayTotal = total || competitors.filter(c => !c.isYou).length;

    return (
      <div className="p-8 space-y-6 bg-background animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Competitor Analysis</h1>
            <p className="text-muted-foreground mt-2">
              Compare your brand's AI visibility against competitors
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
                {total > 0 ? `Processing: Analysed ${completed}/${total} competitors` : `Processing competitors...`}
              </h3>
              <p className="text-sm text-muted-foreground">
                Competitors have been discovered and are currently being analyzed. Analytics data will appear here once processing is complete.
              </p>
              <p className="text-xs text-muted-foreground">
                This can take 2-5 minutes while we gather mentions, calculate visibility scores, and generate competitive insights across AI platforms.
                {elapsedMinutes > 0 && ` Time elapsed: ${elapsedMinutes} minute${elapsedMinutes > 1 ? 's' : ''}.`}
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
              <Button
                  variant="outline"
                  size="sm"
                onClick={() => {
                  setHasLoadedData(false);
                  setIsPageLoading(true);
                  if (domainId) {
                    setDomainId(domainId);
                  }
                }}
                >
                  Refresh Status
                </Button>
                <Button variant="ghost" size="sm" onClick={() => navigate('/insights')}>
                  Go to Insights
              </Button>
            </div>
            </div>
          </div>
        </Card>

            {competitors.length > 0 && (
          <Card className="p-6 mt-6">
            <div className="w-full max-w-md">
                <p className="text-sm font-medium mb-3">Competitors being processed:</p>
                <div className="space-y-2">
                  {competitors.map((comp: any) => (
                    <div key={comp.id} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                      <span className="font-medium">{comp.name}</span>
                      <Badge variant="outline" className="gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Processing
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
          </Card>
            )}
      </div>
    );
  }

  // Note: Empty states for platform filtering are now handled at the tab level, not page level
  // This allows users to switch between tabs and see per-tab empty states with clear filter buttons

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
            {/* <Button variant="outline" onClick={handleExportReport}>
              <FileText className="h-4 w-4 mr-2" />
              Export Report
            </Button> */}
            <Button onClick={handleAddCompetitor} className="gradient-primary shadow-md shadow-primary/20">
              <Plus className="h-4 w-4 mr-2" />
              Add Competitor
            </Button>
          </div>
        </div>

        <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
          {realCompetitors.length > 0 && (
            <div className="flex items-center justify-between gap-4 mb-6">
              <TabsList className="bg-muted/50 p-1 border border-border">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Overview</TabsTrigger>
                <TabsTrigger value="prompts" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Prompts</TabsTrigger>
                <TabsTrigger value="answer-gap" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">Answer Gap</TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-3">
                {/* <TimeFilter selected={timePeriod} onSelect={setTimePeriod} /> */}
              </div>
            </div>
          )}

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6 mt-0">

            {/* Competitor Cards - Show top 5 competitors, 3 per row, exclude "You" */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {realCompetitors.length > 0 ? (
                realCompetitors.slice(0, 5).map((competitor, idx) => (
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
                        </div>
                        <a
                          href={competitor.url.startsWith('http') ? competitor.url : `https://${competitor.url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-muted-foreground hover:text-primary transition-colors inline-flex items-center gap-1 group"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {competitor.url}
                          <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </a>
                      </div>
                      <div 
                        className="w-12 h-12 rounded-xl shadow-glow flex items-center justify-center font-bold text-white text-lg font-inter bg-primary"
                      >
                        #{idx + 1}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      {/* First Row */}
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Mentions</p>
                        <p className="text-xl font-bold font-inter">{competitor.mentions}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Citations</p>
                        <p className="text-xl font-bold font-inter">{competitor.citations || 0}</p>
                      </div>
                      {/* Second Row */}
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Avg Visibility</p>
                        <p className="text-xl font-bold font-inter">{competitor.visibility}%</p>
                      </div>
                      <div className="p-3 rounded-xl bg-muted/30 border border-border">
                        <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Avg Position</p>
                        <p className="text-xl font-bold font-inter">{competitor.averagePosition?.toFixed(1) || '0.0'}</p>
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
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-primary"
                          onClick={() => navigate(`/competitors/${competitor.id}`)}
                        >
                          View Details →
                        </Button>
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

            {/* Show rest of content only if there are real competitors */}
            {realCompetitors.length > 0 && (
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
                        <div className="flex items-center gap-2 mt-1">
                          <p className="text-sm text-muted-foreground">See which prompts competitors dominate</p>
                          <Badge variant="secondary" className="text-xs">
                            <MessageSquare className="h-3 w-3 mr-1" />
                            {promptCards.length} Prompts Tracked
                          </Badge>
                        </div>
                      </div>
                      <Select value={promptsLLMFilter} onValueChange={setPromptsLLMFilter}>
                        <SelectTrigger className="w-[180px]">
                          <SelectValue placeholder="All LLMs" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All LLMs</SelectItem>
                          <SelectItem value="chatgpt">ChatGPT</SelectItem>
                          <SelectItem value="gemini">Gemini</SelectItem>
                          <SelectItem value="perplexity">Perplexity</SelectItem>
                          <SelectItem value="claude">Claude</SelectItem>
                        </SelectContent>
                      </Select>
                </div>

                <div className="space-y-4">
                  {promptCards.length > 0 ? (
                    <>
                      {promptCards.map((prompt: any) => (
                    <Card key={prompt.id} className="p-5 transition-all duration-300 border border-border hover:border-primary">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium mb-2">{prompt.prompt}</h4>
                            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <Eye className="h-4 w-4" />
                              <span className="font-medium text-foreground">{prompt.total} total mentions</span>
                              {prompt.topPlatform && (
                                <>
                                  <span>•</span>
                                  <Badge variant="outline" className="text-[11px]">
                                    {prompt.topPlatform}
                                  </Badge>
                                </>
                              )}
                              <span>•</span>
                              <Badge
                                variant={prompt.isYouWinner ? "default" : "destructive"}
                                className={`text-[11px] ${prompt.isYouWinner ? 'bg-green-500 hover:bg-green-600' : ''}`}
                              >
                                Winner: {prompt.winner}
                              </Badge>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {(prompt.brands || []).map((brand: string, idx: number) => {
                            const mentionCount = (prompt.counts && prompt.counts[idx]) || 0;
                            const citationCount = (prompt.citationCounts && prompt.citationCounts[idx]) || 0;
                            const brandColor = (prompt.colors && prompt.colors[idx]) || 'hsl(var(--muted))';
                            const percentage = prompt.total > 0 ? (mentionCount / prompt.total) * 100 : 0;
                            
                            return (
                              <div key={brand} className="space-y-2">
                                <div className="flex items-center justify-between text-sm">
                                  <span className="font-medium">{brand}</span>
                                  <div className="flex items-center gap-3 text-muted-foreground">
                                    <span>{mentionCount} mentions</span>
                                    {citationCount > 0 && (
                                      <>
                                        <span>•</span>
                                        <span>{citationCount} citations</span>
                                      </>
                                    )}
                                  </div>
                                </div>
                                <div className="relative h-2 w-full overflow-hidden rounded-full bg-primary/20">
                                  <div
                                    className="h-full transition-all"
                                    style={{
                                      width: `${percentage}%`,
                                      backgroundColor: brandColor,
                                    }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </Card>
                      ))}

                      {/* Pagination Controls */}
                      {promptsTotalPages > 1 && (
                        <div className="flex items-center justify-between pt-6 border-t border-border">
                          <div className="text-sm text-muted-foreground">
                            Showing page {promptsCurrentPage} of {promptsTotalPages} ({promptsTotalCount} total results)
                          </div>
                          <div className="flex items-center gap-2">
                          <Button 
                            variant="outline" 
                              size="sm"
                              onClick={() => setPromptsCurrentPage(1)}
                              disabled={promptsCurrentPage === 1}
                          >
                              First
                          </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setPromptsCurrentPage(prev => Math.max(1, prev - 1))}
                              disabled={promptsCurrentPage === 1}
                            >
                              Previous
                            </Button>
                            <div className="flex items-center gap-1">
                              {Array.from({ length: Math.min(5, promptsTotalPages) }, (_, i) => {
                                let pageNum;
                                if (promptsTotalPages <= 5) {
                                  pageNum = i + 1;
                                } else if (promptsCurrentPage <= 3) {
                                  pageNum = i + 1;
                                } else if (promptsCurrentPage >= promptsTotalPages - 2) {
                                  pageNum = promptsTotalPages - 4 + i;
                                } else {
                                  pageNum = promptsCurrentPage - 2 + i;
                                }
                                return (
                                  <Button
                                    key={pageNum}
                                    variant={promptsCurrentPage === pageNum ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => setPromptsCurrentPage(pageNum)}
                                    className="w-10"
                                  >
                                    {pageNum}
                                  </Button>
                                );
                              })}
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setPromptsCurrentPage(prev => Math.min(promptsTotalPages, prev + 1))}
                              disabled={promptsCurrentPage === promptsTotalPages}
                            >
                              Next
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setPromptsCurrentPage(promptsTotalPages)}
                              disabled={promptsCurrentPage === promptsTotalPages}
                            >
                              Last
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-16 space-y-4">
                      <p className="text-sm text-muted-foreground text-center">
                        No prompt performance data available.
                      </p>
                      <p className="text-xs text-muted-foreground">Start analyzing prompts to see data here.</p>
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
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-sm text-muted-foreground">
                        Queries where competitors appear but you don't
                      </p>
                      <Badge variant="destructive" className="text-xs">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        {answerGapData && answerGapData.length > 0 ? answerGapData.length : 0} Gaps Identified
                      </Badge>
                    </div>
                  </div>
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
                    <div className="flex flex-col items-center justify-center py-16 space-y-4">
                      <p className="text-sm text-muted-foreground">No answer gaps identified yet.</p>
                      <p className="text-xs text-muted-foreground">Start analyzing competitors to identify gaps.</p>
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

      <GenerateContentDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        existingContent={selectedGap ? {
          title: selectedGap.query,
          targetKeywords: selectedGap.query.toLowerCase().split(' '),
          type: "guide",
          wordCount: 1500,
          priority: selectedGap.opportunity,
          source: `Answer Gap - Competitor: ${selectedGap.competitor}`,
          description: `Generate content to address this answer gap where ${selectedGap.competitor} is mentioned but you are not. Platforms: ${selectedGap.platforms ? selectedGap.platforms.join(', ') : 'Multiple'}`
        } : undefined}
      />
    </div>
  );
};

export default Competitors;
