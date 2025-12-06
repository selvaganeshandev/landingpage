import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
  const [gridRows, setGridRows] = useState<GridRow[]>([]);
  const [draggedWidget, setDraggedWidget] = useState<Widget | null>(null);
  const [gridDialogOpen, setGridDialogOpen] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDescription, setTemplateDescription] = useState("");

  // Fetch domain statistics
  const { data: domainStats } = useQuery({
    queryKey: ['domainStats', selectedDomain?.id],
    queryFn: async () => {
      if (!selectedDomain?.id) return null;

      // Fetch prompts and prompt groups
      const [prompts, promptGroups] = await Promise.all([
        apiClient.getPrompts({ domain_id: selectedDomain.id }),
        apiClient.getPromptGroups({ domain_id: selectedDomain.id })
      ]);

      // Get unique LLMs from prompts
      const promptsData = Array.isArray(prompts) ? prompts : prompts?.results || [];
      const llms = new Set<string>();
      promptsData.forEach((prompt: any) => {
        if (prompt.analytics) {
          prompt.analytics.forEach((analytics: any) => {
            if (analytics.platform) {
              llms.add(analytics.platform);
            }
          });
        }
      });

      return {
        totalPrompts: promptsData.length,
        totalPromptGroups: Array.isArray(promptGroups) ? promptGroups.length : promptGroups?.results?.length || 0,
        trackedLLMs: Array.from(llms)
      };
    },
    enabled: !!selectedDomain?.id
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
  const confirmSave = () => {
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

    const templateData = {
      name: templateName,
      description: templateDescription,
      gridRows,
    };

    console.log("Saving template:", templateData);

    toast({
      title: "Template Saved",
      description: `"${templateName}" has been saved successfully.`,
    });

    setSaveDialogOpen(false);
    navigate("/reports");
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
              onClick={() => navigate("/reports")}
              className="border-border/50"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold tracking-tight font-inter">
                Report Template Builder
              </h1>
              <p className="text-muted-foreground mt-1">
                Drag and drop widgets to create your custom report template
              </p>
            </div>
          </div>
          <Button onClick={handleSaveTemplate}>
            <Save className="h-4 w-4 mr-2" />
            Save Template
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Available Widgets */}
        <div className="w-80 border-r border-border/50 bg-card/50 backdrop-blur-sm p-6 overflow-y-auto">
          <h2 className="text-lg font-semibold font-inter mb-4">Available Widgets</h2>
          <Accordion type="multiple" defaultValue={widgetModules.map((m) => m.name)} className="space-y-2">
            {widgetModules.map((module) => (
              <AccordionItem key={module.name} value={module.name} className="border rounded-lg px-4 bg-card/80">
                <AccordionTrigger className="text-sm font-semibold hover:no-underline">
                  {module.name}
                  <span className="ml-2 text-xs text-muted-foreground">({module.widgets.length})</span>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 pt-2">
                    {module.widgets.map((widget) => (
                      <Card
                        key={widget.id}
                        draggable
                        onDragStart={() => handleDragStart(widget)}
                        className="p-3 cursor-move hover:border-primary transition-all duration-200 hover:shadow-md border-border/50"
                      >
                        <div className="flex items-start gap-3">
                          <div className="p-2 rounded-lg bg-primary/10">
                            <widget.icon className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-sm mb-1">{widget.title}</h3>
                            <p className="text-xs text-muted-foreground">{widget.description}</p>
                          </div>
                          <Grip className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        </div>
                      </Card>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        {/* Canvas - PDF-like Preview Area */}
        <div className="flex-1 p-8 overflow-y-auto bg-gradient-to-br from-muted/30 to-muted/50">
          <div className="max-w-[850px] mx-auto">
            {/* PDF-like white canvas */}
            <div className="bg-white rounded-lg border border-border min-h-[1100px] p-12 space-y-6">
              {/* Default Report Header */}
              {selectedDomain && (
                <div className="border-b border-border pb-6 mb-8">
                  {/* Brand Info */}
                  <div className="flex items-start gap-4 mb-6">
                    <img
                      src={getFaviconUrl(selectedDomain.url, 48)}
                      alt={`${selectedDomain.name} favicon`}
                      className="h-12 w-12 rounded"
                      onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 48)}
                    />
                    <div className="flex-1">
                      <h2 className="text-2xl font-bold text-gray-900">{selectedDomain.name}</h2>
                      <p className="text-sm text-muted-foreground mt-1">{selectedDomain.url}</p>
                    </div>
                  </div>

                  {/* Statistics Grid */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-muted/30 rounded-lg p-4">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Total Prompts</p>
                      <p className="text-2xl font-bold text-gray-900">{domainStats?.totalPrompts || 0}</p>
                    </div>
                    <div className="bg-muted/30 rounded-lg p-4">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Prompt Groups</p>
                      <p className="text-2xl font-bold text-gray-900">{domainStats?.totalPromptGroups || 0}</p>
                    </div>
                    <div className="bg-muted/30 rounded-lg p-4">
                      <p className="text-xs font-medium text-muted-foreground mb-1">Tracked LLMs</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {domainStats?.trackedLLMs && domainStats.trackedLLMs.length > 0 ? (
                          domainStats.trackedLLMs.map((llm: string) => (
                            <Badge key={llm} variant="secondary" className="text-xs">
                              {llm}
                            </Badge>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">None</p>
                        )}
                      </div>
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
                    <div key={row.id} className="relative group">
                      {/* Remove row button */}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveRow(row.id)}
                        className="absolute -top-3 -right-3 opacity-0 group-hover:opacity-100 transition-opacity z-10 h-7 w-7 p-0 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        <X className="h-4 w-4" />
                      </Button>

                      {/* Grid slots */}
                      <div
                        className={`grid gap-4 ${
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
            <DialogTitle>Save Report Template</DialogTitle>
            <DialogDescription>
              Enter a name and description for your custom report template.
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
            <Button onClick={confirmSave}>Save Template</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ReportBuilder;
