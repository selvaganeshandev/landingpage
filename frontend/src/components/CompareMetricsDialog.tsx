import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Loader2, TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";
import { useDomainStore } from "@/stores/domainStore";

interface CompareMetricsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  competitorId: number;
  competitorName: string;
  competitorUrl: string;
}

interface MetricComparison {
  label: string;
  yourValue: number;
  competitorValue: number;
  difference: number;
  percentageDiff: number;
  unit: string;
  higherIsBetter: boolean;
}

export const CompareMetricsDialog = ({
  open,
  onOpenChange,
  competitorId,
  competitorName,
  competitorUrl,
}: CompareMetricsDialogProps) => {
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [isLoading, setIsLoading] = useState(false);
  const [yourBrandName, setYourBrandName] = useState("");
  const [metrics, setMetrics] = useState<MetricComparison[]>([]);

  useEffect(() => {
    const fetchComparisonData = async () => {
      if (!open || !selectedDomain?.id) return;

      setIsLoading(true);

      try {
        // Fetch competitor details
        const competitorData = await apiClient.getEngineCompetitorDetail(competitorId);

        // Fetch your brand's data from domain
        const domainData = await apiClient.getDomain(selectedDomain.id);
        setYourBrandName(domainData.name || selectedDomain.name);

        // Fetch all competitors to calculate total market share
        const allCompetitorsResponse = await apiClient.getCompetitorsByDomain(selectedDomain.id);
        const allCompetitors = Array.isArray(allCompetitorsResponse) ? allCompetitorsResponse : [];

        // Fetch Share of Voice data which includes your brand's metrics
        const sovResponse = await apiClient.getShareOfVoice({ domain_id: selectedDomain.id });
        const sovData = sovResponse?.results || sovResponse || [];
        const sovArray = Array.isArray(sovData) ? sovData : [];
        const yourBrandSOV = sovArray.find((item: any) => item.competitor === null || item.is_your_brand === true);

        // Use SOV data for your brand's share of voice
        const yourSOV = parseFloat(yourBrandSOV?.share_percentage || 0);

        // Use SOV data which already has your brand's aggregated metrics
        const yourMentions = yourBrandSOV?.mention_count || 0;

        // Get citation count from heatmap or use mention count as estimate
        const yourCitations = Math.floor(yourMentions * 0.8); // Estimate: ~80% of mentions have citations

        // Fetch competitor metric snapshots which might have your brand's data
        const snapshotsResponse = await apiClient.getCompetitorMetricSnapshots({
          domain_id: selectedDomain.id,
          days: 30
        });
        const snapshots = snapshotsResponse?.results || [];
        const yourBrandSnapshot = snapshots.find((s: any) => s.competitor === null);

        // Use snapshot data if available, otherwise use defaults
        const yourAvgPosition = yourBrandSnapshot?.average_position ? parseFloat(yourBrandSnapshot.average_position) : 2.5;
        const yourAvgSentiment = yourBrandSnapshot?.sentiment_score ? parseFloat(yourBrandSnapshot.sentiment_score) : 0.5;

        const yourVisibility = yourBrandSnapshot?.visibility_score
          ? parseFloat(yourBrandSnapshot.visibility_score)
          : (yourAvgPosition > 0 ? Math.max(0, Math.min(100, 100 - (yourAvgPosition * 20))) : 50);

        const yourSentimentPercent = yourAvgSentiment * 100;

        // Build comparison metrics
        const comparisons: MetricComparison[] = [
          {
            label: "Total Mentions",
            yourValue: yourMentions,
            competitorValue: competitorData.total_mentions || 0,
            difference: yourMentions - (competitorData.total_mentions || 0),
            percentageDiff: competitorData.total_mentions > 0
              ? ((yourMentions - competitorData.total_mentions) / competitorData.total_mentions) * 100
              : 0,
            unit: "",
            higherIsBetter: true,
          },
          {
            label: "Citations",
            yourValue: yourCitations,
            competitorValue: competitorData.total_citations || 0,
            difference: yourCitations - (competitorData.total_citations || 0),
            percentageDiff: competitorData.total_citations > 0
              ? ((yourCitations - competitorData.total_citations) / competitorData.total_citations) * 100
              : 0,
            unit: "",
            higherIsBetter: true,
          },
          {
            label: "Share of Voice",
            yourValue: yourSOV,
            competitorValue: parseFloat(competitorData.share_of_voice_percentage || 0),
            difference: yourSOV - parseFloat(competitorData.share_of_voice_percentage || 0),
            percentageDiff: competitorData.share_of_voice_percentage > 0
              ? ((yourSOV - parseFloat(competitorData.share_of_voice_percentage)) / parseFloat(competitorData.share_of_voice_percentage)) * 100
              : 0,
            unit: "%",
            higherIsBetter: true,
          },
          {
            label: "Average Position",
            yourValue: yourAvgPosition,
            competitorValue: parseFloat(competitorData.average_position || 0),
            difference: yourAvgPosition - parseFloat(competitorData.average_position || 0),
            percentageDiff: competitorData.average_position > 0
              ? ((yourAvgPosition - parseFloat(competitorData.average_position)) / parseFloat(competitorData.average_position)) * 100
              : 0,
            unit: "",
            higherIsBetter: false, // Lower is better for position
          },
          {
            label: "Visibility Score",
            yourValue: yourVisibility,
            competitorValue: parseFloat(competitorData.visibility_score || 0),
            difference: yourVisibility - parseFloat(competitorData.visibility_score || 0),
            percentageDiff: competitorData.visibility_score > 0
              ? ((yourVisibility - parseFloat(competitorData.visibility_score)) / parseFloat(competitorData.visibility_score)) * 100
              : 0,
            unit: "%",
            higherIsBetter: true,
          },
          {
            label: "Sentiment Score",
            yourValue: yourSentimentPercent,
            competitorValue: parseFloat(competitorData.sentiment_score || 0) * 100,
            difference: yourSentimentPercent - (parseFloat(competitorData.sentiment_score || 0) * 100),
            percentageDiff: (competitorData.sentiment_score || 0) > 0
              ? ((yourSentimentPercent - (parseFloat(competitorData.sentiment_score) * 100)) / (parseFloat(competitorData.sentiment_score) * 100)) * 100
              : 0,
            unit: "%",
            higherIsBetter: true,
          },
        ];

        setMetrics(comparisons);
      } catch (error: any) {
        console.error('Failed to load comparison data:', error);
        toast({
          title: 'Failed to Load Comparison',
          description: error?.message || error?.toString() || 'Could not fetch comparison data.',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchComparisonData();
  }, [open, competitorId, selectedDomain, toast]);

  const getDifferenceIcon = (metric: MetricComparison) => {
    const isPositive = metric.higherIsBetter
      ? metric.difference > 0
      : metric.difference < 0;

    if (Math.abs(metric.difference) < 0.01) {
      return <Minus className="h-4 w-4 text-muted-foreground" />;
    }

    if (isPositive) {
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    }

    return <TrendingDown className="h-4 w-4 text-red-500" />;
  };

  const getDifferenceColor = (metric: MetricComparison) => {
    const isPositive = metric.higherIsBetter
      ? metric.difference > 0
      : metric.difference < 0;

    if (Math.abs(metric.difference) < 0.01) {
      return "text-muted-foreground";
    }

    return isPositive ? "text-green-600" : "text-red-600";
  };

  const formatValue = (value: number, unit: string) => {
    if (unit === "%") {
      return `${value.toFixed(1)}%`;
    }
    return value.toFixed(0);
  };

  const formatDifference = (metric: MetricComparison) => {
    const sign = metric.difference > 0 ? "+" : "";
    if (metric.unit === "%") {
      return `${sign}${metric.difference.toFixed(1)}%`;
    }
    return `${sign}${metric.difference.toFixed(0)}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="text-xl">
            Metrics Comparison: {yourBrandName} vs {competitorName}
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="h-[500px] pr-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : metrics.length > 0 ? (
            <div className="space-y-4">
              {/* Table */}
              <div className="border border-border rounded-lg overflow-hidden">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-semibold text-sm">Metric</th>
                      <th className="text-center py-3 px-4 font-semibold text-sm text-primary">
                        {yourBrandName}
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-sm text-orange-600">
                        {competitorName}
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-sm">Difference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((metric, index) => (
                      <tr
                        key={index}
                        className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                      >
                        {/* Metric Label */}
                        <td className="py-3 px-4 font-medium text-sm">
                          {metric.label}
                        </td>

                        {/* Your Value */}
                        <td className="py-3 px-4 text-center">
                          <span className="inline-flex items-center justify-center px-3 py-1 rounded-md bg-primary/10 text-primary font-semibold text-sm">
                            {formatValue(metric.yourValue, metric.unit)}
                          </span>
                        </td>

                        {/* Competitor Value */}
                        <td className="py-3 px-4 text-center">
                          <span className="inline-flex items-center justify-center px-3 py-1 rounded-md bg-orange-500/10 text-orange-600 font-semibold text-sm">
                            {formatValue(metric.competitorValue, metric.unit)}
                          </span>
                        </td>

                        {/* Difference */}
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center gap-2">
                            {getDifferenceIcon(metric)}
                            <div className="flex flex-col items-start">
                              <span className={`font-semibold text-sm ${getDifferenceColor(metric)}`}>
                                {formatDifference(metric)}
                              </span>
                              {Math.abs(metric.percentageDiff) > 0.1 && (
                                <span className={`text-xs ${getDifferenceColor(metric)}`}>
                                  ({metric.percentageDiff > 0 ? "+" : ""}{metric.percentageDiff.toFixed(0)}%)
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Summary */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  <span className="text-sm text-muted-foreground">Ahead:</span>
                  <span className="font-bold text-green-600">
                    {metrics.filter(m => m.higherIsBetter ? m.difference > 0 : m.difference < 0).length}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <TrendingDown className="h-5 w-5 text-orange-600" />
                  <span className="text-sm text-muted-foreground">Behind:</span>
                  <span className="font-bold text-orange-600">
                    {metrics.filter(m => m.higherIsBetter ? m.difference < 0 : m.difference > 0).length}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Minus className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Equal:</span>
                  <span className="font-bold text-muted-foreground">
                    {metrics.filter(m => Math.abs(m.difference) < 0.01).length}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 space-y-3">
              <p className="text-sm text-muted-foreground text-center max-w-md">
                No comparison data available.
              </p>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
