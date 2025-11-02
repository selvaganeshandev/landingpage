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
import { useToast } from "@/hooks/use-toast";
import { Building2 } from "lucide-react";

interface AddCompetitorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (competitor: any) => void;
}

export const AddCompetitorDialog = ({ open, onOpenChange, onAdd }: AddCompetitorDialogProps) => {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = () => {
    if (!name.trim() || !website.trim()) {
      toast({
        title: "Missing Information",
        description: "Please provide competitor name and website.",
        variant: "destructive",
      });
      return;
    }

    const newCompetitor = {
      name: name.trim(),
      website: website.trim(),
      description: description.trim(),
    };

    if (onAdd) {
      onAdd(newCompetitor);
    }

    toast({
      title: "Competitor Added",
      description: `"${name}" has been added to tracking. Analysis will begin shortly.`,
    });

    // Reset form
    setName("");
    setWebsite("");
    setDescription("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Building2 className="h-6 w-6 text-primary" />
            Add Competitor
          </DialogTitle>
          <DialogDescription>
            Add a new competitor to track and benchmark against
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Competitor Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Competitor Name*</Label>
            <Input
              id="name"
              placeholder="e.g., Competitor Brand"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-border"
            />
          </div>

          {/* Website */}
          <div className="space-y-2">
            <Label htmlFor="website">Website*</Label>
            <Input
              id="website"
              type="url"
              placeholder="e.g., competitor.com"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              className="border border-border"
            />
            <p className="text-xs text-muted-foreground">
              Enter the main domain (without https://)
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Brief description or notes about this competitor..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="border border-border min-h-[80px]"
            />
          </div>

          <div className="p-4 rounded-lg bg-muted/30 border border border-border">
            <p className="text-sm font-medium mb-1">What happens next?</p>
            <p className="text-xs text-muted-foreground">
              Our AI will start tracking mentions of this competitor across all monitored platforms. 
              Initial data will be available within 24-48 hours.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="gradient-primary">
            Add Competitor
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
