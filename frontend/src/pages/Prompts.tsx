import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, FolderOpen, TrendingUp, Eye, Edit, Sparkles, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { AddPromptGroupDialog } from "@/components/AddPromptGroupDialog";
import { EditPromptGroupDialog } from "@/components/EditPromptGroupDialog";
import { GenerateVariantsDialog } from "@/components/GenerateVariantsDialog";

const Prompts = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const [promptGroups, setPromptGroups] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadPromptGroups();
  }, [searchQuery]);

  const loadPromptGroups = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getPromptGroups({
        search: searchQuery || undefined
      });
      setPromptGroups(response.groups);
    } catch (error: any) {
      toast({
        title: "Error loading prompt groups",
        description: error.message || "Failed to load prompt groups",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDetails = (groupId: number) => {
    navigate(`/prompts/${groupId}`);
  };

  const handleEditGroup = (group: typeof promptGroups[0]) => {
    console.log("Edit Group clicked for:", group);
    setSelectedGroup(group);
    setEditDialogOpen(true);
  };

  const handleGenerateVariants = (group: typeof promptGroups[0]) => {
    console.log("Generate Variants clicked for:", group);
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
            <Input 
              placeholder="Search prompt groups..." 
              className="pl-10 border-border/50"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="outline" onClick={handleOrganizeGroups} className="border-border/50">
            <FolderOpen className="h-4 w-4 mr-2" />
            Organize Groups
          </Button>
        </div>
      </Card>

      <div className="grid gap-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : promptGroups.length > 0 ? (
          promptGroups.map((group) => (
          <Card key={group.id} className="p-6 hover:shadow-elegant transition-all duration-300 hover:scale-[1.01] border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-5">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold font-outfit">Group {group.group_id}</h3>
                  <p className="text-sm text-muted-foreground font-mono bg-gradient-to-br from-muted/30 to-muted/50 px-3 py-2 rounded-xl inline-block border border-border/50">
                    Domain: {group.domain_name}
                  </p>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-3xl font-bold font-outfit">{group.total_mentions}</p>
                    <p className="text-xs text-muted-foreground uppercase tracking-wider">mentions</p>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-success/10 border border-success/20">
                    <TrendingUp className="h-4 w-4 text-success" />
                    <span className="text-sm font-semibold text-success">Avg: {group.average_position}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Prompts ({group.prompts_count || 0})
                </p>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="secondary" className="font-mono text-xs px-3 py-1.5">
                    Created: {new Date(group.created_at).toLocaleDateString()}
                  </Badge>
                  <Badge variant="outline" className="font-mono text-xs px-3 py-1.5">
                    Citations: {group.total_citations}
                  </Badge>
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
        ))
        ) : (
          <Card className="p-12 text-center">
            <FolderOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Prompt Groups Found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery ? "No groups match your search criteria." : "Create your first prompt group to get started."}
            </p>
            {!searchQuery && (
              <Button onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Prompt Group
              </Button>
            )}
          </Card>
        )}
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
        promptGroup={selectedGroup}
      />
    </div>
  );
};

export default Prompts;
