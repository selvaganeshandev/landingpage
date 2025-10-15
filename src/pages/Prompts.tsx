import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, FolderOpen, TrendingUp } from "lucide-react";

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
  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Prompt Monitoring</h1>
          <p className="text-muted-foreground mt-2">
            Track and group prompts to monitor brand visibility
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add Prompt Group
        </Button>
      </div>

      <Card className="p-6">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search prompt groups..." className="pl-10" />
          </div>
          <Button variant="outline">
            <FolderOpen className="h-4 w-4 mr-2" />
            Organize Groups
          </Button>
        </div>
      </Card>

      <div className="grid gap-6">
        {promptGroups.map((group) => (
          <Card key={group.id} className="p-6 hover:shadow-lg transition-shadow">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <h3 className="text-xl font-semibold">{group.name}</h3>
                  <p className="text-sm text-muted-foreground font-mono bg-muted px-2 py-1 rounded inline-block">
                    {group.mainPrompt}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-2xl font-bold">{group.mentions}</p>
                    <p className="text-xs text-muted-foreground">mentions</p>
                  </div>
                  <div className="flex items-center gap-1 text-success">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-sm font-medium">+{group.trend}%</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">Prompt Variants ({group.variants.length})</p>
                <div className="flex flex-wrap gap-2">
                  {group.variants.map((variant, idx) => (
                    <Badge key={idx} variant="secondary" className="font-mono text-xs">
                      {variant}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm">View Details</Button>
                <Button variant="outline" size="sm">Edit Group</Button>
                <Button variant="outline" size="sm">Generate Variants</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Prompts;
