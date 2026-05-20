import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Play, Loader2, CheckCircle } from "lucide-react";

interface StartScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function StartScanDialog({
  open,
  onOpenChange,
}: StartScanDialogProps) {
  const { toast } = useToast();
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [scanComplete, setScanComplete] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([
    "chatgpt",
    "claude",
    "gemini",
    "perplexity",
  ]);
  const [scanResults, setScanResults] = useState({
    totalScanned: 0,
    issuesFound: 0,
    newCases: 0,
  });

  const platforms = [
    { id: "chatgpt", name: "ChatGPT", status: "online" },
    { id: "claude", name: "Claude", status: "online" },
    { id: "gemini", name: "Gemini", status: "online" },
    { id: "perplexity", name: "Perplexity", status: "online" },
    { id: "grok", name: "Grok", status: "online" },
    { id: "deepseek", name: "DeepSeek", status: "online" },
    { id: "copilot", name: "Microsoft Copilot", status: "online" },
  ];

  const handlePlatformToggle = (platformId: string) => {
    if (selectedPlatforms.includes(platformId)) {
      setSelectedPlatforms(selectedPlatforms.filter(p => p !== platformId));
    } else {
      setSelectedPlatforms([...selectedPlatforms, platformId]);
    }
  };

  const handleStartScan = () => {
    if (selectedPlatforms.length === 0) {
      toast({
        title: "No platforms selected",
        description: "Please select at least one platform to scan",
        variant: "destructive",
      });
      return;
    }

    setScanning(true);
    setProgress(0);
    setScanComplete(false);

    // Simulate scanning progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setScanning(false);
          setScanComplete(true);
          setScanResults({
            totalScanned: 247,
            issuesFound: 12,
            newCases: 3,
          });
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const handleClose = () => {
    if (scanComplete) {
      toast({
        title: "Scan complete",
        description: `Found ${scanResults.issuesFound} potential issues across ${scanResults.totalScanned} mentions`,
      });
    }
    setScanning(false);
    setProgress(0);
    setScanComplete(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Start Misinformation Scan
          </DialogTitle>
          <DialogDescription>
            Scan AI platforms for potential misinformation about your brand
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {!scanning && !scanComplete && (
            <>
              {/* Platform Selection */}
              <div className="space-y-3">
                <Label>Select Platforms to Scan</Label>
                <div className="space-y-2">
                  {platforms.map((platform) => (
                    <div
                      key={platform.id}
                      className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent cursor-pointer"
                      onClick={() => handlePlatformToggle(platform.id)}
                    >
                      <div className="flex items-center gap-3">
                        <Checkbox
                          checked={selectedPlatforms.includes(platform.id)}
                          onCheckedChange={() => handlePlatformToggle(platform.id)}
                        />
                        <div>
                          <p className="font-medium">{platform.name}</p>
                          <p className="text-xs text-muted-foreground">
                            Scan responses and citations
                          </p>
                        </div>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {platform.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Scan Options */}
              <div className="p-4 bg-muted rounded-lg space-y-2">
                <h4 className="font-medium text-sm">Scan Configuration</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Scan Depth</p>
                    <p className="font-medium">Comprehensive</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Time Range</p>
                    <p className="font-medium">Last 7 days</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Rules Active</p>
                    <p className="font-medium">4 rules</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Est. Duration</p>
                    <p className="font-medium">~2 minutes</p>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Scanning Progress */}
          {scanning && (
            <div className="space-y-4">
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Scanning platforms...</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
              <div className="text-center text-sm text-muted-foreground">
                Analyzing responses across {selectedPlatforms.length} platforms
              </div>
            </div>
          )}

          {/* Scan Complete */}
          {scanComplete && (
            <div className="space-y-4">
              <div className="flex items-center justify-center py-6">
                <div className="h-16 w-16 rounded-full bg-success/10 flex items-center justify-center">
                  <CheckCircle className="h-8 w-8 text-success" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-semibold mb-2">Scan Complete</h3>
                <p className="text-sm text-muted-foreground">
                  Successfully scanned {scanResults.totalScanned} mentions across {selectedPlatforms.length} platforms
                </p>
              </div>
              <div className="grid grid-cols-3 gap-4 py-4">
                <div className="text-center p-4 bg-muted rounded-lg">
                  <p className="text-2xl font-bold">{scanResults.totalScanned}</p>
                  <p className="text-xs text-muted-foreground">Total Scanned</p>
                </div>
                <div className="text-center p-4 bg-warning/10 rounded-lg">
                  <p className="text-2xl font-bold text-warning">{scanResults.issuesFound}</p>
                  <p className="text-xs text-muted-foreground">Issues Found</p>
                </div>
                <div className="text-center p-4 bg-destructive/10 rounded-lg">
                  <p className="text-2xl font-bold text-destructive">{scanResults.newCases}</p>
                  <p className="text-xs text-muted-foreground">New Cases</p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={scanning}>
            {scanComplete ? "Close" : "Cancel"}
          </Button>
          {!scanning && !scanComplete && (
            <Button onClick={handleStartScan} disabled={selectedPlatforms.length === 0}>
              <Play className="h-4 w-4 mr-2" />
              Start Scan
            </Button>
          )}
          {scanComplete && (
            <Button onClick={handleClose}>
              View Results
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
