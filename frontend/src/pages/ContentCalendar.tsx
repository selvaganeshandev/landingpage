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
  List
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

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
  const { selectedDomain } = useDomainStore();
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [selectedView, setSelectedView] = useState("list");
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedContent, setSelectedContent] = useState<ContentItem | null>(null);
  const [contentItems, setContentItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch generated content from API
  useEffect(() => {
    const fetchContent = async () => {
      if (!selectedDomain) return;

      try {
        setLoading(true);
        const response = await apiClient.getGeneratedContents({ domain_id: selectedDomain.id });

        if (response.status === "success" && response.results) {
          const formattedContent: ContentItem[] = response.results.map((item: any) => ({
            id: item.id.toString(),
            title: item.title,
            type: item.article_type || "blog",
            status: item.status || "draft",
            priority: item.priority || "medium",
            scheduledDate: item.scheduled_date ? new Date(item.scheduled_date) : new Date(),
            targetKeywords: item.keywords ? item.keywords.split(",").map((k: string) => k.trim()) : [],
            opportunitySource: item.source_type === "content_gap" ? "Content Gap" : item.source_type === "topic" ? "Topic" : "Manual",
            estimatedImpact: 75,
            wordCount: item.actual_word_count || item.word_count || 0
          }));
          setContentItems(formattedContent);
        }
      } catch (error) {
        console.error("Error fetching content:", error);
        toast({
          title: "Error",
          description: "Failed to load content items",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, [selectedDomain, toast]);

  const handleGenerateContent = () => {
    setGenerateDialogOpen(true);
  };

  const handleEditContent = (item: ContentItem) => {
    // Navigate to the content editor page
    navigate(`/content-editor/${item.id}`);
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

  // Calculate dynamic summary stats
  const scheduledCount = contentItems.filter(item => item.status === "scheduled").length;
  const highPriorityCount = contentItems.filter(item => item.priority === "high").length;
  const generatedCount = contentItems.filter(item => item.status === "generated" || item.status === "published").length;
  const avgImpact = contentItems.length > 0
    ? Math.round(contentItems.reduce((sum, item) => sum + item.estimatedImpact, 0) / contentItems.length)
    : 0;

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Content Planner</h1>
          <p className="text-muted-foreground mt-1">
            AI-powered content generation prioritized by opportunity
          </p>
        </div>
        <div className="flex gap-3">
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
              <p className="text-2xl font-bold font-inter">{loading ? "-" : scheduledCount}</p>
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
              <p className="text-2xl font-bold font-inter">{loading ? "-" : highPriorityCount}</p>
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
              <p className="text-2xl font-bold font-inter">{loading ? "-" : generatedCount}</p>
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
              <p className="text-2xl font-bold font-inter">{loading ? "-" : `${avgImpact}%`}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-primary" />
            </div>
          </div>
        </Card>
      </div>

      <Tabs value={selectedView} onValueChange={setSelectedView}>
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="list" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            <List className="h-4 w-4 mr-2" />List View
          </TabsTrigger>
          <TabsTrigger value="calendar" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            <CalendarIcon className="h-4 w-4 mr-2" />Calendar View
          </TabsTrigger>
          <TabsTrigger value="pipeline" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
            <Target className="h-4 w-4 mr-2" />Content Pipeline
          </TabsTrigger>
        </TabsList>

        {/* List View */}
        <TabsContent value="list" className="space-y-4 mt-6">
          {loading ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">Loading content...</p>
            </div>
          ) : contentItems.length === 0 ? (
            <Card className="p-12 border border-dashed border-border">
              <div className="text-center text-muted-foreground">
                <FileText className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">No content generated yet</h3>
                <p className="mb-4">Start generating AI-powered content for your domain</p>
                <Button
                  variant="outline"
                  onClick={handleGenerateContent}
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Your First Content
                </Button>
              </div>
            </Card>
          ) : (
            contentItems
              .sort((a, b) => a.scheduledDate.getTime() - b.scheduledDate.getTime())
              .map((item) => (
                <Card key={item.id} className="p-6 hover:shadow-elegant transition-all">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
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
              ))
          )}
        </TabsContent>

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
                    <p className="text-lg font-medium">Coming Soon</p>
                    <p className="text-sm mt-1">Calendar scheduling feature is under development</p>
                  </div>
                )}
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Pipeline View */}
        <TabsContent value="pipeline" className="space-y-6 mt-6">
          {loading ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">Loading pipeline...</p>
            </div>
          ) : contentItems.length === 0 ? (
            <Card className="p-12 border border-dashed border-border">
              <div className="text-center text-muted-foreground">
                <Target className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <h3 className="text-lg font-semibold mb-2">No content in pipeline</h3>
                <p className="mb-4">Start organizing your content generation workflow</p>
                <Button
                  variant="outline"
                  onClick={handleGenerateContent}
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Content
                </Button>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Scheduled Column */}
              <Card className="p-4 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="h-5 w-5 text-primary" />
                  <h3 className="font-semibold">Scheduled</h3>
                  <Badge variant="secondary" className="ml-auto">
                    {contentItems.filter(i => i.status === "scheduled").length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {contentItems.filter(i => i.status === "scheduled").length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      No scheduled content
                    </div>
                  ) : (
                    contentItems.filter(i => i.status === "scheduled").map(item => (
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
                    ))
                  )}
                </div>
              </Card>

              {/* Draft Column */}
              <Card className="p-4 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="h-5 w-5 text-warning" />
                  <h3 className="font-semibold">Draft</h3>
                  <Badge variant="secondary" className="ml-auto">
                    {contentItems.filter(i => i.status === "draft").length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {contentItems.filter(i => i.status === "draft").length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      No drafts yet
                    </div>
                  ) : (
                    contentItems.filter(i => i.status === "draft").map(item => (
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
                    ))
                  )}
                </div>
              </Card>

              {/* Generated Column */}
              <Card className="p-4 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="h-5 w-5 text-primary" />
                  <h3 className="font-semibold">Generated</h3>
                  <Badge variant="secondary" className="ml-auto">
                    {contentItems.filter(i => i.status === "generated").length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {contentItems.filter(i => i.status === "generated").length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      No generated content
                    </div>
                  ) : (
                    contentItems.filter(i => i.status === "generated").map(item => (
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
                    ))
                  )}
                </div>
              </Card>

              {/* Published Column */}
              <Card className="p-4 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle2 className="h-5 w-5 text-success" />
                  <h3 className="font-semibold">Published</h3>
                  <Badge variant="secondary" className="ml-auto">
                    {contentItems.filter(i => i.status === "published").length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {contentItems.filter(i => i.status === "published").length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      No published content yet
                    </div>
                  ) : (
                    contentItems.filter(i => i.status === "published").map(item => (
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
                    ))
                  )}
                </div>
              </Card>
            </div>
          )}
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
