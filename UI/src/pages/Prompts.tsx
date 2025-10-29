import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, FolderOpen, TrendingUp, Eye, Edit, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { AddPromptGroupDialog } from "@/components/AddPromptGroupDialog";
import { EditPromptGroupDialog } from "@/components/EditPromptGroupDialog";
import { GenerateVariantsDialog } from "@/components/GenerateVariantsDialog";

const promptGroups = [
  {
    id: 1,
    name: "Vegan Protein - Athletes",
    mainPrompt: "best vegan protein powder for athletes",
    variants: ["top vegan protein supplement for sports", "affordable plant-based protein", "clean vegan protein for runners"],
    mentions: 89,
    trend: 15,
  },
  {
    id: 2,
    name: "Vegan Protein - General",
    mainPrompt: "best vegan protein powder",
    variants: ["top plant-based protein", "vegan protein powder reviews", "organic vegan protein"],
    mentions: 67,
    trend: 8,
  },
  {
    id: 3,
    name: "Post-Workout Recovery",
    mainPrompt: "best post-workout vegan protein",
    variants: ["vegan recovery protein", "plant protein after workout"],
    mentions: 42,
    trend: 22,
  },
];

const Prompts = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<typeof promptGroups[0] | null>(null);

  const handleViewDetails = (groupId: number) => {
    navigate(`/prompts/${groupId}`);
  };

  const handleEditGroup = (group: typeof promptGroups[0]) => {
    setSelectedGroup(group);
    setEditDialogOpen(true);
  };

  const handleGenerateVariants = (group: typeof promptGroups[0]) => {
    setSelectedGroup(group);
    setGenerateDialogOpen(true);
  };

  const handleOrganizeGroups = () => {
    toast({
      title: "Organize Groups",
      description: "Opening group organization panel...",
    });
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div>
          <h1 className="text-4xl font-bold tracking-tight font-outfit bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Prompt Monitoring
          </h1>
          <p className="text-muted-foreground mt-2">
            Track and group prompts to monitor brand visibility
          </p>
        </div>
        <Button onClick={() => setAddDialogOpen(true)} className="gradient-primary shadow-md shadow-primary/20">
          <Plus className="h-4 w-4 mr-2" />
          Add Prompt Group
        </Button>
      </div>

      <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search prompt groups..." className="pl-10 border-border/50" />
          </div>
          <Button variant="outline" onClick={handleOrganizeGroups} className="border-border/50">
            <FolderOpen className="h-4 w-4 mr-2" />
            Organize Groups
          </Button>
        </div>
      </Card>

      <div className="grid gap-6">
        {promptGroups.map((group) => (
          <Card key={group.id} className="p-6 hover:shadow-elegant transition-all duration-300 hover:scale-[1.01] border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold font-outfit">{group.name}</h3>
                  <p className="text-sm text-muted-foreground font-mono bg-gradient-to-br from-muted/30 to-muted/50 px-3 py-2 rounded-xl inline-block border border-border/50">
                    {group.mainPrompt}
                  </p>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-3xl font-bold font-outfit">{group.mentions}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">mentions</p>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
                    <TrendingUp className="h-4 w-4 text-success" />
                    <span className="text-sm font-semibold text-success">+{group.trend}%</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Prompt Variants ({group.variants.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {group.variants.map((variant, idx) => (
                    <Badge key={idx} variant="secondary" className="font-mono text-xs px-3 py-1.5">
                      {variant}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-3 border-t border-border/50">
                <Button variant="outline" size="sm" onClick={() => handleViewDetails(group.id)} className="border-border/50">
                  <Eye className="h-4 w-4 mr-1" />
                  View Details
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEditGroup(group)} className="border-border/50">
                  <Edit className="h-4 w-4 mr-1" />
                  Edit Group
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleGenerateVariants(group)} className="border-border/50">
                  <Sparkles className="h-4 w-4 mr-1" />
                  Generate Variants
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Dialogs */}
      <AddPromptGroupDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />
      <EditPromptGroupDialog 
        open={editDialogOpen} 
        onOpenChange={setEditDialogOpen}
        promptGroup={selectedGroup}
      />
      <GenerateVariantsDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        mainPrompt={selectedGroup?.mainPrompt || ""}
      />
    </div>
  );
};

export default Prompts;
