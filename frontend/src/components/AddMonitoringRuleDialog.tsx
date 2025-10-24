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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";

interface MonitoringRule {
  id?: number;
  name: string;
  description: string;
  status: string;
  detections?: number;
  lastTriggered?: string;
}

interface AddMonitoringRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule?: MonitoringRule | null;
  onSave: (rule: MonitoringRule) => void;
}

export function AddMonitoringRuleDialog({
  open,
  onOpenChange,
  rule,
  onSave,
}: AddMonitoringRuleDialogProps) {
  const { toast } = useToast();
  const [name, setName] = useState(rule?.name || "");
  const [description, setDescription] = useState(rule?.description || "");
  const [category, setCategory] = useState("product");
  const [severity, setSeverity] = useState("medium");
  const [keywords, setKeywords] = useState<string[]>(["product name", "brand name"]);
  const [keywordInput, setKeywordInput] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["all"]);
  const [autoNotify, setAutoNotify] = useState(true);
  const [autoEscalate, setAutoEscalate] = useState(false);

  const handleAddKeyword = () => {
    if (keywordInput.trim() && !keywords.includes(keywordInput.trim())) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const handleRemoveKeyword = (keyword: string) => {
    setKeywords(keywords.filter(k => k !== keyword));
  };

  const handleSave = () => {
    if (!name.trim() || !description.trim()) {
      toast({
        title: "Missing information",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }

    const ruleData: MonitoringRule = {
      ...(rule?.id && { id: rule.id }),
      name: name.trim(),
      description: description.trim(),
      status: rule?.status || "active",
      detections: rule?.detections || 0,
      lastTriggered: rule?.lastTriggered || "Never",
    };

    onSave(ruleData);
    toast({
      title: rule ? "Rule updated" : "Rule created",
      description: `Monitoring rule "${name}" has been ${rule ? "updated" : "created"} successfully`,
    });
    onOpenChange(false);
    resetForm();
  };

  const resetForm = () => {
    setName("");
    setDescription("");
    setCategory("product");
    setSeverity("medium");
    setKeywords(["product name", "brand name"]);
    setKeywordInput("");
    setPlatforms(["all"]);
    setAutoNotify(true);
    setAutoEscalate(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{rule ? "Edit Monitoring Rule" : "Add New Monitoring Rule"}</DialogTitle>
          <DialogDescription>
            Configure automated detection rules to monitor for misinformation
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rule-name">Rule Name *</Label>
              <Input
                id="rule-name"
                placeholder="e.g., Product Information Accuracy"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="rule-description">Description *</Label>
              <Textarea
                id="rule-description"
                placeholder="Describe what this rule monitors for..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          {/* Category and Severity */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="product">Product Information</SelectItem>
                  <SelectItem value="company">Company Data</SelectItem>
                  <SelectItem value="pricing">Pricing & Plans</SelectItem>
                  <SelectItem value="leadership">Leadership & Quotes</SelectItem>
                  <SelectItem value="legal">Legal & Compliance</SelectItem>
                  <SelectItem value="technical">Technical Specifications</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="severity">Default Severity</Label>
              <Select value={severity} onValueChange={setSeverity}>
                <SelectTrigger id="severity">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Keywords */}
          <div className="space-y-2">
            <Label>Keywords to Monitor</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Add keyword or phrase..."
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleAddKeyword()}
              />
              <Button type="button" onClick={handleAddKeyword}>
                Add
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary" className="gap-1">
                  {keyword}
                  <X
                    className="h-3 w-3 cursor-pointer"
                    onClick={() => handleRemoveKeyword(keyword)}
                  />
                </Badge>
              ))}
            </div>
          </div>

          {/* Platforms */}
          <div className="space-y-2">
            <Label>Monitor on Platforms</Label>
            <div className="grid grid-cols-2 gap-2">
              {["All Platforms", "ChatGPT", "Claude", "Gemini", "Perplexity", "Copilot"].map((platform) => (
                <label key={platform} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={platforms.includes(platform.toLowerCase().replace(" ", "-"))}
                    onChange={(e) => {
                      const value = platform.toLowerCase().replace(" ", "-");
                      if (e.target.checked) {
                        setPlatforms([...platforms, value]);
                      } else {
                        setPlatforms(platforms.filter(p => p !== value));
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{platform}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Automation Settings */}
          <div className="space-y-4 p-4 bg-muted rounded-lg">
            <h4 className="font-medium">Automation Settings</h4>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="auto-notify">Auto-notify on detection</Label>
                <p className="text-xs text-muted-foreground">
                  Send immediate notification when this rule triggers
                </p>
              </div>
              <Switch
                id="auto-notify"
                checked={autoNotify}
                onCheckedChange={setAutoNotify}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="auto-escalate">Auto-escalate high severity</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically escalate to team when severity is high
                </p>
              </div>
              <Switch
                id="auto-escalate"
                checked={autoEscalate}
                onCheckedChange={setAutoEscalate}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            {rule ? "Update Rule" : "Create Rule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
