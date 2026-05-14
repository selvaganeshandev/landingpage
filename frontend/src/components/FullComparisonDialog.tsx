import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import {
  ExternalLink,
  FileText,
  Globe,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
  MessageSquare,
} from "lucide-react";

interface FullComparisonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  alertId: number | null;
}

interface ComparisonData {
  alert: {
    id: number;
    alert_type: string;
    severity: string;
    status: string;
    llm_claim: string;
    source_content_snippet: string;
    explanation: string;
    created_at: string;
  };
  prompt: {
    id: number | null;
    text: string | null;
  };
  llm_response: {
    platform: string | null;
    full_response: string | null;
  };
  source: {
    url: string | null;
    crawl_status: string | null;
    page_title: string | null;
    meta_description: string | null;
    full_content: string | null;
  };
}

const alertTypeLabels: Record<string, string> = {
  misinformation: "Misinformation",
  broken_link: "Broken Link",
  outdated: "Outdated Information",
};

const platformLabels: Record<string, string> = {
  chatgpt: "ChatGPT",
  claude: "Claude",
  gemini: "Gemini",
  perplexity: "Perplexity",
  grok: "Grok",
  deepseek: "DeepSeek",
};

export function FullComparisonDialog({
  open,
  onOpenChange,
  alertId,
}: FullComparisonDialogProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ComparisonData | null>(null);
  const [activeTab, setActiveTab] = useState("side-by-side");
  const [copiedLLM, setCopiedLLM] = useState(false);
  const [copiedSource, setCopiedSource] = useState(false);

  useEffect(() => {
    if (open && alertId) {
      fetchComparisonData();
    }
  }, [open, alertId]);

  const fetchComparisonData = async () => {
    if (!alertId) return;

    setLoading(true);
    try {
      const response = await apiClient.getMisinformationAlertComparison(alertId);
      setData(response as ComparisonData);
    } catch (error: any) {
      toast({
        title: "Error loading comparison",
        description: error.message || "Failed to load comparison data",
        variant: "destructive",
      });
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, type: "llm" | "source") => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === "llm") {
        setCopiedLLM(true);
        setTimeout(() => setCopiedLLM(false), 2000);
      } else {
        setCopiedSource(true);
        setTimeout(() => setCopiedSource(false), 2000);
      }
      toast({
        title: "Copied to clipboard",
        description: "Content has been copied to your clipboard",
      });
    } catch {
      toast({
        title: "Failed to copy",
        description: "Could not copy to clipboard",
        variant: "destructive",
      });
    }
  };

  if (!alertId) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[95vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-xl mb-1">
                Full Content Comparison
              </DialogTitle>
              <DialogDescription>
                Compare the AI response with the actual source content
              </DialogDescription>
            </div>
            {data && (
              <Badge
                variant="secondary"
                className="bg-primary/10 text-primary"
              >
                {alertTypeLabels[data.alert.alert_type] || data.alert.alert_type}
              </Badge>
            )}
          </div>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : data ? (
          <div className="flex-1 overflow-hidden flex flex-col">
            {/* Alert Summary */}
            {data.alert.explanation && (
              <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg mb-4">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-warning">
                      Issue Detected
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {data.alert.explanation}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Prompt Context */}
            {data.prompt.text && (
              <div className="mb-4">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Prompt</span>
                  {data.llm_response.platform && (
                    <Badge variant="outline" className="text-xs">
                      {platformLabels[data.llm_response.platform] ||
                        data.llm_response.platform}
                    </Badge>
                  )}
                </div>
                <div className="p-3 bg-muted/50 rounded-lg text-sm">
                  {data.prompt.text}
                </div>
              </div>
            )}

            <Separator className="mb-4" />

            {/* Tabs for viewing modes */}
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <TabsList className="bg-muted/50 p-1 border border-border mb-4">
                <TabsTrigger
                  value="side-by-side"
                  className="data-[state=active]:bg-background"
                >
                  Side by Side
                </TabsTrigger>
                <TabsTrigger
                  value="llm-response"
                  className="data-[state=active]:bg-background"
                >
                  LLM Response
                </TabsTrigger>
                <TabsTrigger
                  value="source-content"
                  className="data-[state=active]:bg-background"
                >
                  Source Content
                </TabsTrigger>
              </TabsList>

              {/* Side by Side View */}
              <TabsContent
                value="side-by-side"
                className="flex-1 overflow-hidden m-0"
              >
                <div className="grid grid-cols-2 gap-4 h-[400px]">
                  {/* LLM Response Column */}
                  <div className="flex flex-col border border-destructive/30 rounded-lg overflow-hidden h-full">
                    <div className="flex items-center justify-between p-3 bg-destructive/10 border-b border-destructive/30 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-destructive" />
                        <span className="text-sm font-medium">LLM Response</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          handleCopy(data.llm_response.full_response || "", "llm")
                        }
                        disabled={!data.llm_response.full_response}
                      >
                        {copiedLLM ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="flex-1 overflow-auto p-4">
                      {data.llm_response.full_response ? (
                        <p className="text-sm whitespace-pre-wrap">
                          {data.llm_response.full_response}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground italic">
                          No LLM response available
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Source Content Column */}
                  <div className="flex flex-col border border-success/30 rounded-lg overflow-hidden h-full">
                    <div className="flex items-center justify-between p-3 bg-success/10 border-b border-success/30 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-success" />
                        <span className="text-sm font-medium">Source Content</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {data.source.url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              window.open(data.source.url!, "_blank")
                            }
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            handleCopy(data.source.full_content || "", "source")
                          }
                          disabled={!data.source.full_content}
                        >
                          {copiedSource ? (
                            <Check className="h-4 w-4" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                    {data.source.page_title && (
                      <div className="p-3 border-b border-success/20 bg-success/5 flex-shrink-0">
                        <p className="text-xs text-muted-foreground">
                          Page Title
                        </p>
                        <p className="text-sm font-medium">
                          {data.source.page_title}
                        </p>
                      </div>
                    )}
                    <div className="flex-1 overflow-auto p-4">
                      {data.source.full_content ? (
                        <p className="text-sm whitespace-pre-wrap">
                          {data.source.full_content}
                        </p>
                      ) : (
                        <p className="text-sm text-muted-foreground italic">
                          {data.source.crawl_status === "failed"
                            ? "Failed to crawl source content"
                            : data.source.crawl_status === "blocked"
                            ? "Source blocked crawling"
                            : "No source content available"}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Full LLM Response View */}
              <TabsContent
                value="llm-response"
                className="flex-1 overflow-hidden m-0"
              >
                <div className="flex flex-col h-[400px] border border-destructive/30 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between p-3 bg-destructive/10 border-b border-destructive/30 flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-destructive" />
                      <span className="text-sm font-medium">
                        Full LLM Response
                      </span>
                      {data.llm_response.platform && (
                        <Badge variant="outline" className="text-xs">
                          {platformLabels[data.llm_response.platform] ||
                            data.llm_response.platform}
                        </Badge>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        handleCopy(data.llm_response.full_response || "", "llm")
                      }
                      disabled={!data.llm_response.full_response}
                    >
                      {copiedLLM ? (
                        <>
                          <Check className="h-4 w-4 mr-2" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="flex-1 overflow-auto p-4">
                    {data.llm_response.full_response ? (
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">
                        {data.llm_response.full_response}
                      </p>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <p className="text-muted-foreground italic">
                          No LLM response available
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>

              {/* Full Source Content View */}
              <TabsContent
                value="source-content"
                className="flex-1 overflow-hidden m-0"
              >
                <div className="flex flex-col h-[400px] border border-success/30 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between p-3 bg-success/10 border-b border-success/30 flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-success" />
                      <span className="text-sm font-medium">
                        Full Source Content
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {data.source.url && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(data.source.url!, "_blank")}
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Open Source
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          handleCopy(data.source.full_content || "", "source")
                        }
                        disabled={!data.source.full_content}
                      >
                        {copiedSource ? (
                          <>
                            <Check className="h-4 w-4 mr-2" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-4 w-4 mr-2" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                  {/* Source metadata */}
                  {(data.source.page_title || data.source.url) && (
                    <div className="p-3 border-b border-success/20 bg-success/5 space-y-2 flex-shrink-0">
                      {data.source.page_title && (
                        <div>
                          <p className="text-xs text-muted-foreground">
                            Page Title
                          </p>
                          <p className="text-sm font-medium">
                            {data.source.page_title}
                          </p>
                        </div>
                      )}
                      {data.source.url && (
                        <div>
                          <p className="text-xs text-muted-foreground">URL</p>
                          <a
                            href={data.source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline flex items-center gap-1"
                          >
                            <Globe className="h-3 w-3" />
                            {data.source.url}
                          </a>
                        </div>
                      )}
                      {data.source.meta_description && (
                        <div>
                          <p className="text-xs text-muted-foreground">
                            Meta Description
                          </p>
                          <p className="text-sm">{data.source.meta_description}</p>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="flex-1 overflow-auto p-4">
                    {data.source.full_content ? (
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">
                        {data.source.full_content}
                      </p>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <p className="text-muted-foreground italic">
                          {data.source.crawl_status === "failed"
                            ? "Failed to crawl source content"
                            : data.source.crawl_status === "blocked"
                            ? "Source blocked crawling"
                            : "No source content available"}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        ) : null}

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
