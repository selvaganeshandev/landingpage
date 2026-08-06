import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageSquarePlus, ArrowRight } from "lucide-react";

interface NoPromptsYetProps {
  /** What this page would show, e.g. "Competitors are found in AI answers". */
  what: string;
}

/**
 * Shown on Competitors, Topics and Misinformation when the project has no
 * prompts yet.
 *
 * All three are derived from tracked prompt responses: competitors are mined
 * out of the answers, misinformation compares cited pages against what the
 * answers claim, and topics group the keywords those runs use. With zero
 * prompts their usual empty states offer Run/Analyse buttons that can only
 * ever produce nothing — this sends the user to the one action that unblocks
 * all three instead.
 */
export const NoPromptsYet = ({ what }: NoPromptsYetProps) => (
  <div className="p-8 animate-fade-in">
    <Card className="p-12 border border-border">
      <div className="flex flex-col items-center text-center max-w-md mx-auto space-y-4">
        <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
          <MessageSquarePlus className="h-7 w-7 text-primary" />
        </div>
        <h3 className="text-xl font-semibold">Add prompts first</h3>
        <p className="text-sm text-muted-foreground">
          {what} — so this page fills in once your first prompts have been
          tracked. It happens on its own; nothing to run here.
        </p>
        <Button asChild>
          <Link to="/prompts">
            Add prompts
            <ArrowRight className="h-4 w-4 ml-2" />
          </Link>
        </Button>
      </div>
    </Card>
  </div>
);
