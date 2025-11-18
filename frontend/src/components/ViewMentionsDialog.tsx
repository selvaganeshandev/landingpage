import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { MessageSquare, ExternalLink, Loader2 } from "lucide-react";

interface ViewMentionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  competitorId: number;
  competitorName: string;
  domainId: string;
}

export const ViewMentionsDialog = ({
  open,
  onOpenChange,
  competitorId,
  competitorName,
  domainId,
}: ViewMentionsDialogProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [mentions, setMentions] = useState<any[]>([]);

  useEffect(() => {
    const fetchMentions = async () => {
      if (!open || !domainId) return;

      setIsLoading(true);
      const startTime = performance.now();
      console.log('⏱️ ViewMentionsDialog - Starting to fetch mentions for competitor:', competitorId);

      try {
        // Fetch with competitor_id filter and large page size
        // Backend now supports page_size parameter (max 1000) and is_mentioned filter
        const apiStartTime = performance.now();
        const data = await apiClient.getCompetitorPromptAnalyticsEngine({
          domain_id: domainId,
          competitor_id: String(competitorId),
          is_mentioned: 'true', // Filter at backend for performance (only mentioned rows)
          page_size: '1000', // Request all results in one call
        });

        const apiTime = ((performance.now() - apiStartTime) / 1000).toFixed(2);
        const allRows = data?.results || [];
        console.log(`⏱️ API call took ${apiTime}s - Fetched ${allRows.length} relevant rows (backend filtered by is_mentioned=true)`);

        // Backend now filters by is_mentioned=true, so all rows are relevant
        // Just verify data structure and log for debugging
        if (allRows.length > 0) {
          console.log('🔍 Sample rows:', allRows.slice(0, 3));
        }

        const relevantRows = allRows; // All rows from backend are already relevant

        // Group by prompt and sum mention counts across all platforms
        const promptMap = new Map();
        relevantRows.forEach((mention: any) => {
          const promptId = mention?.prompt;
          const promptText = mention?.prompt_text || `Prompt #${promptId}`;
          const count = Number(mention?.mention_count || 0);

          if (!promptMap.has(promptId)) {
            promptMap.set(promptId, {
              id: promptId,
              prompt: promptText,
              mentionCount: count,
            });
          } else {
            // If same prompt appears on multiple platforms, sum the counts
            const existing = promptMap.get(promptId);
            existing.mentionCount += count;
          }
        });

        const formattedMentions = Array.from(promptMap.values())
          .filter(m => m.mentionCount > 0)  // Only show prompts where competitor is mentioned
          .sort((a, b) => b.mentionCount - a.mentionCount);

        const processingTime = ((performance.now() - startTime) / 1000 - parseFloat(apiTime)).toFixed(2);
        console.log(`⏱️ Processing took ${processingTime}s`);
        console.log('✅ ViewMentionsDialog - Final formatted mentions:', formattedMentions.length, 'unique prompts');
        if (formattedMentions.length > 0) {
          console.log('📊 Top mentions:', formattedMentions.slice(0, 5).map(m => `${m.prompt.substring(0, 60)}: ${m.mentionCount}`));
        }

        setMentions(formattedMentions);
      } catch (error: any) {
        console.error('Failed to load competitor mentions:', error);
        toast({
          title: 'Failed to Load Mentions',
          description: error?.message || 'Could not fetch competitor mentions.',
          variant: 'destructive',
        });
      } finally {
        const totalTime = ((performance.now() - startTime) / 1000).toFixed(2);
        console.log(`✅ ViewMentionsDialog - Total time: ${totalTime}s`);
        setIsLoading(false);
      }
    };

    fetchMentions();
  }, [open, competitorId, domainId, toast]);

  const handleViewPrompt = (promptId: number) => {
    onOpenChange(false);
    navigate(`/prompts/${promptId}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="text-2xl">
            Prompts Mentioning {competitorName}
          </DialogTitle>
          <DialogDescription>
            View all prompts where {competitorName} is mentioned and analyze their performance.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[500px] pr-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : mentions.length > 0 ? (
            <div className="space-y-3">
              {mentions.map((mention, index) => (
                <div
                  key={mention.id || index}
                  className="p-5 rounded-xl border border-border hover:border-primary transition-all bg-card/50 hover:shadow-md"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-medium text-foreground leading-relaxed mb-2">
                          {mention.prompt}
                        </p>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            <MessageSquare className="h-3 w-3 mr-1" />
                            {mention.mentionCount} {mention.mentionCount === 1 ? 'mention' : 'mentions'}
                          </Badge>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border border-border hover:border-primary hover:bg-primary/5 flex-shrink-0"
                        onClick={() => handleViewPrompt(mention.id)}
                      >
                        <ExternalLink className="h-4 w-4 mr-2" />
                        View Prompt
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 space-y-3">
              <div className="w-16 h-16 rounded-full bg-muted/30 flex items-center justify-center">
                <MessageSquare className="h-8 w-8 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground text-center max-w-md">
                No prompts found where {competitorName} is mentioned.
              </p>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};
