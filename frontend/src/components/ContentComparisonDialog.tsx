import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { 
  CheckCircle, 
  XCircle, 
  Loader2,
  Globe,
  Brain,
  AlertTriangle
} from "lucide-react";
import { useState } from "react";

interface ContentComparisonDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ContentComparisonDialog({
  open,
  onOpenChange,
}: ContentComparisonDialogProps) {
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [prompt, setPrompt] = useState("");
  const [isScanning, setIsScanning] = useState(false);
  const [hasResults, setHasResults] = useState(false);

  // Mock data for UI demonstration
  const mockOriginalContent = "Our product is available in 15 countries worldwide and supports 8 languages. It was launched in 2020 and has over 100,000 active users.";
  const mockLlmResponse = "According to sources, this product is available in 20 countries and supports 12 languages. It was launched in 2019 and has approximately 50,000 users.";
  const mockAccuracyScore = 45;

  const handleScan = () => {
    setIsScanning(true);
    // Simulate API call
    setTimeout(() => {
      setIsScanning(false);
      setHasResults(true);
    }, 2000);
  };

  const handleReset = () => {
    setWebsiteUrl("");
    setPrompt("");
    setHasResults(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Content Comparison & Verification</DialogTitle>
          <DialogDescription>
            Compare your website content with AI model responses to detect misinformation
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Input Section */}
          <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
            <div className="space-y-2">
              <Label htmlFor="website-url">Website URL</Label>
              <div className="flex gap-2">
                <Input
                  id="website-url"
                  placeholder="https://example.com/product-info"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  disabled={isScanning || hasResults}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="test-prompt">Test Prompt (What to ask AI models)</Label>
              <Textarea
                id="test-prompt"
                placeholder="e.g., Tell me about [Your Product] availability and user base"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={3}
                disabled={isScanning || hasResults}
              />
            </div>

            <div className="flex gap-2">
              <Button 
                onClick={handleScan} 
                disabled={!websiteUrl || !prompt || isScanning || hasResults}
                className="flex-1"
              >
                {isScanning ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Scanning & Comparing...
                  </>
                ) : (
                  'Start Comparison'
                )}
              </Button>
              {hasResults && (
                <Button variant="outline" onClick={handleReset}>
                  New Comparison
                </Button>
              )}
            </div>
          </div>

          {/* Results Section */}
          {hasResults && (
            <>
              <Separator />

              {/* Accuracy Score */}
              <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                    <h3 className="font-semibold">Accuracy Score</h3>
                  </div>
                  <Badge className="bg-destructive text-destructive-foreground">
                    {mockAccuracyScore}% Match
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Significant discrepancies detected between source content and AI responses
                </p>
              </div>

              {/* Comparison Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Original Content */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-success/10 flex items-center justify-center">
                      <Globe className="h-4 w-4 text-success" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">Original Content</h3>
                      <p className="text-xs text-muted-foreground">From your website</p>
                    </div>
                  </div>
                  <div className="p-4 bg-success/5 border border-success/20 rounded-lg">
                    <p className="text-sm leading-relaxed">{mockOriginalContent}</p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-muted-foreground">Key Facts:</h4>
                    <div className="space-y-1">
                      <div className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                        <span>Available in <strong>15 countries</strong></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                        <span>Supports <strong>8 languages</strong></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                        <span>Launched in <strong>2020</strong></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <CheckCircle className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                        <span>Over <strong>100,000 active users</strong></span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* LLM Response */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-warning/10 flex items-center justify-center">
                      <Brain className="h-4 w-4 text-warning" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">AI Model Response</h3>
                      <p className="text-xs text-muted-foreground">What AI says</p>
                    </div>
                  </div>
                  <div className="p-4 bg-destructive/5 border border-destructive/20 rounded-lg">
                    <p className="text-sm leading-relaxed">{mockLlmResponse}</p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-muted-foreground">Detected Claims:</h4>
                    <div className="space-y-1">
                      <div className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-destructive mt-0.5 flex-shrink-0" />
                        <span>Available in <strong>20 countries</strong> <Badge variant="destructive" className="ml-1 text-[10px] h-4">Wrong</Badge></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-destructive mt-0.5 flex-shrink-0" />
                        <span>Supports <strong>12 languages</strong> <Badge variant="destructive" className="ml-1 text-[10px] h-4">Wrong</Badge></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-destructive mt-0.5 flex-shrink-0" />
                        <span>Launched in <strong>2019</strong> <Badge variant="destructive" className="ml-1 text-[10px] h-4">Wrong</Badge></span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <XCircle className="h-3 w-3 text-destructive mt-0.5 flex-shrink-0" />
                        <span>Approximately <strong>50,000 users</strong> <Badge variant="destructive" className="ml-1 text-[10px] h-4">Wrong</Badge></span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Actions */}
              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                <div>
                  <h4 className="text-sm font-semibold">Misinformation Detected</h4>
                  <p className="text-xs text-muted-foreground">Multiple inaccuracies found in AI responses</p>
                </div>
                <Button>Create Alert Case</Button>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
