import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import {
  ArrowLeft,
  Save,
  BarChart3,
  PieChart,
  LineChart,
  Table2,
  TrendingUp,
  Users,
  FileText,
  Target,
  Activity,
  Grip,
  Plus,
  LayoutGrid,
  X,
  Link2,
  Eye,
  Smile,
  Meh,
  Frown,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  AreaChart,
  Area,
  BarChart as RechartsBarChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Legend,
  LineChart as RechartsLineChart,
} from "recharts";

// Define widget types
type WidgetType = "metric" | "chart" | "table" | "text";
type GridType = "single" | "double" | "triple" | "quad";

interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  icon: any;
  description: string;
}

interface GridRow {
  id: string;
  type: GridType;
  slots: (Widget | null)[];
}

interface WidgetModule {
  name: string;
  widgets: Widget[];
}

// Available widgets grouped by modules
const widgetModules: WidgetModule[] = [
  {
    name: "Information Metrics",
    widgets: [
      // Performance Metrics
      {
        id: "visibility-metric",
        type: "metric",
        title: "Overall Visibility Score",
        icon: Target,
        description: "Overall visibility score",
      },
      {
        id: "avg-position-metric",
        type: "metric",
        title: "Average Position",
        icon: TrendingUp,
        description: "Average position in responses",
      },
      {
        id: "engagement-metric",
        type: "metric",
        title: "Engagement Score",
        icon: Activity,
        description: "Overall engagement score",
      },
      {
        id: "share-metric",
        type: "metric",
        title: "Share of Voice",
        icon: Target,
        description: "Your share of voice percentage",
      },
      // Mention Metrics
      {
        id: "total-mentions-metric",
        type: "metric",
        title: "Total AI Mentions",
        icon: Eye,
        description: "Total brand mentions",
      },
      {
        id: "mention-rate-metric",
        type: "metric",
        title: "Mention Rate",
        icon: TrendingUp,
        description: "Percentage of prompts with mentions",
      },
      {
        id: "mention-growth-metric",
        type: "metric",
        title: "Mention Growth",
        icon: TrendingUp,
        description: "Growth vs previous period",
      },
      {
        id: "platform-coverage-metric",
        type: "metric",
        title: "Platform Coverage",
        icon: BarChart3,
        description: "Number of platforms with mentions",
      },
      // Citation Metrics
      {
        id: "total-citations-metric",
        type: "metric",
        title: "Total Citations",
        icon: Link2,
        description: "Total citations across all platforms",
      },
      {
        id: "citation-rate-metric",
        type: "metric",
        title: "Citation Rate",
        icon: Link2,
        description: "Citations per mention",
      },
      {
        id: "citation-density-metric",
        type: "metric",
        title: "Citation Density",
        icon: Link2,
        description: "Average citations per response",
      },
      {
        id: "primary-sources-metric",
        type: "metric",
        title: "Primary Sources",
        icon: Link2,
        description: "Count of primary source citations",
      },
      // Sentiment Metrics
      {
        id: "positive-sentiment-metric",
        type: "metric",
        title: "Positive Sentiment %",
        icon: Smile,
        description: "Percentage of positive mentions",
      },
      {
        id: "avg-sentiment-metric",
        type: "metric",
        title: "Average Sentiment Score",
        icon: Activity,
        description: "Average sentiment score",
      },
      {
        id: "sentiment-trend-metric",
        type: "metric",
        title: "Sentiment Trend",
        icon: TrendingUp,
        description: "Sentiment change vs previous period",
      },
      {
        id: "negative-sentiment-metric",
        type: "metric",
        title: "Negative Sentiment %",
        icon: Frown,
        description: "Percentage of negative mentions",
      },
      // Competitive Metrics
      {
        id: "market-position-metric",
        type: "metric",
        title: "Market Position",
        icon: Target,
        description: "Your rank vs competitors",
      },
      {
        id: "competitor-gap-metric",
        type: "metric",
        title: "Competitor Gap",
        icon: Users,
        description: "Difference from top competitor",
      },
      {
        id: "market-share-trend-metric",
        type: "metric",
        title: "Market Share Trend",
        icon: TrendingUp,
        description: "Share of voice trend",
      },
      // Quality Metrics
      {
        id: "health-score-metric",
        type: "metric",
        title: "Health Score",
        icon: Activity,
        description: "Domain AI-friendliness score",
      },
      {
        id: "content-quality-metric",
        type: "metric",
        title: "Content Quality Score",
        icon: FileText,
        description: "Based on sentiment and engagement",
      },
      {
        id: "topics-covered-metric",
        type: "metric",
        title: "Topics Covered",
        icon: FileText,
        description: "Number of topics with mentions",
      },
      {
        id: "answer-coverage-metric",
        type: "metric",
        title: "Answer Coverage",
        icon: Target,
        description: "Percentage of prompts answered",
      },
      // Alert Metrics
      {
        id: "active-alerts-metric",
        type: "metric",
        title: "Active Alerts",
        icon: AlertCircle,
        description: "Open misinformation alerts",
      },
      {
        id: "critical-issues-metric",
        type: "metric",
        title: "Critical Issues",
        icon: AlertCircle,
        description: "High severity alerts",
      },
      {
        id: "broken-links-metric",
        type: "metric",
        title: "Broken Links",
        icon: Link2,
        description: "Failed citation URLs",
      },
      {
        id: "misinformation-cases-metric",
        type: "metric",
        title: "Misinformation Cases",
        icon: AlertCircle,
        description: "Detected misinformation alerts",
      },
      // Growth Metrics
      {
        id: "mention-growth-percent-metric",
        type: "metric",
        title: "Mention Growth %",
        icon: TrendingUp,
        description: "Growth vs previous period",
      },
      {
        id: "visibility-trend-metric",
        type: "metric",
        title: "Visibility Trend",
        icon: TrendingUp,
        description: "Visibility score change",
      },
      {
        id: "citation-growth-metric",
        type: "metric",
        title: "Citation Growth",
        icon: TrendingUp,
        description: "Citation growth percentage",
      },
      {
        id: "engagement-growth-metric",
        type: "metric",
        title: "Engagement Growth",
        icon: TrendingUp,
        description: "Engagement score change",
      },
    ],
  },
  {
    name: "Mentions",
    widgets: [
      {
        id: "mentions-metric",
        type: "metric",
        title: "Mentions Count",
        icon: TrendingUp,
        description: "Total number of mentions",
      },
      {
        id: "mentions-chart",
        type: "chart",
        title: "Mentions Over Time",
        icon: LineChart,
        description: "Line chart showing mention trends",
      },
      {
        id: "platform-chart",
        type: "chart",
        title: "Platform Breakdown",
        icon: BarChart3,
        description: "Bar chart by AI platform",
      },
    ],
  },
  {
    name: "Competitors",
    widgets: [
      {
        id: "competitors-metric",
        type: "metric",
        title: "Competitor Count",
        icon: Users,
        description: "Number of competitors tracked",
      },
      {
        id: "share-metric",
        type: "metric",
        title: "Share of Voice",
        icon: Target,
        description: "Your share of voice percentage",
      },
      {
        id: "competitors-table",
        type: "table",
        title: "Competitor Analysis",
        icon: Table2,
        description: "Detailed competitor comparison",
      },
    ],
  },
  {
    name: "Content",
    widgets: [
      {
        id: "topics-table",
        type: "table",
        title: "Top Topics",
        icon: Table2,
        description: "Table of trending topics",
      },
      {
        id: "summary-text",
        type: "text",
        title: "Executive Summary",
        icon: FileText,
        description: "Text summary section",
      },
    ],
  },
  {
    name: "Sentiment",
    widgets: [
      {
        id: "sentiment-metric",
        type: "metric",
        title: "Sentiment Score",
        icon: Activity,
        description: "Overall sentiment analysis",
      },
      {
        id: "sentiment-chart",
        type: "chart",
        title: "Sentiment Distribution",
        icon: PieChart,
        description: "Pie chart of sentiment breakdown",
      },
    ],
  },
];

