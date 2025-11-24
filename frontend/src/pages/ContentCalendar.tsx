import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Calendar as CalendarIcon,
  Plus,
  Sparkles,
  Clock,
  Target,
  FileText,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Edit,
  Settings,
  ArrowLeft
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";

interface ContentItem {
  id: string;
  title: string;
  type: "blog" | "guide" | "comparison" | "listicle" | "technical";
  status: "scheduled" | "draft" | "generated" | "published";
  priority: "high" | "medium" | "low";
  scheduledDate: Date;
  targetKeywords: string[];
  opportunitySource: string;
  estimatedImpact: number;
  wordCount: number;
}

const ContentCalendar = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [selectedView, setSelectedView] = useState("calendar");
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedContent, setSelectedContent] = useState<ContentItem | null>(null);

  // Mock content items with prioritization
  const [contentItems] = useState<ContentItem[]>([
    {
      id: "1",
      title: "Best Vegan BCAA Supplements - Complete Guide",
      type: "guide",
      status: "scheduled",
      priority: "high",
      scheduledDate: new Date(2025, 9, 20),
      targetKeywords: ["vegan bcaa", "plant-based supplements"],
      opportunitySource: "Answer Gap Analysis",
      estimatedImpact: 94,
      wordCount: 2000
    },
    {
      id: "2",
      title: "Plant Protein vs Whey: Which is Better for Athletes?",
      type: "comparison",
      status: "draft",
      priority: "high",
      scheduledDate: new Date(2025, 9, 22),
      targetKeywords: ["plant protein athletes", "vegan protein powder"],
      opportunitySource: "Competitor Weakness",
      estimatedImpact: 87,
      wordCount: 1800
    },
    {
      id: "3",
      title: "Top 10 Unflavored Plant Protein Powders in 2025",
      type: "listicle",
      status: "generated",
      priority: "high",
      scheduledDate: new Date(2025, 9, 24),
      targetKeywords: ["unflavored plant protein", "natural protein powder"],
      opportunitySource: "Answer Gap Analysis",
      estimatedImpact: 82,
      wordCount: 1500
    },
    {
      id: "4",
      title: "How to Choose Organic Plant-Based Protein Powder",
      type: "blog",
      status: "scheduled",
      priority: "medium",
      scheduledDate: new Date(2025, 9, 26),
      targetKeywords: ["organic protein powder", "plant-based nutrition"],
      opportunitySource: "High Visibility Topic",
      estimatedImpact: 76,
      wordCount: 1200
    },
    {
      id: "5",
      title: "Understanding Amino Acid Profiles in Vegan Proteins",
      type: "technical",
      status: "scheduled",
      priority: "medium",
      scheduledDate: new Date(2025, 9, 28),
      targetKeywords: ["amino acids vegan", "protein quality"],
      opportunitySource: "Content Gap",
      estimatedImpact: 68,
      wordCount: 2500
    }
  ]);

  const handleGenerateContent = () => {
    setGenerateDialogOpen(true);
  };

  const handleEditContent = (item: ContentItem) => {
    setSelectedContent(item);
    setGenerateDialogOpen(true);
  };

  // Listen for content generation requests from other pages
  useEffect(() => {
    const handleOpenGeneration = (event: CustomEvent) => {
      const params = event.detail;
      if (params) {
        setSelectedContent({
          id: Date.now().toString(),
          title: params.topic || "",
          type: params.articleType || "blog",
          status: "draft",
          priority: params.priority || "medium",
          scheduledDate: new Date(),
          targetKeywords: typeof params.keywords === 'string' ? params.keywords.split(', ') : (params.keywords || []),
          opportunitySource: params.source || "Manual",
          estimatedImpact: 75,
          wordCount: params.wordCount || 1500,
          // Pass through source tracking
          sourceType: params.sourceType,
          sourceId: params.sourceId,
          sourceReference: params.sourceReference,
          // Additional context
          competitorMentions: params.competitorMentions,
          recommendation: params.recommendation,
          frequency: params.frequency,
          platforms: params.platforms
        });
      }
      setGenerateDialogOpen(true);
    };

    window.addEventListener('openContentGeneration' as any, handleOpenGeneration);
    return () => {
      window.removeEventListener('openContentGeneration' as any, handleOpenGeneration);
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "published": return "bg-success/10 text-success";
      case "generated": return "bg-primary/10 text-primary";
      case "draft": return "bg-warning/10 text-warning";
      default: return "bg-muted text-muted-foreground";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high": return "bg-destructive/10 text-destructive border-destructive/20";
      case "medium": return "bg-warning/10 text-warning border-warning/20";
      default: return "bg-muted text-muted-foreground border-border";
    }
  };

  const getContentIcon = (type: string) => {
    switch (type) {
      case "guide": return "📖";
      case "comparison": return "⚖️";
      case "listicle": return "📋";
      case "technical": return "🔧";
      default: return "📝";
    }
  };

  const itemsForSelectedDate = contentItems.filter(
    item => selectedDate && 
    item.scheduledDate.toDateString() === selectedDate.toDateString()
  );

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-inter">Content Calendar</h1>
            <p className="text-muted-foreground mt-1">
              AI-powered content generation prioritized by opportunity
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            onClick={() => navigate('/automation')}
            className="border-border/50"
          >
            <Settings className="h-4 w-4 mr-2" />
            Automation Settings
          </Button>
          <Select defaultValue="weekly">
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Frequency" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Twice Weekly</SelectItem>
              <SelectItem value="biweekly">Weekly</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleGenerateContent} className="gradient-primary shadow-md shadow-primary/20">
            <Sparkles className="h-4 w-4 mr-2" />
            Generate Content
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Scheduled</p>
              <p className="text-2xl font-bold font-inter">12</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Clock className="h-5 w-5 text-primary" />
            </div>
          </div>
        </Card>
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">High Priority</p>
              <p className="text-2xl font-bold font-inter">8</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="h-5 w-5 text-destructive" />
            </div>
          </div>
        </Card>
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Generated</p>
              <p className="text-2xl font-bold font-inter">24</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-success/10 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-success" />
            </div>
          </div>
        </Card>
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Avg Impact</p>
              <p className="text-2xl font-bold font-inter">82%</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
          </div>
        </Card>
      </div>

      <Tabs value={selectedView} onValueChange={setSelectedView}>
        <TabsList>
          <TabsTrigger value="calendar">Calendar View</TabsTrigger>
          <TabsTrigger value="list">List View</TabsTrigger>
          <TabsTrigger value="pipeline">Content Pipeline</TabsTrigger>
        </TabsList>

        {/* Calendar View */}
        <TabsContent value="calendar" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="p-6 border border-border">
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={setSelectedDate}
                className="rounded-md"
              />
            </Card>

            <div className="lg:col-span-2 space-y-4">
              <Card className="p-6 border border-border">
                <h3 className="text-lg font-semibold mb-4">
                  {selectedDate?.toLocaleDateString('en-US', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </h3>
                
                {itemsForSelectedDate.length > 0 ? (
                  <div className="space-y-3">
                    {itemsForSelectedDate.map((item) => (
                      <Card key={item.id} className="p-4 border border-border">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-xl">{getContentIcon(item.type)}</span>
                              <h4 className="font-semibold">{item.title}</h4>
                            </div>
                            <div className="flex flex-wrap gap-2 mb-3">
                              <Badge variant="outline" className={getPriorityColor(item.priority)}>
                                {item.priority} priority
                              </Badge>
                              <Badge variant="outline" className={getStatusColor(item.status)}>
                                {item.status}
                              </Badge>
                              <Badge variant="secondary">
                                {item.wordCount} words
                              </Badge>
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1">
                              <p>📊 Source: {item.opportunitySource}</p>
                              <p>🎯 Est. Impact: {item.estimatedImpact}%</p>
                              <p>🔑 Keywords: {item.targetKeywords.join(", ")}</p>
                            </div>
                          </div>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleEditContent(item)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <CalendarIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No content scheduled for this date</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={handleGenerateContent}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Content
                    </Button>
                  </div>
                )}
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* List View */}
        <TabsContent value="list" className="space-y-4 mt-6">
          {contentItems
            .sort((a, b) => a.scheduledDate.getTime() - b.scheduledDate.getTime())
            .map((item) => (
              <Card key={item.id} className="p-6 hover:shadow-elegant transition-all">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-2xl">{getContentIcon(item.type)}</span>
                      <div>
                        <h3 className="text-lg font-semibold">{item.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {item.scheduledDate.toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-4">
                      <Badge variant="outline" className={getPriorityColor(item.priority)}>
                        {item.priority}
                      </Badge>
                      <Badge variant="outline" className={getStatusColor(item.status)}>
                        {item.status}
                      </Badge>
                      <Badge variant="secondary">{item.type}</Badge>
                      <Badge variant="secondary">{item.wordCount} words</Badge>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground mb-1">Source</p>
                        <p className="font-medium">{item.opportunitySource}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground mb-1">Estimated Impact</p>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-primary"
                              style={{ width: `${item.estimatedImpact}%` }}
                            />
                          </div>
                          <span className="font-medium">{item.estimatedImpact}%</span>
                        </div>
                      </div>
                      <div className="col-span-2">
                        <p className="text-muted-foreground mb-1">Target Keywords</p>
                        <div className="flex flex-wrap gap-1">
                          {item.targetKeywords.map((kw, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs">
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleEditContent(item)}
                  >
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </Button>
                </div>
              </Card>
            ))}
        </TabsContent>

        {/* Pipeline View */}
        <TabsContent value="pipeline" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Scheduled Column */}
            <Card className="p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">Scheduled</h3>
                <Badge variant="secondary" className="ml-auto">3</Badge>
              </div>
              <div className="space-y-3">
                {contentItems.filter(i => i.status === "scheduled").map(item => (
                  <Card key={item.id} className="p-3 cursor-pointer hover:shadow-md transition-all">
                    <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                    <div className="flex items-center justify-between text-xs">
                      <Badge variant="outline" className={getPriorityColor(item.priority)}>
                        {item.priority}
                      </Badge>
                      <span className="text-muted-foreground">
                        {item.scheduledDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>

            {/* Draft Column */}
            <Card className="p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <FileText className="h-5 w-5 text-warning" />
                <h3 className="font-semibold">Draft</h3>
                <Badge variant="secondary" className="ml-auto">1</Badge>
              </div>
              <div className="space-y-3">
                {contentItems.filter(i => i.status === "draft").map(item => (
                  <Card key={item.id} className="p-3 cursor-pointer hover:shadow-md transition-all">
                    <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                    <div className="flex items-center justify-between text-xs">
                      <Badge variant="outline" className={getPriorityColor(item.priority)}>
                        {item.priority}
                      </Badge>
                      <span className="text-muted-foreground">
                        {item.scheduledDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>

            {/* Generated Column */}
            <Card className="p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">Generated</h3>
                <Badge variant="secondary" className="ml-auto">1</Badge>
              </div>
              <div className="space-y-3">
                {contentItems.filter(i => i.status === "generated").map(item => (
                  <Card key={item.id} className="p-3 cursor-pointer hover:shadow-md transition-all">
                    <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                    <div className="flex items-center justify-between text-xs">
                      <Badge variant="outline" className={getPriorityColor(item.priority)}>
                        {item.priority}
                      </Badge>
                      <span className="text-muted-foreground">
                        {item.scheduledDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            </Card>

            {/* Published Column */}
            <Card className="p-4 border border-border">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="h-5 w-5 text-success" />
                <h3 className="font-semibold">Published</h3>
                <Badge variant="secondary" className="ml-auto">0</Badge>
              </div>
              <div className="text-center py-8 text-muted-foreground text-sm">
                No published content yet
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <GenerateContentDialog 
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        existingContent={selectedContent}
      />
    </div>
  );
};

export default ContentCalendar;
