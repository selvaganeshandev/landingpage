import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  ArrowLeft, 
  TrendingUp,
  Sparkles,
  Share2,
  FileText,
  Copy,
  Loader2
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

const PromptDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [promptGroup, setPromptGroup] = useState<any>(null);
  const [prompts, setPrompts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadPromptGroupDetail();
      loadPrompts();
    }
  }, [id]);

  const loadPromptGroupDetail = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getPromptGroupDetail(parseInt(id!));
      setPromptGroup(response.group);
    } catch (error: any) {
      toast({
        title: "Error loading prompt group",
        description: error.message || "Failed to load prompt group details",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadPrompts = async () => {
    try {
      const response = await apiClient.getPrompts({
        group_id: parseInt(id!)
      });
      setPrompts(response.prompts);
    } catch (error: any) {
      console.error("Failed to load prompts:", error);
    }
  };

  const mentionTrend = [
    { month: "Jul", mentions: 65, avgPosition: 1.8 },
    { month: "Aug", mentions: 71, avgPosition: 1.7 },
    { month: "Sep", mentions: 76, avgPosition: 1.6 },
    { month: "Oct", mentions: 82, avgPosition: 1.5 },
    { month: "Nov", mentions: 85, avgPosition: 1.5 },
    { month: "Dec", mentions: 89, avgPosition: 1.4 },
  ];

  const variantPerformance = [
    { variant: "main prompt", mentions: 32, avgPosition: 1.2 },
    { variant: "variant 1", mentions: 24, avgPosition: 1.5 },
    { variant: "variant 2", mentions: 18, avgPosition: 1.8 },
    { variant: "variant 3", mentions: 15, avgPosition: 1.6 },
  ];

  const platformBreakdown = [
    { platform: "ChatGPT", mentions: 35 },
    { platform: "Claude", mentions: 28 },
    { platform: "Perplexity", mentions: 16 },
    { platform: "Gemini", mentions: 10 },
  ];

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied to Clipboard",
      description: "Prompt has been copied.",
    });
  };

  const handleShare = () => {
    toast({
      title: "Share Link Generated",
      description: "Prompt group link copied to clipboard.",
    });
  };

  const handleExport = () => {
    toast({
      title: "Exporting Report",
      description: "Prompt group report is being generated...",
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!promptGroup) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="p-8 text-center">
          <h2 className="text-2xl font-bold mb-4">Prompt Group Not Found</h2>
          <p className="text-gray-600 mb-4">The prompt group you're looking for doesn't exist.</p>
          <Button onClick={() => navigate("/prompts")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Prompts
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
            className="border-border/50"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-outfit">Group {promptGroup?.group_id || 'N/A'}</h1>
            <p className="text-muted-foreground mt-1">
              Domain: {promptGroup?.domain_name || 'N/A'}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleShare} className="border-border/50">
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" onClick={handleExport} className="border-border/50">
            <FileText className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Total Mentions</p>
            <p className="text-4xl font-bold font-outfit">{promptGroup?.total_mentions || 0}</p>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-success" />
              <span className="text-sm font-semibold text-success">Created: {promptGroup?.created_at ? new Date(promptGroup.created_at).toLocaleDateString() : 'N/A'}</span>
            </div>
          </div>
        </Card>

        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Active Variants</p>
            <p className="text-4xl font-bold font-outfit">{prompts?.length || 0}</p>
            <p className="text-sm text-muted-foreground">Prompts in this group</p>
          </div>
        </Card>

        <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground uppercase tracking-wider">Avg Position</p>
            <p className="text-4xl font-bold font-outfit">{promptGroup?.average_position || 0}</p>
            <p className="text-sm text-muted-foreground">Average position across platforms</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Prompt */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold font-outfit">Prompts in Group</h3>
              </div>
              <div className="space-y-3">
                {prompts && prompts.length > 0 ? (
                  prompts.map((prompt, idx) => (
                    <div key={prompt.id} className="p-4 rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 border border-border/50">
                      <div className="flex items-center justify-between">
                        <p className="font-mono text-sm">{prompt.prompt_text}</p>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{prompt.track_status}</Badge>
                          <Badge variant="secondary">{prompt.type}</Badge>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground text-center py-4">No prompts found in this group</p>
                )}
              </div>
            </div>
          </Card>

          {/* Mention Trends */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border/50">
                <h3 className="text-lg font-semibold font-outfit">Mention Volume Trends</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Track how mention frequency changes over time
                </p>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mentionTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} reversed />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "var(--radius)",
                    }}
                  />
                  <Legend />
                  <Line 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="mentions" 
                    name="Mentions"
                    stroke="hsl(var(--primary))" 
                    strokeWidth={3}
                    dot={{ fill: "hsl(var(--primary))", r: 4 }}
                  />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="avgPosition" 
                    name="Avg Position"
                    stroke="hsl(var(--chart-2))" 
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--chart-2))", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Variant Performance */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-6">
              <div className="pb-4 border-b border-border/50">
                <h3 className="text-lg font-semibold font-outfit">Variant Performance</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Compare performance across prompt variations
                </p>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={variantPerformance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="variant" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "var(--radius)",
                    }}
                  />
                  <Bar dataKey="mentions" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Prompt Variants */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-4 border-b border-border/50">
                <h3 className="text-lg font-semibold font-outfit">Prompt Variants</h3>
                <Badge variant="secondary">{promptGroup.prompts?.length || 0}</Badge>
              </div>
              <div className="space-y-3">
                {promptGroup.prompts?.map((prompt, idx) => (
                  <div
                    key={prompt.id}
                    className="group p-3 rounded-xl bg-muted/30 border border-border/50 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-mono mb-2">{prompt.prompt_text}</p>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">{prompt.type}</Badge>
                          <Badge variant="secondary" className="text-xs">{prompt.track_status}</Badge>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(prompt.prompt_text)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                )) || []}
              </div>
            </div>
          </Card>

          {/* Platform Distribution */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-4">
              <h3 className="text-lg font-semibold font-outfit pb-4 border-b border-border/50">Platform Distribution</h3>
              <div className="space-y-3">
                {platformBreakdown.map((platform, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{platform.platform}</span>
                      <span className="text-sm font-bold font-outfit">{platform.mentions}</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-chart-${idx + 1} transition-all duration-500`}
                        style={{ width: `${(platform.mentions / 89) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Quick Actions */}
          <Card className="p-6 shadow-elegant border-border/50 backdrop-blur-sm bg-card/80">
            <div className="space-y-3">
              <h3 className="text-lg font-semibold font-outfit pb-4 border-b border-border/50">Quick Actions</h3>
              <Button variant="outline" className="w-full justify-start border-border/50">
                <Sparkles className="h-4 w-4 mr-2" />
                Generate More Variants
              </Button>
              <Button variant="outline" className="w-full justify-start border-border/50">
                <TrendingUp className="h-4 w-4 mr-2" />
                View All Mentions
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PromptDetail;