// Dummy data for previews
const dummyLineData = [
  { month: "Jan", mentions: 45 },
  { month: "Feb", mentions: 52 },
  { month: "Mar", mentions: 61 },
  { month: "Apr", mentions: 58 },
  { month: "May", mentions: 70 },
  { month: "Jun", mentions: 85 },
];

const dummyBarData = [
  { platform: "ChatGPT", mentions: 120 },
  { platform: "Claude", mentions: 95 },
  { platform: "Gemini", mentions: 78 },
  { platform: "Perplexity", mentions: 65 },
];

const dummyPieData = [
  { name: "Positive", value: 65, color: "#22c55e" },
  { name: "Neutral", value: 25, color: "#94a3b8" },
  { name: "Negative", value: 10, color: "#ef4444" },
];

const ReportBuilder = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const [searchParams] = useSearchParams();
  const templateId = searchParams.get('template_id');

  const [gridRows, setGridRows] = useState<GridRow[]>([]);
  const [draggedWidget, setDraggedWidget] = useState<Widget | null>(null);
  const [draggedRowIndex, setDraggedRowIndex] = useState<number | null>(null);
  const [dragOverRowIndex, setDragOverRowIndex] = useState<number | null>(null);
  const [gridDialogOpen, setGridDialogOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedModule, setSelectedModule] = useState<string>("Information Metrics");
  const [widgetSearchQuery, setWidgetSearchQuery] = useState("");

  // Fetch template data if editing
  const { data: templateData, isLoading: isLoadingTemplate } = useQuery({
    queryKey: ['reportTemplate', templateId],
    queryFn: async () => {
      if (!templateId) return null;
      const response = await apiClient.get(`/reports/templates/${templateId}/`);
      return response;
    },
    enabled: !!templateId,
  });

  // Load template data into state when editing
  useEffect(() => {
    if (templateData && templateId) {
      setIsEditMode(true);
      setTemplateName(templateData.name || "");
      setTemplateDescription(templateData.description || "");
      if (templateData.grid_rows && Array.isArray(templateData.grid_rows)) {
        setGridRows(templateData.grid_rows);
      }
    }
  }, [templateData, templateId]);

  // Fetch domain statistics
  const { data: domainStats, isLoading: isLoadingStats } = useQuery({
    queryKey: ['domainStats', selectedDomain?.id],
    queryFn: async () => {
      if (!selectedDomain?.id) return null;

      // Fetch prompts, prompt groups, and dashboard summary (for platforms)
      const [prompts, promptGroups, dashboardSummary] = await Promise.all([
        apiClient.getPrompts({ domain_id: selectedDomain.id }),
        apiClient.getPromptGroups({ domain_id: selectedDomain.id }),
        apiClient.getDashboardSummary({ domain_id: String(selectedDomain.id), days: 30 })
      ]);

      // Handle prompts response - could be array or paginated object
      const promptsData = Array.isArray(prompts) ? prompts : prompts?.results || prompts?.prompts || [];

      // Extract LLMs from dashboard summary platforms
      const llms = new Set<string>();
      if (Array.isArray(dashboardSummary?.platforms)) {
        dashboardSummary.platforms.forEach((platform: any) => {
          if (platform.platform) {
            llms.add(platform.platform);
          }
        });
      }

      // Handle prompt groups response - the API returns { total_count, groups }
      const groupsCount = Array.isArray(promptGroups)
        ? promptGroups.length
        : (promptGroups?.groups?.length || promptGroups?.results?.length || 0);

      return {
        totalPrompts: promptsData.length,
        totalPromptGroups: groupsCount,
        trackedLLMs: Array.from(llms),
        lastUpdated: new Date().toISOString()
      };
    },
    enabled: !!selectedDomain?.id,
    refetchOnMount: true,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Add new grid row
  const addGridRow = (type: GridType) => {
    let slots: (Widget | null)[] = [];
    switch (type) {
      case "single":
        slots = [null];
        break;
      case "double":
        slots = [null, null];
        break;
      case "triple":
        slots = [null, null, null];
        break;
      case "quad":
        slots = [null, null, null, null];
        break;
    }

    const newRow: GridRow = {
      id: `grid-${Date.now()}`,
      type,
      slots,
    };
    setGridRows([...gridRows, newRow]);
    setGridDialogOpen(false);
  };

  // Handle drag start from sidebar
  const handleDragStart = (widget: Widget) => {
    setDraggedWidget(widget);
  };

  // Handle drag over slot
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  // Handle drop on slot
  const handleDrop = (rowId: string, slotIndex: number) => {
    if (!draggedWidget) return;

    const updatedRows = gridRows.map((row) => {
      if (row.id === rowId) {
        const newSlots = [...row.slots];
        newSlots[slotIndex] = { ...draggedWidget };
        return { ...row, slots: newSlots };
      }
      return row;
    });

    setGridRows(updatedRows);
    setDraggedWidget(null);
  };

  // Remove widget from slot
  const handleRemoveWidget = (rowId: string, slotIndex: number) => {
    const updatedRows = gridRows.map((row) => {
      if (row.id === rowId) {
        const newSlots = [...row.slots];
        newSlots[slotIndex] = null;
        return { ...row, slots: newSlots };
      }
      return row;
    });
    setGridRows(updatedRows);
  };

  // Remove entire grid row
  const handleRemoveRow = (rowId: string) => {
    setGridRows(gridRows.filter((row) => row.id !== rowId));
  };

  // Handle row drag start
  const handleRowDragStart = (e: React.DragEvent, index: number) => {
    setDraggedRowIndex(index);
    e.dataTransfer.effectAllowed = "move";
  };

  // Handle row drag over
  const handleRowDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";

    if (draggedRowIndex === null || draggedRowIndex === index) return;

    setDragOverRowIndex(index);
  };

  // Handle row drag leave
  const handleRowDragLeave = () => {
    setDragOverRowIndex(null);
  };

  // Handle row drop
  const handleRowDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();

    if (draggedRowIndex === null || draggedRowIndex === dropIndex) {
      setDraggedRowIndex(null);
      setDragOverRowIndex(null);
      return;
    }

    const newRows = [...gridRows];
    const [draggedRow] = newRows.splice(draggedRowIndex, 1);
    newRows.splice(dropIndex, 0, draggedRow);

    setGridRows(newRows);
    setDraggedRowIndex(null);
    setDragOverRowIndex(null);
  };

  // Handle row drag end
  const handleRowDragEnd = () => {
    setDraggedRowIndex(null);
    setDragOverRowIndex(null);
  };

  // Handle save template
  const handleSaveTemplate = () => {
    if (gridRows.length === 0) {
      toast({
        title: "Cannot Save",
        description: "Please add at least one grid to your template.",
        variant: "destructive",
      });
      return;
    }
    setSaveDialogOpen(true);
  };

  // Confirm save
  const confirmSave = async () => {
    if (!templateName.trim()) {
      toast({
        title: "Name Required",
        description: "Please enter a template name.",
        variant: "destructive",
      });
      return;
    }

    if (templateDescription.length > 200) {
      toast({
        title: "Description Too Long",
        description: "Description must be 200 characters or less.",
        variant: "destructive",
      });
      return;
    }

    const templatePayload = {
      name: templateName,
      description: templateDescription,
      template_type: "custom",
      grid_rows: gridRows,
    };

    try {
      if (isEditMode && templateId) {
        // Update existing template
        await apiClient.put(`/reports/templates/${templateId}/`, templatePayload);

        toast({
          title: "Template Updated",
          description: `"${templateName}" has been updated successfully.`,
        });
      } else {
        // Create new template
        await apiClient.post("/reports/templates/", templatePayload);

        toast({
          title: "Template Saved",
          description: `"${templateName}" has been saved successfully.`,
        });
      }

      setSaveDialogOpen(false);
      navigate("/reports");
    } catch (error: any) {
      console.error("Error saving template:", error);
      toast({
        title: isEditMode ? "Update Failed" : "Save Failed",
        description: error.message || "Failed to save template. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Render widget preview with dummy data
  const renderWidgetPreview = (widget: Widget) => {
    switch (widget.id) {
      case "mentions-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Total Mentions</p>
            <p className="text-4xl font-bold text-blue-600">1,234</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +12.5% from last month
            </p>
          </Card>
        );

      case "sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Sentiment Score</p>
            <p className="text-4xl font-bold text-green-600">8.4/10</p>
            <p className="text-sm text-muted-foreground mt-2">Mostly Positive</p>
          </Card>
        );

      case "competitors-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Competitors Tracked</p>
            <p className="text-4xl font-bold text-purple-600">8</p>
            <p className="text-sm text-muted-foreground mt-2">Active monitoring</p>
          </Card>
        );

      case "share-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Share of Voice</p>
            <p className="text-4xl font-bold text-orange-600">42%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +5% increase
            </p>
          </Card>
        );

      case "mentions-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsLineChart data={dummyLineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="mentions" stroke="#3b82f6" strokeWidth={2} />
              </RechartsLineChart>
            </ResponsiveContainer>
          </Card>
        );

      case "sentiment-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsPieChart>
                <Pie
                  data={dummyPieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {dummyPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
          </Card>
        );

      case "platform-chart":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <ResponsiveContainer width="100%" height={200}>
              <RechartsBarChart data={dummyBarData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="mentions" fill="#8b5cf6" />
              </RechartsBarChart>
            </ResponsiveContainer>
          </Card>
        );

      case "topics-table":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Topic</th>
                    <th className="text-right py-2">Mentions</th>
                    <th className="text-right py-2">Trend</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2">AI Integration</td>
                    <td className="text-right">145</td>
                    <td className="text-right text-green-600">↑ 12%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Product Features</td>
                    <td className="text-right">98</td>
                    <td className="text-right text-green-600">↑ 8%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Pricing</td>
                    <td className="text-right">76</td>
                    <td className="text-right text-red-600">↓ 3%</td>
                  </tr>
                  <tr>
                    <td className="py-2">Customer Support</td>
                    <td className="text-right">52</td>
                    <td className="text-right text-green-600">↑ 15%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      case "competitors-table":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead className="border-b">
                  <tr>
                    <th className="text-left py-2">Competitor</th>
                    <th className="text-right py-2">Mentions</th>
                    <th className="text-right py-2">Share</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2">Competitor A</td>
                    <td className="text-right">234</td>
                    <td className="text-right">28%</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-2">Competitor B</td>
                    <td className="text-right">189</td>
                    <td className="text-right">23%</td>
                  </tr>
                  <tr>
                    <td className="py-2">Competitor C</td>
                    <td className="text-right">156</td>
                    <td className="text-right">19%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        );

      case "summary-text":
        return (
          <Card className="p-6">
            <h3 className="font-semibold mb-4">{widget.title}</h3>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                This month showed strong performance across all AI platforms with a 12.5% increase in
                total mentions compared to the previous period.
              </p>
              <p>
                Sentiment remains predominantly positive at 65%, with ChatGPT leading in mention volume
                at 120 mentions, followed by Claude at 95 mentions.
              </p>
              <p>
                Key topics driving visibility include AI Integration and Product Features, while
                maintaining a healthy 42% share of voice in the competitive landscape.
              </p>
            </div>
          </Card>
        );

      case "total-prompts-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Total Prompts</p>
            <p className="text-4xl font-bold text-indigo-600">{domainStats?.totalPrompts || 0}</p>
            <p className="text-sm text-muted-foreground mt-2">Tracked prompts</p>
          </Card>
        );

      case "total-citations-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Total Citations</p>
            <p className="text-4xl font-bold text-blue-600">342</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +18.2% from last month
            </p>
          </Card>
        );

      case "total-mentions-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Total Mentions</p>
            <p className="text-4xl font-bold text-cyan-600">1,547</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +24.5% from last month
            </p>
          </Card>
        );

      case "visibility-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Visibility Score</p>
            <p className="text-4xl font-bold text-emerald-600">87.5</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +6.3% improvement
            </p>
          </Card>
        );

      case "avg-position-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Avg Position</p>
            <p className="text-4xl font-bold text-amber-600">2.4</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              -0.3 (improved)
            </p>
          </Card>
        );

      case "positive-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Positive Sentiment</p>
            <p className="text-4xl font-bold text-green-600">68%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Smile className="h-4 w-4" />
              Majority positive
            </p>
          </Card>
        );

      case "neutral-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-slate-500/10 to-slate-500/5 border-slate-200">
            <p className="text-sm text-muted-foreground mb-2">Neutral Sentiment</p>
            <p className="text-4xl font-bold text-slate-600">24%</p>
            <p className="text-sm text-muted-foreground mt-2 flex items-center gap-1">
              <Meh className="h-4 w-4" />
              Balanced feedback
            </p>
          </Card>
        );

      case "negative-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Negative Sentiment</p>
            <p className="text-4xl font-bold text-red-600">8%</p>
            <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
              <Frown className="h-4 w-4" />
              Minimal negative
            </p>
          </Card>
        );

      // New Information Metrics
      case "engagement-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Engagement Score</p>
            <p className="text-4xl font-bold text-violet-600">92.3</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +8.1% improvement
            </p>
          </Card>
        );

      case "mention-rate-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-sky-500/10 to-sky-500/5 border-sky-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Rate</p>
            <p className="text-4xl font-bold text-sky-600">67%</p>
            <p className="text-sm text-muted-foreground mt-2">Of total prompts</p>
          </Card>
        );

      case "mention-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-teal-500/10 to-teal-500/5 border-teal-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Growth</p>
            <p className="text-4xl font-bold text-teal-600">+24.5%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              vs last month
            </p>
          </Card>
        );

      case "platform-coverage-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-pink-500/10 to-pink-500/5 border-pink-200">
            <p className="text-sm text-muted-foreground mb-2">Platform Coverage</p>
            <p className="text-4xl font-bold text-pink-600">5/5</p>
            <p className="text-sm text-muted-foreground mt-2">All platforms active</p>
          </Card>
        );

      case "citation-rate-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Rate</p>
            <p className="text-4xl font-bold text-indigo-600">2.8</p>
            <p className="text-sm text-muted-foreground mt-2">Citations per mention</p>
          </Card>
        );

      case "citation-density-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-fuchsia-500/10 to-fuchsia-500/5 border-fuchsia-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Density</p>
            <p className="text-4xl font-bold text-fuchsia-600">3.2</p>
            <p className="text-sm text-muted-foreground mt-2">Avg per response</p>
          </Card>
        );

      case "primary-sources-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-rose-500/10 to-rose-500/5 border-rose-200">
            <p className="text-sm text-muted-foreground mb-2">Primary Sources</p>
            <p className="text-4xl font-bold text-rose-600">156</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +12 this month
            </p>
          </Card>
        );

      case "avg-sentiment-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-lime-500/10 to-lime-500/5 border-lime-200">
            <p className="text-sm text-muted-foreground mb-2">Average Sentiment Score</p>
            <p className="text-4xl font-bold text-lime-600">7.8/10</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Smile className="h-4 w-4" />
              Highly positive
            </p>
          </Card>
        );

      case "sentiment-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Sentiment Trend</p>
            <p className="text-4xl font-bold text-emerald-600">+0.4</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Improving trend
            </p>
          </Card>
        );

      case "market-position-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-purple-500/10 to-purple-500/5 border-purple-200">
            <p className="text-sm text-muted-foreground mb-2">Market Position</p>
            <p className="text-4xl font-bold text-purple-600">#2</p>
            <p className="text-sm text-muted-foreground mt-2">Out of 8 competitors</p>
          </Card>
        );

      case "competitor-gap-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Competitor Gap</p>
            <p className="text-4xl font-bold text-orange-600">-145</p>
            <p className="text-sm text-muted-foreground mt-2">Behind leader</p>
          </Card>
        );

      case "market-share-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-500/5 border-amber-200">
            <p className="text-sm text-muted-foreground mb-2">Market Share Trend</p>
            <p className="text-4xl font-bold text-amber-600">+3.2%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Growing share
            </p>
          </Card>
        );

      case "health-score-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border-cyan-200">
            <p className="text-sm text-muted-foreground mb-2">Health Score</p>
            <p className="text-4xl font-bold text-cyan-600">94/100</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <Activity className="h-4 w-4" />
              Excellent health
            </p>
          </Card>
        );

      case "content-quality-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Content Quality Score</p>
            <p className="text-4xl font-bold text-blue-600">88/100</p>
            <p className="text-sm text-muted-foreground mt-2">High quality content</p>
          </Card>
        );

      case "topics-covered-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-500/5 border-indigo-200">
            <p className="text-sm text-muted-foreground mb-2">Topics Covered</p>
            <p className="text-4xl font-bold text-indigo-600">24</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              +6 new topics
            </p>
          </Card>
        );

      case "answer-coverage-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Answer Coverage</p>
            <p className="text-4xl font-bold text-violet-600">78%</p>
            <p className="text-sm text-muted-foreground mt-2">Of all prompts</p>
          </Card>
        );

      case "active-alerts-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Active Alerts</p>
            <p className="text-4xl font-bold text-red-600">3</p>
            <p className="text-sm text-muted-foreground mt-2">Require attention</p>
          </Card>
        );

      case "critical-issues-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200">
            <p className="text-sm text-muted-foreground mb-2">Critical Issues</p>
            <p className="text-4xl font-bold text-red-600">1</p>
            <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              High priority
            </p>
          </Card>
        );

      case "broken-links-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 border-yellow-200">
            <p className="text-sm text-muted-foreground mb-2">Broken Links</p>
            <p className="text-4xl font-bold text-yellow-600">7</p>
            <p className="text-sm text-muted-foreground mt-2">Need fixing</p>
          </Card>
        );

      case "misinformation-cases-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-500/5 border-orange-200">
            <p className="text-sm text-muted-foreground mb-2">Misinformation Cases</p>
            <p className="text-4xl font-bold text-orange-600">2</p>
            <p className="text-sm text-orange-600 mt-2 flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              Under review
            </p>
          </Card>
        );

      case "mention-growth-percent-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200">
            <p className="text-sm text-muted-foreground mb-2">Mention Growth %</p>
            <p className="text-4xl font-bold text-green-600">+24.5%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Strong growth
            </p>
          </Card>
        );

      case "visibility-trend-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border-emerald-200">
            <p className="text-sm text-muted-foreground mb-2">Visibility Trend</p>
            <p className="text-4xl font-bold text-emerald-600">+6.3%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Improving visibility
            </p>
          </Card>
        );

      case "citation-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-500/5 border-blue-200">
            <p className="text-sm text-muted-foreground mb-2">Citation Growth</p>
            <p className="text-4xl font-bold text-blue-600">+18.2%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              More citations
            </p>
          </Card>
        );

      case "engagement-growth-metric":
        return (
          <Card className="p-6 bg-gradient-to-br from-violet-500/10 to-violet-500/5 border-violet-200">
            <p className="text-sm text-muted-foreground mb-2">Engagement Growth</p>
            <p className="text-4xl font-bold text-violet-600">+8.1%</p>
            <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              Better engagement
            </p>
          </Card>
        );

      default:
        return (
          <Card className="p-6 bg-muted">
            <p className="text-sm text-muted-foreground">Preview not available</p>
          </Card>
        );
    }
  };

  return (
    <div className="h-screen flex flex-col bg-background animate-fade-in">
      {/* Header */}
      <div className="p-8 pb-4 border-b border-border/50">
        <div className="flex items-center justify-between">
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
              <h1 className="text-3xl font-bold tracking-tight font-inter">
                {isEditMode ? "Edit Template" : "Report Template Builder"}
              </h1>
              <p className="text-muted-foreground mt-1">
                {isEditMode
                  ? "Update your custom report template"
                  : "Drag and drop widgets to create your custom report template"}
              </p>
            </div>
          </div>
          <Button onClick={handleSaveTemplate}>
            <Save className="h-4 w-4 mr-2" />
            {isEditMode ? "Update Template" : "Save Template"}
          </Button>
        </div>
      </div>

      {/* Loading state */}
      {isLoadingTemplate && templateId && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-muted-foreground">Loading template...</p>
          </div>
        </div>
      )}

      {/* Main content */}
      {(!isLoadingTemplate || !templateId) && (
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Available Widgets */}
        <div className="w-80 border-r border-border/50 bg-card/50 backdrop-blur-sm p-6 overflow-y-auto">
          <h2 className="text-lg font-semibold font-inter mb-4">Available Widgets</h2>

          {/* Module Selector Dropdown */}
          <Select value={selectedModule} onValueChange={setSelectedModule}>
            <SelectTrigger className="mb-4">
              <SelectValue placeholder="Select widget category" />
            </SelectTrigger>
            <SelectContent>
              {widgetModules.map((module) => (
                <SelectItem key={module.name} value={module.name}>
                  {module.name} ({module.widgets.length})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Widget Search Input */}
          <div className="relative mb-4">
            <Input
              type="text"
              placeholder="Search widgets..."
              value={widgetSearchQuery}
              onChange={(e) => setWidgetSearchQuery(e.target.value)}
              className="pr-8"
            />
            {widgetSearchQuery && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setWidgetSearchQuery("")}
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>

          {/* Show widgets when module is selected */}
          {selectedModule && (() => {
            const filteredWidgets = widgetModules
              .find((m) => m.name === selectedModule)
              ?.widgets.filter((widget) =>
                widget.title.toLowerCase().includes(widgetSearchQuery.toLowerCase()) ||
                widget.description.toLowerCase().includes(widgetSearchQuery.toLowerCase())
              ) || [];

            return (
              <div className="space-y-3">
                {filteredWidgets.length > 0 ? (
                  filteredWidgets.map((widget) => (
                    <Card
                      key={widget.id}
                      draggable
                      onDragStart={() => handleDragStart(widget)}
                      className="p-3 cursor-move hover:border-primary transition-all duration-200 hover:shadow-md border-border/50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10">
                          <widget.icon className="h-4 w-4 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-medium text-sm">{widget.title}</h3>
                        </div>
                        <Grip className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      </div>
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="text-sm">No widgets found</p>
                    {widgetSearchQuery && (
                      <p className="text-xs mt-1">Try a different search term</p>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>

        {/* Canvas - PDF-like Preview Area */}
        <div className="flex-1 p-8 overflow-y-auto bg-gradient-to-br from-muted/30 to-muted/50">
          <div className="max-w-[850px] mx-auto">
            {/* PDF-like white canvas */}
            <div className="bg-white rounded-lg border border-border min-h-[1100px] p-12 space-y-6">
              {/* Default Report Header */}
              {selectedDomain && (
                <div className="border-b border-border pb-4 mb-6">
                  {/* Brand Info - Compact */}
                  <div className="flex items-center gap-3 mb-3">
                    <img
                      src={getFaviconUrl(selectedDomain.url, 32)}
                      alt={`${selectedDomain.name} favicon`}
                      className="h-8 w-8 rounded"
                      onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 32)}
                    />
                    <div className="flex-1">
                      <h2 className="text-xl font-bold text-gray-900">{selectedDomain.name}</h2>
                      <p className="text-xs text-muted-foreground">{selectedDomain.url}</p>
                    </div>
                  </div>

                  {/* Statistics - Compact Single Line */}
                  <div className="flex items-center gap-6 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Prompts:</span>
                      <span className="text-gray-900 font-semibold">
                        {isLoadingStats ? "..." : (domainStats?.totalPrompts ?? 0)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Groups:</span>
                      <span className="text-gray-900 font-semibold">
                        {isLoadingStats ? "..." : (domainStats?.totalPromptGroups ?? 0)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">LLMs:</span>
                      <div className="flex flex-wrap gap-1">
                        {isLoadingStats ? (
                          <span className="text-muted-foreground">...</span>
                        ) : domainStats?.trackedLLMs && domainStats.trackedLLMs.length > 0 ? (
                          domainStats.trackedLLMs.map((llm: string) => (
                            <Badge key={llm} variant="outline" className="text-xs py-0 h-5">
                              {llm}
                            </Badge>
                          ))
                        ) : (
                          <span className="text-muted-foreground">None</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Dates - Compact Single Line */}
                  <div className="flex items-center gap-6 text-xs text-muted-foreground mt-2">
                    <div className="flex items-center gap-2">
                      <span>Report Created:</span>
                      <span className="text-gray-900">
                        {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>Data Updated:</span>
                      <span className="text-gray-900">
                        {isLoadingStats ? "..." : (
                          domainStats?.lastUpdated
                            ? new Date(domainStats.lastUpdated).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                            : selectedDomain.updated_at
                            ? new Date(selectedDomain.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                            : new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {gridRows.length === 0 ? (
                <div className="h-full flex items-center justify-center py-32">
                  <div className="text-center max-w-md">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                      <FileText className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">Start Building Your Report</h3>
                    <p className="text-muted-foreground mb-6">
                      Click the button below to add a grid, then drag widgets from the sidebar into
                      the grid slots.
                    </p>
                    <Button onClick={() => setGridDialogOpen(true)} size="lg">
                      <Plus className="h-5 w-5 mr-2" />
                      Add Grid
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  {gridRows.map((row, rowIndex) => (
                    <div
                      key={row.id}
                      draggable
                      onDragStart={(e) => handleRowDragStart(e, rowIndex)}
                      onDragOver={(e) => handleRowDragOver(e, rowIndex)}
                      onDragLeave={handleRowDragLeave}
                      onDrop={(e) => handleRowDrop(e, rowIndex)}
                      onDragEnd={handleRowDragEnd}
                      className={`relative group transition-all duration-200 ${
                        draggedRowIndex === rowIndex ? 'opacity-50 scale-95' : ''
                      } ${
                        dragOverRowIndex === rowIndex && draggedRowIndex !== rowIndex
                          ? 'border-2 border-primary border-dashed rounded-lg p-2 bg-primary/5'
                          : 'mb-6'
                      }`}
                    >
                      {/* Drag handle and remove button container */}
                      <div className="absolute -top-3 -left-3 right-3 flex items-center justify-between z-10">
                        <div className="flex items-center gap-2 bg-background border border-border rounded-md px-2 py-1 shadow-sm opacity-0 group-hover:opacity-100 transition-opacity cursor-move">
                          <Grip className="h-4 w-4 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">Drag to reorder</span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemoveRow(row.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity h-7 w-7 p-0 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>

                      {/* Grid slots */}
                      <div
                        className={`grid gap-4 mt-4 ${
                          row.type === "single"
                            ? "grid-cols-1"
                            : row.type === "double"
                            ? "grid-cols-2"
                            : row.type === "triple"
                            ? "grid-cols-3"
                            : "grid-cols-4"
                        }`}
                      >
                        {row.slots.map((widget, slotIndex) => (
                          <div
                            key={`${row.id}-${slotIndex}`}
                            className="relative min-h-[200px] border-2 border-dashed border-border rounded-lg p-4 transition-all hover:border-primary/50"
                            onDragOver={handleDragOver}
                            onDrop={() => handleDrop(row.id, slotIndex)}
                          >
                            {widget ? (
                              <div className="relative group/widget h-full">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleRemoveWidget(row.id, slotIndex)}
                                  className="absolute -top-2 -right-2 opacity-0 group-hover/widget:opacity-100 transition-opacity z-10 h-6 w-6 p-0 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                                {renderWidgetPreview(widget)}
                              </div>
                            ) : (
                              <div className="h-full flex items-center justify-center text-muted-foreground">
                                <div className="text-center">
                                  <LayoutGrid className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                  <p className="text-sm">Drop widget here</p>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}

                  {/* Add more grids button */}
                  <div className="flex justify-center pt-4">
                    <Button
                      onClick={() => setGridDialogOpen(true)}
                      variant="outline"
                      className="border-dashed"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Grid
                    </Button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Grid Selection Dialog */}
      <Dialog open={gridDialogOpen} onOpenChange={setGridDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Select Grid Layout</DialogTitle>
            <DialogDescription>
              Choose how many columns you want in this grid row.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-4">
            <Card
              className="p-6 cursor-pointer hover:border-primary transition-all hover:shadow-md"
              onClick={() => addGridRow("single")}
            >
              <div className="text-center mb-4">
                <h3 className="font-semibold mb-2">Single Column</h3>
                <p className="text-sm text-muted-foreground">Full width grid for large widgets</p>
              </div>
              <div className="h-16 border-2 border-dashed border-border rounded"></div>
            </Card>

            <Card
              className="p-6 cursor-pointer hover:border-primary transition-all hover:shadow-md"
              onClick={() => addGridRow("double")}
            >
              <div className="text-center mb-4">
                <h3 className="font-semibold mb-2">Two Columns</h3>
                <p className="text-sm text-muted-foreground">Side-by-side widgets</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
              </div>
            </Card>

            <Card
              className="p-6 cursor-pointer hover:border-primary transition-all hover:shadow-md"
              onClick={() => addGridRow("triple")}
            >
              <div className="text-center mb-4">
                <h3 className="font-semibold mb-2">Three Columns</h3>
                <p className="text-sm text-muted-foreground">Three widgets in a row</p>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
              </div>
            </Card>

            <Card
              className="p-6 cursor-pointer hover:border-primary transition-all hover:shadow-md"
              onClick={() => addGridRow("quad")}
            >
              <div className="text-center mb-4">
                <h3 className="font-semibold mb-2">Four Columns</h3>
                <p className="text-sm text-muted-foreground">Four widgets in a row</p>
              </div>
              <div className="grid grid-cols-4 gap-1">
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
                <div className="h-16 border-2 border-dashed border-border rounded"></div>
              </div>
            </Card>
          </div>
        </DialogContent>
      </Dialog>

      {/* Save Template Dialog */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {isEditMode ? "Update Report Template" : "Save Report Template"}
            </DialogTitle>
            <DialogDescription>
              {isEditMode
                ? "Update the name and description for your custom report template."
                : "Enter a name and description for your custom report template."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Template Name *
              </label>
              <Input
                id="name"
                placeholder="e.g., Monthly Performance Report"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="description" className="text-sm font-medium">
                Description
                <span className="text-muted-foreground ml-1">
                  ({templateDescription.length}/200 characters)
                </span>
              </label>
              <Textarea
                id="description"
                placeholder="Brief description of what this report template includes..."
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value.slice(0, 200))}
                maxLength={200}
                rows={3}
              />
            </div>
            <div className="bg-muted p-3 rounded-lg">
              <p className="text-sm text-muted-foreground">
                <strong>{gridRows.length}</strong> grid row{gridRows.length !== 1 ? "s" : ""} with{" "}
                <strong>
                  {gridRows.reduce((acc, row) => acc + row.slots.filter((s) => s !== null).length, 0)}
                </strong>{" "}
                widget{gridRows.reduce((acc, row) => acc + row.slots.filter((s) => s !== null).length, 0) !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmSave}>
              {isEditMode ? "Update Template" : "Save Template"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ReportBuilder;
