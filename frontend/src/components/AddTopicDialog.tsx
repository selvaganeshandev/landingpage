import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface AddTopicDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (topic: any) => void;
}

export const AddTopicDialog = ({ open, onOpenChange, onAdd }: AddTopicDialogProps) => {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");

  const handleAddKeyword = () => {
    if (keywordInput.trim() && !keywords.includes(keywordInput.trim())) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const handleRemoveKeyword = (index: number) => {
    setKeywords(keywords.filter((_, i) => i !== index));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddKeyword();
    }
  };

  const handleSubmit = () => {
    if (!name.trim()) {
      toast({
        title: "Missing Topic Name",
        description: "Please provide a name for the topic.",
        variant: "destructive",
      });
      return;
    }

    if (keywords.length === 0) {
      toast({
        title: "No Keywords",
        description: "Please add at least one keyword for tracking.",
        variant: "destructive",
      });
      return;
    }

    const newTopic = {
      name: name.trim(),
      description: description.trim(),
      keywords,
      mentions: 0,
      visibility: 0,
      sentiment: 0,
      trend: 0,
      platforms: [],
    };

    if (onAdd) {
      onAdd(newTopic);
    }

    toast({
      title: "Topic Added",
      description: `"${name}" has been added to your tracking.`,
    });

    // Reset form
    setName("");
    setDescription("");
    setKeywords([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl">Add New Topic</DialogTitle>
          <DialogDescription>
            Create a custom topic to track specific categories or themes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Topic Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Topic Name*</Label>
            <Input
              id="name"
              placeholder="e.g., Recovery & Post-Workout"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-border"
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description of what this topic covers..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border border-border min-h-[80px]"
            />
          </div>

          {/* Keywords */}
          <div className="space-y-2">
            <Label htmlFor="keyword">Keywords*</Label>
            <div className="flex gap-2">
              <Input
                id="keyword"
                placeholder="Add a keyword..."
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="border border-border"
              />
              <Button type="button" onClick={handleAddKeyword} variant="outline">
                Add
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Add keywords that define this topic. Press Enter or click Add.
            </p>
            
            {keywords.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {keywords.map((keyword, idx) => (
                  <Badge
                    key={idx}
                    variant="secondary"
                    className="pl-3 pr-2 py-1.5 text-sm"
                  >
                    {keyword}
                    <button
                      onClick={() => handleRemoveKeyword(idx)}
                      className="ml-2 hover:text-destructive transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div className="p-4 rounded-lg bg-muted/30 border border-border">
            <p className="text-sm font-medium mb-1">Pro Tip</p>
            <p className="text-xs text-muted-foreground">
              Choose keywords that are specific to your topic and likely to appear in AI responses. You can always edit and refine these later.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="gradient-primary">
            Add Topic
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
