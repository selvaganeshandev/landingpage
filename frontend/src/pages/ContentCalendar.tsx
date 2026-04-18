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
  List,
  Trash2,
  Loader2,
  Book,
  GitCompare,
  Wrench,
  Rocket,
  Briefcase,
  Package,
  LayoutGrid,
  BookOpen,
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  ListOrdered,
  MessageCircle,
  HelpCircle,
  MessagesSquare,
  Mail,
  MessageSquare,
  Upload,
  PenLine,
  ChevronDown,
  type LucideIcon
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { GenerateContentDialog } from "@/components/GenerateContentDialog";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

interface ContentItem {
  id: string;
  title: string;
  type: string;
  status: "planned" | "scheduled" | "draft" | "generated" | "published";
  priority: "high" | "medium" | "low";
  scheduledDate: Date;
  targetKeywords: string[];
  opportunitySource: string;
  estimatedImpact: number;
  wordCount: number;
  totalComments: number;
  pendingComments: number;
}

const contentTypeIconMap: Record<string, { icon: LucideIcon; gradient: string }> = {
  // Articles
  blog:             { icon: FileText,       gradient: "from-blue-500 to-indigo-600" },
  guide:            { icon: Book,           gradient: "from-blue-500 to-indigo-600" },
  comparison:       { icon: GitCompare,     gradient: "from-blue-500 to-indigo-600" },
  listicle:         { icon: List,           gradient: "from-blue-500 to-indigo-600" },
  technical:        { icon: Wrench,         gradient: "from-blue-500 to-indigo-600" },
  // Web Pages
  landing_page:     { icon: Rocket,         gradient: "from-violet-500 to-purple-600" },
  services_page:    { icon: Briefcase,      gradient: "from-violet-500 to-purple-600" },
  product_page:     { icon: Package,        gradient: "from-violet-500 to-purple-600" },
  features_page:    { icon: LayoutGrid,     gradient: "from-violet-500 to-purple-600" },
  resource_page:    { icon: BookOpen,       gradient: "from-violet-500 to-purple-600" },
  // Social Media
  twitter_post:     { icon: Twitter,        gradient: "from-orange-500 to-amber-600" },
  linkedin_post:    { icon: Linkedin,       gradient: "from-orange-500 to-amber-600" },
  facebook_post:    { icon: Facebook,       gradient: "from-orange-500 to-amber-600" },
  instagram_caption:{ icon: Instagram,      gradient: "from-orange-500 to-amber-600" },
  social_thread:    { icon: ListOrdered,    gradient: "from-orange-500 to-amber-600" },
  // Community
  reddit_post:      { icon: MessageCircle,  gradient: "from-pink-500 to-rose-600" },
  quora_answer:     { icon: HelpCircle,     gradient: "from-pink-500 to-rose-600" },
  forum_post:       { icon: MessagesSquare, gradient: "from-pink-500 to-rose-600" },
  product_hunt:     { icon: Rocket,         gradient: "from-pink-500 to-rose-600" },
  newsletter_snippet:{ icon: Mail,          gradient: "from-pink-500 to-rose-600" },
};

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
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<ContentItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  // Plan content dialog state (Issue 8C)
  const [planDialogOpen, setPlanDialogOpen] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [planForm, setPlanForm] = useState({
    title: '',
    keywords: '',
    article_type: 'blog',
    priority: 'medium',
    word_count: 1500,
  });
  // Fetch generated content from API
  useEffect(() => {
    const fetchContent = async () => {
      if (!selectedDomain) return;

      try {
        const isFirstPage = currentPage === 1;
        if (isFirstPage) {
          setLoading(true);
        } else {
          setLoadingMore(true);
        }
        const response = await apiClient.getGeneratedContents({ domain_id: selectedDomain.id, page: currentPage, page_size: '20' });

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
            wordCount: item.actual_word_count || item.word_count || 0,
            totalComments: item.total_comments || 0,
            pendingComments: item.pending_comments || 0
          }));

          if (isFirstPage) {
            setContentItems(formattedContent);
          } else {
            setContentItems(prev => [...prev, ...formattedContent]);
          }

          setHasMore(response.has_next || false);
          setTotalCount(response.count || 0);
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
        setLoadingMore(false);
      }
    };

    fetchContent();
  }, [selectedDomain, currentPage, toast]);

  // Reset to first page when domain changes
  useEffect(() => {
    setCurrentPage(1);
    setContentItems([]);
  }, [selectedDomain]);

  const handleLoadMore = () => {
    if (hasMore && !loadingMore) {
      setCurrentPage(prev => prev + 1);
    }
  };

  const handleGenerateContent = () => {
    setGenerateDialogOpen(true);
  };

  const handleEditContent = (item: ContentItem) => {
    // Navigate to the content editor page
    navigate(`/content-editor/${item.id}`);
  };

  const handleDeleteClick = (item: ContentItem) => {
    setItemToDelete(item);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!itemToDelete) return;

    setIsDeleting(true);
    try {
      await apiClient.deleteGeneratedContent(parseInt(itemToDelete.id));

      // Remove from local state
      setContentItems(prev => prev.filter(item => item.id !== itemToDelete.id));
      setTotalCount(prev => Math.max(0, prev - 1));

      toast({
        title: "Content Deleted",
        description: `"${itemToDelete.title}" has been deleted successfully.`,
      });
    } catch (error) {
      console.error("Error deleting content:", error);
      toast({
        title: "Error",
        description: "Failed to delete content. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setItemToDelete(null);
    }
  };

  // Plan content handler (Issue 8C)
  const handlePlanContent = async () => {
    if (!selectedDomain || !planForm.title.trim()) return;

    setIsPlanning(true);
    try {
      const response = await apiClient.planContent({
        domain_id: selectedDomain.id,
        title: planForm.title,
        keywords: planForm.keywords,
        article_type: planForm.article_type,
        priority: planForm.priority,
        word_count: planForm.word_count,
        scheduled_date: selectedDate?.toISOString(),
      });

      if (response.status === 'success' && response.data) {
        const item = response.data;
        const newItem: ContentItem = {
          id: item.id.toString(),
          title: item.title,
          type: item.article_type || 'blog',
          status: 'planned',
          priority: item.priority || 'medium',
          scheduledDate: item.scheduled_date ? new Date(item.scheduled_date) : new Date(),
          targetKeywords: item.keywords ? item.keywords.split(',').map((k: string) => k.trim()) : [],
          opportunitySource: 'Manual',
          estimatedImpact: 0,
          wordCount: item.word_count || 1500,
          totalComments: 0,
          pendingComments: 0,
        };
        setContentItems(prev => [newItem, ...prev]);
        setPlanDialogOpen(false);
        setPlanForm({ title: '', keywords: '', article_type: 'blog', priority: 'medium', word_count: 1500 });
        toast({
          title: "Content Planned",
          description: `"${planForm.title}" has been added to your content plan.`,
        });
      }
    } catch (error) {
      console.error("Error planning content:", error);
      toast({
        title: "Error",
        description: "Failed to plan content. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsPlanning(false);
    }
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
      case "planned": return "bg-violet-500/10 text-violet-600";
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

  const getContentTypeInfo = (type: string) => {
    return contentTypeIconMap[type] || { icon: FileText, gradient: "from-blue-500 to-indigo-600" };
  };

  const getReviewStatus = (item: ContentItem) => {
    if (item.totalComments === 0) {
      return { label: "No Reviews", className: "bg-muted text-muted-foreground border-border" };
    }
    if (item.pendingComments > 0) {
      return { label: "In Review", className: "bg-warning/10 text-warning border-warning/20" };
    }
    return { label: "Reviewed", className: "bg-success/10 text-success border-success/20" };
  };

  const itemsForSelectedDate = contentItems.filter(
    item => selectedDate &&
    item.scheduledDate.toDateString() === selectedDate.toDateString()
  );

  // Calculate dynamic summary stats
  const plannedCount = contentItems.filter(item => item.status === "planned").length;
  const scheduledCount = contentItems.filter(item => item.status === "scheduled").length;
  const draftCount = contentItems.filter(item => item.status === "draft").length;
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
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/automation')}
            className="border-border/50"
          >
            <Settings className="h-4 w-4 mr-2" />
            CMS Settings
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/bulk-upload')}
            className="border-border/50"
          >
            <Upload className="h-4 w-4 mr-2" />
            Bulk Upload
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="gradient-primary shadow-md shadow-primary/20 gap-2">
                <Sparkles className="h-4 w-4" />
                Create Content
                <ChevronDown className="h-3.5 w-3.5 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 p-1.5">
              <DropdownMenuItem
                onClick={handleGenerateContent}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer"
              >
                <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="font-medium text-sm">Generate with AI</p>
                  <p className="text-xs text-muted-foreground">Create content using AI wizard</p>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => setPlanDialogOpen(true)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <PenLine className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="font-medium text-sm">Plan Content</p>
                  <p className="text-xs text-muted-foreground">Schedule an idea for later</p>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Planned</p>
              <p className="text-2xl font-bold font-inter">{loading ? "-" : plannedCount}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
              <PenLine className="h-5 w-5 text-violet-500" />
            </div>
          </div>
        </Card>
        <Card className="p-4 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Drafts / Scheduled</p>
              <p className="text-2xl font-bold font-inter">{loading ? "-" : draftCount + scheduledCount}</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-destructive/10 flex items-center justify-center">
              <FileText className="h-5 w-5 text-destructive" />
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
                        {(() => {
                          const { icon: TypeIcon, gradient } = getContentTypeInfo(item.type);
                          return (
                            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center flex-shrink-0`}>
                              <TypeIcon className="h-5 w-5 text-white" />
                            </div>
                          );
                        })()}
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

                    <div className="flex flex-col items-end gap-3">
                      {(() => {
                        const reviewStatus = getReviewStatus(item);
                        return (
                          <Badge variant="outline" className={`${reviewStatus.className} gap-1.5`}>
                            <MessageSquare className="h-3 w-3" />
                            {reviewStatus.label}
                            {item.totalComments > 0 && (
                              <span className="font-normal opacity-75">
                                ({item.pendingComments}/{item.totalComments})
                              </span>
                            )}
                          </Badge>
                        );
                      })()}
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditContent(item)}
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteClick(item)}
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ))
          )}

          {/* Load More */}
          {hasMore && (
            <div className="flex flex-col items-center gap-3 pt-8">
              <div className="text-sm text-muted-foreground">
                Showing <span className="font-medium text-foreground">{contentItems.length}</span> of{" "}
                <span className="font-medium text-foreground">{totalCount}</span> items
              </div>
              <Button
                size="lg"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="min-w-[180px] shadow-sm"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
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
                          <div className="flex gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditContent(item)}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteClick(item)}
                              className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <CalendarIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-lg font-medium">No content for this date</p>
                    <p className="text-sm mt-1 mb-3">Plan content for this date or generate new content</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPlanDialogOpen(true)}
                    >
                      <PenLine className="h-4 w-4 mr-2" />
                      Plan Content for This Date
                    </Button>
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* Load More */}
          {hasMore && (
            <div className="flex flex-col items-center gap-3 pt-8">
              <div className="text-sm text-muted-foreground">
                Showing <span className="font-medium text-foreground">{contentItems.length}</span> of{" "}
                <span className="font-medium text-foreground">{totalCount}</span> items
              </div>
              <Button
                size="lg"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="min-w-[180px] shadow-sm"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
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
            <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
              {/* Planned Column */}
              <Card className="p-4 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <PenLine className="h-5 w-5 text-violet-500" />
                  <h3 className="font-semibold">Planned</h3>
                  <Badge variant="secondary" className="ml-auto">
                    {contentItems.filter(i => i.status === "planned").length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {contentItems.filter(i => i.status === "planned").length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPlanDialogOpen(true)}
                        className="text-muted-foreground"
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Plan content
                      </Button>
                    </div>
                  ) : (
                    contentItems.filter(i => i.status === "planned").map(item => (
                      <Card key={item.id} className="p-3 hover:shadow-md transition-all">
                        <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                        <div className="flex items-center justify-between text-xs mb-2">
                          <Badge variant="outline" className={getPriorityColor(item.priority)}>
                            {item.priority}
                          </Badge>
                          <span className="text-muted-foreground">
                            {item.scheduledDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full h-7 text-xs"
                          onClick={() => {
                            setSelectedContent({
                              id: item.id,
                              title: item.title,
                              type: item.type,
                              status: "draft",
                              priority: item.priority,
                              scheduledDate: item.scheduledDate,
                              targetKeywords: item.targetKeywords,
                              opportunitySource: item.opportunitySource,
                              estimatedImpact: 0,
                              wordCount: item.wordCount,
                              totalComments: 0,
                              pendingComments: 0,
                            });
                            setGenerateDialogOpen(true);
                          }}
                        >
                          <Sparkles className="h-3 w-3 mr-1" />
                          Generate Now
                        </Button>
                      </Card>
                    ))
                  )}
                </div>
              </Card>

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
                      <Card key={item.id} className="p-3 hover:shadow-md transition-all">
                        <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                        <div className="flex items-center justify-between text-xs mb-2">
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
                      <Card key={item.id} className="p-3 hover:shadow-md transition-all">
                        <p className="font-medium text-sm mb-2 line-clamp-2">{item.title}</p>
                        <div className="flex items-center justify-between text-xs mb-2">
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

          {/* Load More */}
          {hasMore && (
            <div className="flex flex-col items-center gap-3 pt-8">
              <div className="text-sm text-muted-foreground">
                Showing <span className="font-medium text-foreground">{contentItems.length}</span> of{" "}
                <span className="font-medium text-foreground">{totalCount}</span> items
              </div>
              <Button
                size="lg"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="min-w-[180px] shadow-sm"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>

      <GenerateContentDialog
        open={generateDialogOpen}
        onOpenChange={setGenerateDialogOpen}
        existingContent={selectedContent}
      />

      {/* Plan Content Dialog (Issue 8C) */}
      <Dialog open={planDialogOpen} onOpenChange={setPlanDialogOpen}>
        <DialogContent className="sm:max-w-lg p-0 overflow-hidden">
          {/* Header with gradient */}
          <div className="px-6 pt-6 pb-4 bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-950/30 dark:to-purple-950/30 border-b">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-md">
                <PenLine className="h-5 w-5 text-white" />
              </div>
              <div>
                <DialogHeader className="p-0 space-y-0">
                  <DialogTitle className="text-lg">Plan New Content</DialogTitle>
                </DialogHeader>
                <p className="text-sm text-muted-foreground">Schedule a content idea for future generation</p>
              </div>
            </div>
          </div>

          <div className="px-6 py-4 space-y-4">
            {/* Scheduled Date Highlight */}
            {selectedDate && (
              <div className="flex items-center gap-2 px-3 py-2 bg-primary/5 rounded-lg border border-primary/10">
                <CalendarIcon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">
                  {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
            )}

            <div>
              <Label className="text-sm font-medium">Title <span className="text-destructive">*</span></Label>
              <Input
                className="mt-1"
                value={planForm.title}
                onChange={(e) => setPlanForm({ ...planForm, title: e.target.value })}
                placeholder="e.g. 10 Best SEO Tools for Small Business in 2025"
              />
            </div>

            <div>
              <Label className="text-sm font-medium">Target Keywords</Label>
              <Textarea
                className="mt-1"
                value={planForm.keywords}
                onChange={(e) => setPlanForm({ ...planForm, keywords: e.target.value })}
                placeholder="seo tools, best seo software, keyword tracking"
                rows={2}
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-sm font-medium">Type</Label>
                <Select value={planForm.article_type} onValueChange={(v) => setPlanForm({ ...planForm, article_type: v })}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="blog">Blog Post</SelectItem>
                    <SelectItem value="guide">How-to Guide</SelectItem>
                    <SelectItem value="comparison">Comparison</SelectItem>
                    <SelectItem value="listicle">Listicle</SelectItem>
                    <SelectItem value="technical">Technical</SelectItem>
                    <SelectItem value="landing_page">Landing Page</SelectItem>
                    <SelectItem value="services_page">Services Page</SelectItem>
                    <SelectItem value="product_page">Product Page</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm font-medium">Priority</Label>
                <Select value={planForm.priority} onValueChange={(v) => setPlanForm({ ...planForm, priority: v })}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm font-medium">Words</Label>
                <Select value={String(planForm.word_count)} onValueChange={(v) => setPlanForm({ ...planForm, word_count: parseInt(v) })}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="500">500</SelectItem>
                    <SelectItem value="800">800</SelectItem>
                    <SelectItem value="1500">1,500</SelectItem>
                    <SelectItem value="2000">2,000</SelectItem>
                    <SelectItem value="2500">2,500</SelectItem>
                    <SelectItem value="3500">3,500</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter className="px-6 py-4 border-t bg-muted/30">
            <Button variant="outline" onClick={() => setPlanDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handlePlanContent}
              disabled={isPlanning || !planForm.title.trim()}
              className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white shadow-md"
            >
              {isPlanning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Planning...
                </>
              ) : (
                <>
                  <PenLine className="h-4 w-4 mr-2" />
                  Add to Plan
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Content</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{itemToDelete?.title}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  );
};

export default ContentCalendar;
