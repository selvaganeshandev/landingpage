import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader } from "@/components/PageLoader";
import { useDomainStore } from "@/stores/domainStore";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import {
  Link2,
  ExternalLink,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Globe,
  Building2,
  ArrowUpRight,
  FileText,
  RefreshCw,
  Loader2,
  LinkIcon,
  TrendingUp,
} from "lucide-react";

const Citations = () => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState("all");
  const pageSize = 20;

  const domainId = selectedDomain?.id?.toString() || "";

  // Fetch dashboard data
  const { data: dashboardData, isLoading: dashboardLoading, refetch: refetchDashboard } = useQuery({
    queryKey: ["citationsDashboard", domainId],
    queryFn: () => apiClient.getCitationsDashboard({ domain_id: domainId }),
    enabled: !!domainId,
  });

  // Fetch citations list
  const { data: citationsData, isLoading: citationsLoading, refetch: refetchCitations } = useQuery({
    queryKey: ["citations", domainId, statusFilter, sourceTypeFilter, platformFilter, searchQuery, currentPage],
    queryFn: () =>
      apiClient.getCitations({
        domain_id: domainId,
        status: statusFilter !== "all" ? statusFilter : undefined,
        source_type: sourceTypeFilter !== "all" ? sourceTypeFilter : undefined,
        platform: platformFilter !== "all" ? platformFilter : undefined,
        search: searchQuery || undefined,
        page: currentPage,
        page_size: pageSize,
      }),
    enabled: !!domainId,
  });

  // Fetch citations by source
  const { data: sourceData, refetch: refetchSource } = useQuery({
    queryKey: ["citationsBySource", domainId],
    queryFn: () => apiClient.getCitationsBySource({ domain_id: domainId, limit: 10 }),
    enabled: !!domainId,
  });

  const handleExport = () => {
    toast({
      title: "Exporting Report",
      description: "Your citations report is being generated...",
    });
  };

  const handleRefresh = async () => {
    await Promise.all([refetchDashboard(), refetchCitations(), refetchSource()]);
    toast({
      title: "Data refreshed",
      description: "Citations data has been updated.",
    });
  };

  if (!selectedDomain) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[400px] bg-background animate-fade-in">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Link2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-2">No Domain Selected</h2>
        <p className="text-muted-foreground text-center max-w-md">
          Please select a domain from the dropdown to view citation analytics.
        </p>
      </div>
    );
  }

  if (dashboardLoading) {
    return <PageLoader />;
  }

  const summary = dashboardData?.summary || {
    total_citations: 0,
    unique_sources: 0,
    your_domain_citations: 0,
    competitor_citations: 0,
    citation_rate: 0,
    avg_citations_per_response: 0,
    broken_links: 0,
    new_sources_7d: 0,
  };

  const statusBreakdown = dashboardData?.status_breakdown || {};
  const platformBreakdown = dashboardData?.platform_breakdown || {};
  const topSources = sourceData?.results || dashboardData?.top_domains || [];
  const citations = citationsData?.results || [];
  const totalCitations = citationsData?.total || 0;
  const totalPages = Math.ceil(totalCitations / pageSize);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "valid":
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case "broken":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "blocked":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      case "pending":
        return <Clock className="h-4 w-4 text-muted-foreground" />;
      default:
        return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const truncateUrl = (url: string, maxLength: number = 60) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + "...";
  };

  const filteredCitations = citations.filter((c: any) => {
    if (activeTab === "your_domain") return c.is_your_domain;
    if (activeTab === "third_party") return !c.is_your_domain;
    return true;
  });

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Citations</h1>
          <p className="text-muted-foreground mt-2">
            Track and analyze source citations across AI platforms
          </p>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Total Citations</p>
              <h3 className="text-4xl font-bold mt-2">{summary.total_citations}</h3>
            </div>
            <div className="p-3 rounded-xl bg-primary/10">
              <Link2 className="h-6 w-6 text-primary" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <ArrowUpRight className="h-4 w-4 text-success" />
            <span className="text-success font-medium">+{summary.new_sources_7d}</span>
            <span className="text-muted-foreground">new this week</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Unique Sources</p>
              <h3 className="text-4xl font-bold mt-2">{summary.unique_sources}</h3>
            </div>
            <div className="p-3 rounded-xl bg-secondary/10">
              <Globe className="h-6 w-6 text-secondary" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Distinct domains cited</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Your Domain</p>
              <h3 className="text-4xl font-bold text-success mt-2">{summary.your_domain_citations}</h3>
            </div>
            <div className="p-3 rounded-xl bg-success/10">
              <Building2 className="h-6 w-6 text-success" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Citations to your website</span>
          </div>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground font-medium">Broken Links</p>
              <h3 className="text-4xl font-bold text-destructive mt-2">{summary.broken_links}</h3>
            </div>
            <div className="p-3 rounded-xl bg-destructive/10">
              <XCircle className="h-6 w-6 text-destructive" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Need attention</span>
          </div>
        </Card>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Citation Rate</p>
              <p className="text-2xl font-bold mt-1">{summary.citation_rate}%</p>
            </div>
            <TrendingUp className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Of responses include citations</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Avg Citations/Response</p>
              <p className="text-2xl font-bold mt-1">{summary.avg_citations_per_response}</p>
            </div>
            <LinkIcon className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Average per AI response</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Valid Links</p>
              <p className="text-2xl font-bold text-success mt-1">{statusBreakdown.valid || 0}</p>
            </div>
            <CheckCircle2 className="h-5 w-5 text-success" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Working citations</p>
        </Card>

        <Card className="p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Pending</p>
              <p className="text-2xl font-bold text-warning mt-1">{statusBreakdown.pending || 0}</p>
            </div>
            <Clock className="h-5 w-5 text-warning" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">Awaiting validation</p>
        </Card>
      </div>

      {/* Platform & Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Citations by Platform */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Citations by Platform</h3>
          <div className="space-y-4">
            {Object.entries(platformBreakdown).length > 0 ? (
              Object.entries(platformBreakdown).map(([platform, count]: [string, any]) => {
                const total = Object.values(platformBreakdown).reduce((a: any, b: any) => a + b, 0) as number;
                const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
                return (
                  <div key={platform} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium capitalize">{platform}</span>
                      <span className="text-sm text-muted-foreground">{count} ({percentage}%)</span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden bg-muted">
                      <div
                        className="h-full bg-primary rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
                  <Globe className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm">No platform data available</p>
              </div>
            )}
          </div>
        </Card>

        {/* Top Cited Sources */}
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-4">Top Cited Sources</h3>
          <div className="space-y-3">
            {topSources.length > 0 ? (
              topSources.slice(0, 5).map((source: any, index: number) => (
                <div key={source.source_domain || source.domain} className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                      index === 0
                        ? "bg-gradient-to-br from-primary to-secondary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}>
                      {index + 1}
                    </div>
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${source.source_domain || source.domain}&sz=32`}
                      alt=""
                      className="w-4 h-4"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                    <div className="flex flex-col">
                      <span className="text-sm truncate max-w-[160px] font-medium">{source.source_domain || source.domain}</span>
                      {source.platforms && source.platforms.length > 0 && (
                        <span className="text-xs text-muted-foreground">{source.platforms.join(', ')}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary">{source.mention_count || source.count}</Badge>
                    {source.valid_count !== undefined && (
                      <div className="text-xs text-muted-foreground mt-1">
                        {source.valid_count} valid
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
                  <Globe className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-muted-foreground text-sm">No sources data available</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Citations Table */}
      <Card className="p-6 border border-border">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
            <TabsList className="bg-muted/50 p-1 border border-border">
              <TabsTrigger value="all" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                All Citations
              </TabsTrigger>
              <TabsTrigger value="your_domain" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                Your Domain
              </TabsTrigger>
              <TabsTrigger value="third_party" className="data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:text-white">
                Third Party
              </TabsTrigger>
            </TabsList>

            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search URLs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-[200px]"
                />
              </div>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="success">Valid</SelectItem>
                  <SelectItem value="failed">Broken</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>

              <Select value={platformFilter} onValueChange={setPlatformFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue placeholder="Platform" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Platforms</SelectItem>
                  <SelectItem value="ChatGPT">ChatGPT</SelectItem>
                  <SelectItem value="Claude">Claude</SelectItem>
                  <SelectItem value="Google Gemini">Gemini</SelectItem>
                  <SelectItem value="Perplexity">Perplexity</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <TabsContent value={activeTab}>
            <CitationsTable
              citations={filteredCitations}
              isLoading={citationsLoading}
              getStatusIcon={getStatusIcon}
              formatDate={formatDate}
              truncateUrl={truncateUrl}
            />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-muted-foreground">
                  Showing {(currentPage - 1) * pageSize + 1} to{" "}
                  {Math.min(currentPage * pageSize, totalCitations)} of {totalCitations} citations
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
};

// Citations Table Component
const CitationsTable = ({
  citations,
  isLoading,
  getStatusIcon,
  formatDate,
  truncateUrl,
}: {
  citations: any[];
  isLoading: boolean;
  getStatusIcon: (status: string) => JSX.Element;
  formatDate: (date: string) => string;
  truncateUrl: (url: string, maxLength?: number) => string;
}) => {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-muted-foreground">Loading citations...</p>
      </div>
    );
  }

  if (citations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
          <Link2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No citations found</h3>
        <p className="text-muted-foreground">Try adjusting your filters to see more results</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30">
            <TableHead className="w-[40px] py-2 px-2">Status</TableHead>
            <TableHead className="py-2 px-2">Source URL</TableHead>
            <TableHead className="py-2 px-2">Domain</TableHead>
            <TableHead className="text-center py-2 px-2">Mentions</TableHead>
            <TableHead className="py-2 px-2">Platform</TableHead>
            <TableHead className="py-2 px-2">Last Mentioned</TableHead>
            <TableHead className="w-[50px] py-2 px-2"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {citations.map((citation: any) => (
            <TableRow key={citation.id} className="hover:bg-muted/20 transition-colors">
              <TableCell className="py-2 px-2">{getStatusIcon(citation.display_status)}</TableCell>
              <TableCell className="py-2 px-2">
                <div className="flex flex-col gap-0.5">
                  <div className="flex items-center gap-1.5">
                    <img
                      src={`https://www.google.com/s2/favicons?domain=${citation.source_domain}&sz=32`}
                      alt=""
                      className="w-4 h-4 flex-shrink-0"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                    <span className="text-sm" title={citation.url}>
                      {truncateUrl(citation.url, 50)}
                    </span>
                  </div>
                  {citation.context_snippet && (
                    <p className="text-xs text-muted-foreground line-clamp-1 max-w-[400px]" title={citation.context_snippet}>
                      {citation.context_snippet}
                    </p>
                  )}
                </div>
              </TableCell>
              <TableCell className="py-2 px-2">
                <span className="text-sm text-muted-foreground">{citation.source_domain}</span>
              </TableCell>
              <TableCell className="text-center py-2 px-2">
                <Badge variant="secondary">
                  {citation.mention_count || 1}
                </Badge>
              </TableCell>
              <TableCell className="py-2 px-2">
                {citation.platform && (
                  <Badge variant="outline" className="capitalize font-medium">
                    {citation.platform}
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground py-2 px-2">
                {formatDate(citation.last_mentioned_at || citation.created_at)}
              </TableCell>
              <TableCell className="py-2 px-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => window.open(citation.url, "_blank")}
                  className="h-8 w-8 hover:bg-primary/10"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default Citations;
