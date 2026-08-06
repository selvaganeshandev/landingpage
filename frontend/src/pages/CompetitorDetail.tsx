import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TimeFilter } from "@/components/TimeFilter";
import { PageLoader } from "@/components/PageLoader";
import { ViewMentionsDialog } from "@/components/ViewMentionsDialog";
import { CompareMetricsDialog } from "@/components/CompareMetricsDialog";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Building2,
  ExternalLink,
  Share2,
  FileText,
  Target,
  MessageSquare,
  ArrowLeftRight,
  Lightbulb,
  AlertTriangle,
  Download,
  Loader2,
  Trash2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { getActiveDomainId } from "@/utils/activeDomain";
import { useDomainStore } from "@/stores/domainStore";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell
} from "recharts";

// The page charts a 30-day window by default; the export covers everything on
// record, so it re-fetches the time-scoped calls over a range wide enough to
// reach the first snapshot and walks the paginated prompt table to its end.
const EXPORT_DAYS = 3650;
const EXPORT_PROMPT_PAGE_SIZE = 200;
const EXPORT_MAX_PROMPT_PAGES = 100;

const CompetitorDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const { selectedDomain } = useDomainStore();
  const [timePeriod, setTimePeriod] = useState("30");
  const [activeTab, setActiveTab] = useState("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [competitor, setCompetitor] = useState<any>(null);
  const [domainId, setDomainId] = useState<string | null>(null);
  const [mentionTrend, setMentionTrend] = useState<any[]>([]);
  const [marketRank, setMarketRank] = useState<number | null>(null);
  const [viewMentionsDialogOpen, setViewMentionsDialogOpen] = useState(false);
  const [compareMetricsDialogOpen, setCompareMetricsDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [platformBreakdown, setPlatformBreakdown] = useState<any[]>([]);
  const [sentimentData, setSentimentData] = useState([
    { name: "Positive", value: 0, color: "hsl(var(--success))" },
    { name: "Neutral", value: 0, color: "hsl(var(--warning))" },
    { name: "Negative", value: 0, color: "hsl(var(--destructive))" },
  ]);
  const [topMentions, setTopMentions] = useState<any[]>([]);
  const [swotInsights, setSwotInsights] = useState<{
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    threats: string[];
  }>({
    strengths: [],
    weaknesses: [],
    opportunities: [],
    threats: [],
  });

  // Sync domainId from selectedDomain or localStorage
  useEffect(() => {
    if (!user) return;

    if (selectedDomain?.id) {
      const newDomainId = String(selectedDomain.id);
      if (newDomainId !== domainId) {
        setDomainId(newDomainId);
      }
    } else {
      const serverActiveDomain = getActiveDomainId(user);
      const serverDomainId = serverActiveDomain || '';
      if (serverDomainId !== domainId) {
        setDomainId(serverDomainId);
      }
    }
  }, [user, selectedDomain?.id, domainId]);

  // Fetch competitor data
  useEffect(() => {
    const fetchCompetitor = async () => {
      if (!id || !domainId) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        // Fetch competitor details, trend data, all competitors, and prompt analytics in parallel
        const [data, snapshotData, allCompetitors, promptAnalytics]: any[] = await Promise.all([
          apiClient.getEngineCompetitorDetail(Number(id)),
          apiClient.getCompetitorMetricSnapshots({
            domain_id: domainId,
            competitor_id: id,
            days: Number(timePeriod)
          }),
          apiClient.getEngineCompetitors({ domain_id: domainId }),
          apiClient.getCompetitorPromptAnalyticsEngine({
            domain_id: domainId,
            competitor_id: id,
            is_mentioned: 'true',
            page_size: '1000' // Get enough data to calculate accurate sentiment breakdown
          })
        ]);

        // Convert sentiment_score from -1 to 1 range to 0-100 percentage for display
        const rawSentiment = Number(data.sentiment_score || 0);
        const totalMentions = Number(data.total_mentions || 0);
        let sentimentPercent = 0;
        if (rawSentiment === -1 || (rawSentiment === 0 && totalMentions === 0)) {
          sentimentPercent = 0; // No data or unmentioned
        } else {
          sentimentPercent = Math.round((rawSentiment + 1) * 50);
        }

        setCompetitor({
          id: data.id,
          name: data.name || 'Unknown',
          url: data.url || data.domain_name || '',
          logo: data.name ? data.name.charAt(0).toUpperCase() : '?',
          mentions: data.total_mentions || 0,
          citations: data.total_citations || 0,
          visibility: Math.round(Number(data.visibility_score || 0)),
          sentiment: sentimentPercent,
          avgPosition: Number(data.average_position || 0),
          shareOfVoice: Math.round(Number(data.share_of_voice_percentage || 0)),
          trend: Number(data.trend_percentage || 0),
          description: data.description || `${data.name} - Competitor analysis and performance tracking.`,
        });

        let computedMentionTrend: any[] = [];
        // Process snapshot data for the trend chart
        const snapshots = Array.isArray(snapshotData) ? snapshotData : snapshotData?.results || [];
        if (snapshots.length > 0) {
          const trendData = snapshots.map((snap: any) => {
            const date = new Date(snap.timestamp || snap.created_at);
            const monthLabel = date.toLocaleDateString('en-US', { month: 'short' });

            return {
              month: monthLabel,
              mentions: Number(snap.total_mentions || 0),
              position: Number(snap.average_position || 0),
              date: date.getTime() // for sorting
            };
          });

          // Sort by date and remove duplicates (keep latest for each month)
          const sortedTrend = trendData
            .sort((a, b) => a.date - b.date)
            .reduce((acc: any[], curr) => {
              const existingIndex = acc.findIndex(item => item.month === curr.month);
              if (existingIndex >= 0) {
                // Replace with newer data for same month
                acc[existingIndex] = curr;
              } else {
                acc.push(curr);
              }
              return acc;
            }, [])
            .map(({ date, ...rest }) => rest); // Remove date field before setting

          computedMentionTrend = sortedTrend;
          setMentionTrend(sortedTrend);
        } else {
          computedMentionTrend = [];
          setMentionTrend([]);
        }

        // Calculate platform breakdown from the latest snapshot
        let computedPlatformBreakdown: any[] = [];
        if (snapshots.length > 0) {
          // Sort snapshots by timestamp (most recent first) to ensure we get the latest
          const sortedSnapshots = [...snapshots].sort((a: any, b: any) => {
            const dateA = new Date(a.timestamp || a.created_at || 0).getTime();
            const dateB = new Date(b.timestamp || b.created_at || 0).getTime();
            return dateB - dateA; // Descending order (newest first)
          });
          const latestSnapshot = sortedSnapshots[0]; // Most recent snapshot
          const platformMetrics = latestSnapshot.platform_metrics || [];

          if (Array.isArray(platformMetrics) && platformMetrics.length > 0) {
            // Calculate total mentions across all platforms
            const totalPlatformMentions = platformMetrics.reduce((sum: number, pm: any) => {
              return sum + (Number(pm.mentions) || 0);
            }, 0);

            // Build platform breakdown with percentages
            const breakdown = platformMetrics
              .filter((pm: any) => (Number(pm.mentions) || 0) > 0) // Only platforms with mentions
              .map((pm: any) => ({
                platform: pm.platform || 'Unknown',
                mentions: Number(pm.mentions) || 0,
                percentage: totalPlatformMentions > 0
                  ? Number(((Number(pm.mentions) / totalPlatformMentions) * 100).toFixed(1))
                  : 0
              }))
              .sort((a, b) => b.mentions - a.mentions); // Sort by mentions desc

            computedPlatformBreakdown = breakdown;
            setPlatformBreakdown(breakdown);
          } else {
            computedPlatformBreakdown = [];
            setPlatformBreakdown([]);
          }
        } else {
          computedPlatformBreakdown = [];
          setPlatformBreakdown([]);
        }

        // Calculate market rank based on share of voice
        const competitors = Array.isArray(allCompetitors) ? allCompetitors : allCompetitors?.results || [];
        if (competitors.length > 0) {
          // Sort competitors by share of voice (descending) or mentions if share of voice is not available
          const sortedCompetitors = competitors
            .map((c: any) => ({
              id: c.id,
              shareOfVoice: Number(c.share_of_voice_percentage || 0),
              mentions: Number(c.total_mentions || 0)
            }))
            .sort((a, b) => {
              // Primary sort by share of voice, fallback to mentions
              if (b.shareOfVoice !== a.shareOfVoice) {
                return b.shareOfVoice - a.shareOfVoice;
              }
              return b.mentions - a.mentions;
            });

          // Find the rank (1-indexed)
          const rank = sortedCompetitors.findIndex(c => c.id === Number(id)) + 1;
          setMarketRank(rank > 0 ? rank : null);
        } else {
          setMarketRank(null);
        }

        // Calculate top prompts for competitor across all LLMs.
        //
        // The list endpoint groups its results by prompt —
        // {prompt_id, prompt_text, analytics: [...]} — with the per-platform
        // readings one level down in `analytics`. Flatten to one row per
        // reading, carrying the prompt identity down with it, so the
        // aggregation below sees the fields it expects.
        const compPromptGroups = Array.isArray(promptAnalytics) ? promptAnalytics : promptAnalytics?.results || [];
        const compAnalytics = compPromptGroups.flatMap((group: any) =>
          (Array.isArray(group.analytics) ? group.analytics : []).map((entry: any) => ({
            ...entry,
            promptId: group.prompt_id,
            promptText: group.prompt_text || '',
          }))
        );

        // Aggregate prompts by prompt_id to combine data across all LLMs
        const promptMap = new Map();
        compAnalytics.forEach((item: any) => {
          // Only process items where competitor is mentioned
          if (!item.is_mentioned) {
            return;
          }
          
          const promptId = item.promptId;
          const promptText = item.promptText;

          // Skip if we don't have both promptId and promptText
          if (!promptId || !promptText) {
            return;
          }

          const existing = promptMap.get(promptId) || {
            prompt: promptText,
            promptId: promptId,
            totalMentions: 0,
            totalCitations: 0,
            bestPosition: Infinity,
            platforms: new Set(),
            sentiments: new Set()
          };

          // Try multiple possible field names for mention_count
          const mentionCount = Number(item.mention_count || item.total_mentions || item.mentions || 0);
          existing.totalMentions += mentionCount;
          
          // Try multiple possible field names for citations
          let citations = 0;
          if (item.citation_list) {
            citations = Array.isArray(item.citation_list) ? item.citation_list.length : 0;
          } else if (item.total_citations) {
            citations = Number(item.total_citations);
          } else if (item.citations) {
            citations = Number(item.citations);
          }
          existing.totalCitations += citations;
          
          // Try multiple possible field names for position
          const position = item.position ? Number(item.position) : null;
          if (position && position > 0 && position < existing.bestPosition) {
            existing.bestPosition = position;
          }
          
          if (item.platform) {
            existing.platforms.add(item.platform);
          }
          
          if (item.sentiment_category || item.sentiment) {
            existing.sentiments.add(item.sentiment_category || item.sentiment);
          }

          promptMap.set(promptId, existing);
        });

        // Convert to array and calculate performance score
        const topPrompts = Array.from(promptMap.values())
          .filter(p => p.totalMentions > 0)
          .map(p => ({
            prompt: p.prompt,
            position: p.bestPosition !== Infinity ? p.bestPosition : null,
            platforms: Array.from(p.platforms),
            sentiment: Array.from(p.sentiments)[0] || 'neutral', // Use first sentiment or default
            mentions: p.totalMentions,
            citations: p.totalCitations,
            performanceScore: (p.totalMentions * 2) + p.totalCitations + (p.bestPosition !== Infinity ? (100 - p.bestPosition * 10) : 0)
          }));

        // Sort by performance score and take top 5
        topPrompts.sort((a, b) => b.performanceScore - a.performanceScore);
        const topPromptSlice = topPrompts.slice(0, 5);
        setTopMentions(topPromptSlice);

        // Build SWOT insights
        const competitorSummary = {
          id: data.id,
          visibility: Math.round(Number(data.visibility_score || 0)),
          sentiment: Math.round((Number(data.sentiment_score || 0) + 1) * 50),
          avgPosition: Number(data.average_position || 0),
          citations: data.total_citations || 0,
          shareOfVoice: Math.round(Number(data.share_of_voice_percentage || 0)),
          trend: Number(data.trend_percentage || 0),
          totalMentions: data.total_mentions || 0,
        };
        const computedSwot = buildSwotInsights({
          competitorData: competitorSummary,
          platformBreakdown: computedPlatformBreakdown,
          mentionTrend: computedMentionTrend,
          topPrompts,
          competitorsList: Array.isArray(allCompetitors) ? allCompetitors : allCompetitors?.results || [],
        });
        setSwotInsights(computedSwot);

        // Calculate sentiment breakdown from prompt analytics
        const analytics = compAnalytics;
        if (analytics.length > 0) {
          // Count mentions by sentiment category
          let positiveCount = 0;
          let neutralCount = 0;
          let negativeCount = 0;

          analytics.forEach((item: any) => {
            const mentionCount = Number(item.mention_count || 0);
            const sentimentCategory = (item.sentiment_category || '').toLowerCase();
            
            if (sentimentCategory === 'positive') {
              positiveCount += mentionCount;
            } else if (sentimentCategory === 'neutral') {
              neutralCount += mentionCount;
            } else if (sentimentCategory === 'negative') {
              negativeCount += mentionCount;
            }
          });

          // Calculate percentages
          const totalMentions = positiveCount + neutralCount + negativeCount;
          if (totalMentions > 0) {
            // Calculate raw percentages
            const positivePctRaw = (positiveCount / totalMentions) * 100;
            const neutralPctRaw = (neutralCount / totalMentions) * 100;
            const negativePctRaw = (negativeCount / totalMentions) * 100;
            
            // Round to ensure they sum to 100%
            let positivePct = Math.round(positivePctRaw);
            let neutralPct = Math.round(neutralPctRaw);
            let negativePct = Math.round(negativePctRaw);
            
            // Adjust to ensure sum equals 100%
            const sum = positivePct + neutralPct + negativePct;
            if (sum !== 100) {
              // Adjust the largest value to make sum = 100
              const diff = 100 - sum;
              if (positivePct >= neutralPct && positivePct >= negativePct) {
                positivePct += diff;
              } else if (neutralPct >= negativePct) {
                neutralPct += diff;
              } else {
                negativePct += diff;
              }
            }

            setSentimentData([
              { name: "Positive", value: positivePct, color: "hsl(var(--success))" },
              { name: "Neutral", value: neutralPct, color: "hsl(var(--warning))" },
              { name: "Negative", value: negativePct, color: "hsl(var(--destructive))" },
            ]);
          } else {
            // No mentions, set to zero
            setSentimentData([
              { name: "Positive", value: 0, color: "hsl(var(--success))" },
              { name: "Neutral", value: 0, color: "hsl(var(--warning))" },
              { name: "Negative", value: 0, color: "hsl(var(--destructive))" },
            ]);
          }
        } else {
          // No analytics data, set to zero
          setSentimentData([
            { name: "Positive", value: 0, color: "hsl(var(--success))" },
            { name: "Neutral", value: 0, color: "hsl(var(--warning))" },
            { name: "Negative", value: 0, color: "hsl(var(--destructive))" },
          ]);
        }
      } catch (error: any) {
        console.error('Failed to load competitor details:', error);
        toast({
          title: 'Failed to Load Competitor',
          description: error?.message || 'Could not fetch competitor details.',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchCompetitor();
  }, [id, domainId, timePeriod, toast]);

  const handleShare = () => {
    toast({
      title: "Share Link Generated",
      description: "Competitor profile link copied to clipboard.",
    });
  };

  /**
   * Export this competitor's full record as a multi-sheet workbook.
   *
   * The charts above are scoped to the selected time period; the export is not,
   * so the snapshot and prompt calls are re-issued over the full range. Prompt
   * rows are rebuilt from the API response rather than read out of page state:
   * the list endpoint returns prompts grouped as
   * `{prompt_id, prompt_text, analytics: [...]}`, and the per-prompt figures
   * live one level down in `analytics`. Sheets with no rows are skipped.
   */
  const handleExport = async () => {
    if (!id || !domainId || !competitor) {
      toast({
        title: "Export failed",
        description: "Competitor data is not loaded yet.",
        variant: "destructive",
      });
      return;
    }

    setIsExporting(true);
    try {
      const XLSX = await import("xlsx");

      const snapshotData: any = await apiClient.getCompetitorMetricSnapshots({
        domain_id: domainId,
        competitor_id: id,
        days: EXPORT_DAYS,
      });

      // Walk every page of this competitor's prompts. The page cap is a runaway
      // guard — if it bites, the Summary sheet says so rather than letting a
      // partial file read as complete.
      const promptGroups: any[] = [];
      let promptPage = 1;
      let promptTotalPages = 1;
      let promptsTruncated = false;
      while (promptPage <= promptTotalPages) {
        if (promptPage > EXPORT_MAX_PROMPT_PAGES) {
          promptsTruncated = true;
          break;
        }
        const res: any = await apiClient.getCompetitorPromptAnalyticsEngine({
          domain_id: domainId,
          competitor_id: id,
          page_size: String(EXPORT_PROMPT_PAGE_SIZE),
          page: promptPage,
        });
        const batch = Array.isArray(res) ? res : res?.results || [];
        promptGroups.push(...batch);
        promptTotalPages = Array.isArray(res) ? 1 : Number(res?.total_pages || 1);
        promptPage += 1;
      }

      const promptRows: any[] = [];
      promptGroups.forEach((group: any) => {
        (Array.isArray(group.analytics) ? group.analytics : []).forEach((a: any) => {
          promptRows.push({
            Prompt: group.prompt_text || "",
            Platform: a.platform || "",
            Mentioned: a.is_mentioned ? "Yes" : "No",
            Mentions: Number(a.mention_count ?? (a.is_mentioned ? 1 : 0)),
            Citations: Array.isArray(a.citation_list) ? a.citation_list.length : 0,
            Position: a.position ?? "",
            Sentiment: a.sentiment_category || "",
            "Sentiment score": Number(a.sentiment_score || 0),
            "Tracked at": a.tracked_at ? new Date(a.tracked_at).toLocaleString() : "",
          });
        });
      });

      // Per-prompt totals across every platform, strongest first.
      const perPrompt = new Map<string, { mentions: number; citations: number; platforms: Set<string> }>();
      promptGroups.forEach((group: any) => {
        (Array.isArray(group.analytics) ? group.analytics : []).forEach((a: any) => {
          if (!a.is_mentioned) return;
          const key = group.prompt_text || "";
          if (!key) return;
          const held = perPrompt.get(key) || { mentions: 0, citations: 0, platforms: new Set<string>() };
          held.mentions += Number(a.mention_count || 0);
          held.citations += Array.isArray(a.citation_list) ? a.citation_list.length : 0;
          if (a.platform) held.platforms.add(a.platform);
          perPrompt.set(key, held);
        });
      });
      const topPromptRows = Array.from(perPrompt.entries())
        .map(([prompt, agg]) => ({
          Prompt: prompt,
          Mentions: agg.mentions,
          Citations: agg.citations,
          Platforms: Array.from(agg.platforms).join(", "),
        }))
        .sort((a, b) => b.Mentions - a.Mentions);

      // Sentiment split, weighted by mention count, over the full history.
      const sentimentTotals: Record<string, number> = { positive: 0, neutral: 0, negative: 0 };
      promptGroups.forEach((group: any) => {
        (Array.isArray(group.analytics) ? group.analytics : []).forEach((a: any) => {
          const category = String(a.sentiment_category || "").toLowerCase();
          if (category in sentimentTotals) {
            sentimentTotals[category] += Number(a.mention_count || 0);
          }
        });
      });
      const sentimentTotal = Object.values(sentimentTotals).reduce((sum, n) => sum + n, 0);

      const snapshots: any[] = Array.isArray(snapshotData) ? snapshotData : snapshotData?.results || [];
      const sortedSnapshots = [...snapshots].sort((a: any, b: any) =>
        new Date(a.timestamp || a.created_at || 0).getTime() -
        new Date(b.timestamp || b.created_at || 0).getTime());
      const latestSnapshot = sortedSnapshots[sortedSnapshots.length - 1];
      const latestPlatformMetrics: any[] = Array.isArray(latestSnapshot?.platform_metrics)
        ? latestSnapshot.platform_metrics
        : [];
      const latestPlatformTotal = latestPlatformMetrics.reduce(
        (sum: number, pm: any) => sum + Number(pm.mentions || 0), 0);

      const wb = XLSX.utils.book_new();

      const summarySheet: any[][] = [
        ["Competitor Report", ""],
        ["Competitor", competitor.name],
        ["Website", competitor.url || ""],
        ["Domain", selectedDomain?.name || ""],
        ["Coverage", "Full history — unfiltered by time period"],
        ["Generated", new Date().toLocaleString()],
        ["", ""],
        ["Metric", "Value"],
        ["Market rank", marketRank ?? "Not ranked"],
        ["Total mentions", competitor.mentions],
        ["Total citations", competitor.citations],
        ["Visibility score", competitor.visibility],
        ["Sentiment (%)", competitor.sentiment],
        ["Average position", competitor.avgPosition],
        ["Share of voice (%)", competitor.shareOfVoice],
        ["Trend (%)", competitor.trend],
        ["", ""],
        ["Metric snapshots", snapshots.length],
        ["Prompts covered", promptGroups.length],
        ["Prompt analytics rows", promptRows.length],
      ];
      if (promptsTruncated) {
        summarySheet.push(["", ""]);
        summarySheet.push([
          "Note",
          `Prompt export stopped at ${EXPORT_MAX_PROMPT_PAGES * EXPORT_PROMPT_PAGE_SIZE} prompts — this file does not contain every prompt on record.`,
        ]);
      }
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summarySheet), "Summary");

      if (sortedSnapshots.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(
          sortedSnapshots.map((snap: any) => ({
            Date: String(snap.timestamp || snap.created_at || "").split("T")[0],
            Mentions: Number(snap.total_mentions || 0),
            Citations: Number(snap.total_citations || 0),
            "Visibility score": Number(snap.visibility_score || 0),
            "Sentiment score": Number(snap.sentiment_score || 0),
            "Avg position": Number(snap.average_position || 0),
            "Share of voice (%)": Number(snap.share_of_voice_percentage || 0),
          })),
        ), "Metric History");
      }

      if (latestPlatformMetrics.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(
          latestPlatformMetrics.map((pm: any) => ({
            Platform: pm.platform || "Unknown",
            Mentions: Number(pm.mentions || 0),
            Citations: Number(pm.citations || 0),
            "Share (%)": latestPlatformTotal > 0
              ? Number(((Number(pm.mentions || 0) / latestPlatformTotal) * 100).toFixed(1))
              : 0,
            "As of": String(latestSnapshot?.timestamp || latestSnapshot?.created_at || "").split("T")[0],
          })),
        ), "Platform Distribution");
      }

      if (sentimentTotal > 0) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(
          ["positive", "neutral", "negative"].map((category) => ({
            Sentiment: category.charAt(0).toUpperCase() + category.slice(1),
            Mentions: sentimentTotals[category],
            "Share (%)": Number(((sentimentTotals[category] / sentimentTotal) * 100).toFixed(1)),
          })),
        ), "Sentiment");
      }

      if (topPromptRows.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(topPromptRows), "Top Prompts");
      }

      if (promptRows.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(promptRows), "Prompt Analytics");
      }

      const swotRows = (["strengths", "weaknesses", "opportunities", "threats"] as const)
        .flatMap((bucket) =>
          (swotInsights[bucket] || []).map((point: string) => ({
            Category: bucket.charAt(0).toUpperCase() + bucket.slice(1),
            Insight: point,
          })));
      if (swotRows.length) {
        XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(swotRows), "SWOT");
      }

      const safeName = (competitor.name || "competitor").replace(/[^a-z0-9]+/gi, "_");
      const today = new Date().toISOString().split("T")[0];
      XLSX.writeFile(wb, `competitor_${safeName}_${today}.xlsx`);

      toast({
        title: "Export ready",
        description: promptsTruncated
          ? `Downloaded ${wb.SheetNames.length} sheets. Prompt data was capped — see the Summary sheet.`
          : `Downloaded ${wb.SheetNames.length} sheet${wb.SheetNames.length === 1 ? "" : "s"} for ${competitor.name}.`,
      });
    } catch (error: any) {
      console.error("Competitor export failed:", error);
      toast({
        title: "Export failed",
        description: error?.message || "Could not build the workbook.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteCompetitor = async () => {
    if (!competitor || deleteConfirmText !== competitor.name) {
      return;
    }

    setIsDeleting(true);
    try {
      await apiClient.deleteCompetitor(Number(id));
      toast({
        title: "Competitor Deleted",
        description: `${competitor.name} has been successfully deleted.`,
      });
      setDeleteDialogOpen(false);
      navigate("/competitors");
    } catch (error: any) {
      console.error("Failed to delete competitor:", error);
      toast({
        title: "Delete Failed",
        description: error?.message || "Could not delete the competitor. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const renderSwotList = (items: string[], emptyText: string) => {
    if (!items || items.length === 0) {
      return <p className="text-sm text-muted-foreground">{emptyText}</p>;
    }

    return (
      <ul className="space-y-2">
        {items.map((item, idx) => (
          <li key={idx} className="text-sm flex items-start gap-2">
            <span className="mt-1 text-foreground">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    );
  };

  // Helper function to format URL with protocol
  const formatUrl = (url: string) => {
    if (!url) return '#';
    // Check if URL already has a protocol
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Add https:// if no protocol exists
    return `https://${url}`;
  };

  // Show loading state
  if (isLoading || !competitor) {
    return <PageLoader sidebarOpen />;
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="space-y-4 pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              onClick={() => navigate(-1)}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl border-2 border-border shadow-lg flex items-center justify-center bg-card overflow-hidden">
                {competitor.url ? (
                  <img
                    src={getFaviconUrl(competitor.url, 64)}
                    alt={`${competitor.name} favicon`}
                    className="w-10 h-10 object-contain"
                    onError={(e) => handleFaviconError(e, competitor.url, competitor.name, 64)}
                  />
                ) : (
                  <span className="text-3xl font-bold text-primary">{competitor.logo}</span>
                )}
              </div>
              <div>
                <h1 className="text-4xl font-bold tracking-tight">{competitor.name}</h1>
                <p className="text-muted-foreground mt-2">{competitor.url}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={handleExport} disabled={isExporting}>
              {isExporting
                ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                : <Download className="h-4 w-4 mr-2" />}
              {isExporting ? "Exporting..." : "Export to Excel"}
            </Button>
            <Button
              variant="ghost"
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => {
                setDeleteConfirmText("");
                setDeleteDialogOpen(true);
              }}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Competitor
            </Button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Mentions</p>
            <p className="text-4xl font-bold font-inter">{competitor.mentions}</p>
            <div className="flex items-center gap-2">
              {competitor.trend > 0 ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
              <span className={`text-sm font-semibold ${competitor.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
              </span>
            </div>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Citations</p>
            <p className="text-4xl font-bold font-inter">{competitor.citations || 0}</p>
            <p className="text-sm text-muted-foreground">Source references</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Share of Voice</p>
            <p className="text-4xl font-bold font-inter">{competitor.shareOfVoice}%</p>
            <p className="text-sm text-muted-foreground">Market share</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-inter">{competitor.avgPosition?.toFixed(1) || '0.0'}</p>
            <p className="text-sm text-muted-foreground">Across all platforms</p>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Visibility</p>
            <p className="text-4xl font-bold font-inter">{competitor.visibility}%</p>
            <Progress value={competitor.visibility} className="h-2" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Mention Trends */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border">
                <h3 className="text-lg font-semibold font-inter">Mention Volume & Position Trends</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Track mention frequency and average position over time
                </p>
              </div>
              {mentionTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mentionTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                    <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "var(--radius)",
                      }}
                    />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="mentions"
                      name="Mentions"
                      stroke="hsl(var(--primary))"
                      strokeWidth={3}
                      dot={{ fill: "hsl(var(--primary))", r: 4 }}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="position"
                      name="Avg Position"
                      stroke="hsl(var(--chart-2))"
                      strokeWidth={2}
                      dot={{ fill: "hsl(var(--chart-2))", r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[300px]">
                  <p className="text-sm text-muted-foreground">No trend data available for the selected period.</p>
                </div>
              )}
            </div>
          </Card>

          {/* Platform Breakdown */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border">
                <h3 className="text-lg font-semibold font-inter">Platform Distribution</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Mention breakdown across AI platforms
                </p>
              </div>
              {platformBreakdown.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={platformBreakdown}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ platform, percentage }) => `${platform} ${percentage}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="mentions"
                      >
                        {platformBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={`hsl(var(--chart-${index + 1}))`} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-3">
                    {platformBreakdown.map((platform, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border">
                        <div className="flex items-center gap-3">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: `hsl(var(--chart-${idx + 1}))` }} />
                          <span className="font-medium">{platform.platform}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-bold font-inter">{platform.mentions}</p>
                          <p className="text-xs text-muted-foreground">{platform.percentage}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-[250px]">
                  <div className="text-center space-y-2">
                    <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground/30" />
                    <p className="text-sm text-muted-foreground">No platform data available</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Tabs Section */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="bg-muted/50 p-1 border border-border mb-6">
                <TabsTrigger value="overview" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Overview
                </TabsTrigger>
                <TabsTrigger value="mentions" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  Top Mentions
                </TabsTrigger>
                <TabsTrigger value="swot" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                  SWOT Analysis
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div>
                  <h3 className="text-lg font-semibold mb-3 font-inter">About {competitor.name}</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    Competitive analysis and performance metrics for {competitor.name}.
                  </p>
                </div>
                {sentimentData.length > 0 && (
                  <div className="pt-4">
                    <h3 className="text-lg font-semibold mb-4 font-inter">Sentiment Distribution</h3>
                    <div className="grid grid-cols-3 gap-4">
                      {sentimentData.map((item) => (
                        <div key={item.name} className="p-4 rounded-xl border border-border bg-muted/30">
                          <p className="text-sm text-muted-foreground mb-2">{item.name}</p>
                          <p className="text-3xl font-bold font-inter">{item.value}%</p>
                          <Progress value={item.value} className="h-2 mt-2" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="mentions" className="space-y-2">
                {topMentions.length > 0 ? (
                  topMentions.map((mention, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl border border-border/80 bg-card/70 hover:border-primary transition-all"
                    >
                      <div className="space-y-2">
                        <div>
                          <div className="flex items-center gap-1.5 mb-1 flex-wrap text-xs">
                            {mention.platforms.map((platform: string, pIdx: number) => (
                              <Badge key={pIdx} variant="outline" className="px-2 py-0.5 text-[11px]">
                                {platform}
                              </Badge>
                            ))}
                            <Badge variant="secondary" className="capitalize px-2 py-0.5 text-[11px]">
                              {mention.sentiment}
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-foreground line-clamp-2">{mention.prompt}</p>
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border/60">
                          <span className="flex items-center gap-2 font-medium text-foreground">
                            <span>{mention.mentions} mentions</span>
                            <span className="text-border">|</span>
                            <span>{mention.citations} citations</span>
                          </span>
                        </div>
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center border border-border rounded-xl bg-muted/30">
                    <MessageSquare className="h-10 w-10 mx-auto text-muted-foreground/30 mb-2" />
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      No prompts found for {competitor.name}.
                    </p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="swot" className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-xl border border-success/20 bg-success/5">
                    <h4 className="font-semibold mb-3 font-inter text-success flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Strengths
                    </h4>
                    {renderSwotList(swotInsights.strengths, "Not enough data to detect strengths yet.")}
                  </div>
                  <div className="p-5 rounded-xl border border-warning/20 bg-warning/5">
                    <h4 className="font-semibold mb-3 font-inter text-warning flex items-center gap-2">
                      <Target className="h-4 w-4" />
                      Weaknesses
                    </h4>
                    {renderSwotList(swotInsights.weaknesses, "No clear weaknesses identified so far.")}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-5 rounded-xl border border-primary/20 bg-primary/5">
                    <h4 className="font-semibold mb-3 font-inter text-primary flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Opportunities
                    </h4>
                    {renderSwotList(swotInsights.opportunities, "No immediate opportunities detected.")}
                  </div>
                  <div className="p-5 rounded-xl border border-destructive/20 bg-destructive/5">
                    <h4 className="font-semibold mb-3 font-inter text-destructive flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Threats
                    </h4>
                    {renderSwotList(swotInsights.threats, "No major threats at the moment.")}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Stats</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Sentiment Score</span>
                <span className={`text-lg font-bold font-inter ${
                  competitor.sentiment >= 60 ? 'text-success' :
                  competitor.sentiment >= 40 ? 'text-warning' :
                  'text-destructive'
                }`}>
                  {competitor.sentiment}%
                </span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Market Rank</span>
                <span className="text-lg font-bold font-inter">
                  {marketRank ? `#${marketRank}` : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <span className="text-sm text-muted-foreground">Total Citations</span>
                <span className="text-lg font-bold font-inter">{competitor.citations || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Growth Trend</span>
                <span className={`text-lg font-bold font-inter ${
                  competitor.trend > 0 ? 'text-success' :
                  competitor.trend < 0 ? 'text-destructive' :
                  'text-muted-foreground'
                }`}>
                  {competitor.trend > 0 ? '+' : ''}{competitor.trend}%
                </span>
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
            <h3 className="text-lg font-semibold mb-4 font-inter">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="outline" className="w-full justify-start border border-border" asChild>
                <a href={formatUrl(competitor.url)} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Visit Website
                </a>
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start border border-border"
                onClick={() => setViewMentionsDialogOpen(true)}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                View All Mentions
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start border border-border"
                onClick={() => setCompareMetricsDialogOpen(true)}
              >
                <ArrowLeftRight className="h-4 w-4 mr-2" />
                Compare Metrics
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* View Mentions Dialog */}
      <ViewMentionsDialog
        open={viewMentionsDialogOpen}
        onOpenChange={setViewMentionsDialogOpen}
        competitorId={Number(id)}
        competitorName={competitor.name}
        domainId={domainId || ''}
      />

      {/* Compare Metrics Dialog */}
      <CompareMetricsDialog
        open={compareMetricsDialogOpen}
        onOpenChange={setCompareMetricsDialogOpen}
        competitorId={Number(id)}
        competitorName={competitor.name}
        competitorUrl={competitor.url}
      />

      {/* Delete Competitor Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Delete Competitor
            </DialogTitle>
            <DialogDescription className="pt-2">
              This action cannot be undone. This will permanently delete{" "}
              <strong>{competitor.name}</strong> and all associated analytics data.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="confirm-name">
                Type <strong>{competitor.name}</strong> to confirm:
              </Label>
              <Input
                id="confirm-name"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="Enter competitor name"
                className="w-full"
              />
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteCompetitor}
              disabled={deleteConfirmText !== competitor.name || isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete Competitor"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CompetitorDetail;

type SwotBuilderInput = {
  competitorData: {
    id: number;
    visibility: number;
    sentiment: number;
    avgPosition: number;
    citations: number;
    shareOfVoice: number;
    trend: number;
    totalMentions: number;
  };
  platformBreakdown: Array<{ platform: string; mentions: number; percentage: number }>;
  mentionTrend: Array<{ month: string; mentions: number }>;
  topPrompts: Array<{ prompt: string; mentions: number; citations: number }>;
  competitorsList: any[];
};

const buildSwotInsights = ({
  competitorData,
  platformBreakdown,
  mentionTrend,
  topPrompts,
  competitorsList,
}: SwotBuilderInput) => {
  const strengths: string[] = [];
  const weaknesses: string[] = [];
  const opportunities: string[] = [];
  const threats: string[] = [];

  const addItem = (list: string[], text?: string) => {
    if (text && !list.includes(text)) {
      list.push(text);
    }
  };

  // Strengths
  if (competitorData.visibility >= 70) {
    addItem(strengths, `High visibility score (${competitorData.visibility}%) across AI platforms.`);
  }
  if (competitorData.sentiment >= 60) {
    addItem(strengths, `Positive brand sentiment at ${competitorData.sentiment}%.`);
  }
  if (platformBreakdown.length > 0) {
    const topPlatform = platformBreakdown[0];
    addItem(strengths, `Dominates on ${topPlatform.platform} with ${topPlatform.percentage}% of mentions.`);
  }
  const mentionTrendGrowth =
    mentionTrend.length >= 2
      ? mentionTrend[mentionTrend.length - 1].mentions - mentionTrend[mentionTrend.length - 2].mentions
      : 0;
  if (mentionTrendGrowth > 0) {
    addItem(strengths, `Mention volume is rising (+${mentionTrendGrowth} vs previous period).`);
  }

  // Weaknesses
  if (competitorData.citations < 5) {
    addItem(weaknesses, `Citation footprint is limited (${competitorData.citations} references).`);
  }
  if (competitorData.sentiment < 50) {
    addItem(weaknesses, `Sentiment trends toward neutral/negative (${competitorData.sentiment}%).`);
  }
  if (competitorData.avgPosition > 5) {
    addItem(weaknesses, `Average ranking position ${competitorData.avgPosition.toFixed(1)} trails top results.`);
  }
  const lowPlatform = platformBreakdown.find((p) => p.percentage > 0 && p.percentage < 10);
  if (lowPlatform) {
    addItem(weaknesses, `Low visibility on ${lowPlatform.platform} (only ${lowPlatform.percentage}% share).`);
  }

  // Opportunities
  const citationGapPrompt = topPrompts.find((p) => p.citations === 0 && p.mentions >= 5);
  if (citationGapPrompt) {
    addItem(
      opportunities,
      `Add supporting citations for "${citationGapPrompt.prompt}" to capture more authority.`
    );
  }
  if (platformBreakdown.length > 1) {
    const trailingPlatform = platformBreakdown[platformBreakdown.length - 1];
    if (trailingPlatform.percentage <= 5) {
      addItem(
        opportunities,
        `Expand presence on ${trailingPlatform.platform}, currently only ${trailingPlatform.percentage}% of mentions.`
      );
    }
  }
  if (competitorData.shareOfVoice < 20) {
    addItem(
      opportunities,
      `Share of voice is ${competitorData.shareOfVoice}% — campaigns here could quickly grow mindshare.`
    );
  }
  if (mentionTrendGrowth <= 0 && mentionTrend.length > 1) {
    addItem(opportunities, "Recent mention volume plateaued — a fresh push could restart growth.");
  }

  // Threats
  const sortedCompetitors = [...competitorsList]
    .map((c: any) => ({
      id: c.id,
      name: c.name,
      shareOfVoice: Number(c.share_of_voice_percentage || 0),
      sentiment: c.sentiment_score ? Math.round((Number(c.sentiment_score) + 1) * 50) : 0,
    }))
    .sort((a, b) => b.shareOfVoice - a.shareOfVoice);

  const marketLeader = sortedCompetitors.find((c) => c.id !== competitorData.id);
  if (marketLeader && marketLeader.shareOfVoice > competitorData.shareOfVoice + 5) {
    addItem(
      threats,
      `${marketLeader.name} leads share of voice by ${(
        marketLeader.shareOfVoice - competitorData.shareOfVoice
      ).toFixed(1)} points.`
    );
  }
  if (competitorData.trend < 0) {
    addItem(threats, `Mention growth down ${Math.abs(competitorData.trend)}% this period.`);
  }
  const sentimentLeader = sortedCompetitors.find(
    (c) => c.id !== competitorData.id && c.sentiment > competitorData.sentiment + 5
  );
  if (sentimentLeader) {
    addItem(
      threats,
      `${sentimentLeader.name} enjoys stronger sentiment (${sentimentLeader.sentiment}%) with audiences.`
    );
  }

  const limitList = (list: string[]) => list.slice(0, 4);

  return {
    strengths: limitList(strengths),
    weaknesses: limitList(weaknesses),
    opportunities: limitList(opportunities),
    threats: limitList(threats),
  };
};
