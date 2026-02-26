import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Search,
  Download,
  RefreshCw,
  Trash2,
  Columns,
  List,
  LayoutGrid,
  Monitor,
  Smartphone,
  Star,
  TrendingUp,
  TrendingDown,
  Info,
  Tag,
  ExternalLink,
  ChevronRight,
  BarChart3,
  ArrowRight,
} from "lucide-react";

// Mock data for demonstration
const mockKeywords = [
  {
    id: 1,
    keyword: "best spine hospital in mumbai",
    url: "/speciality/centre-orthopedic-care/spine-su...",
    rank: 4,
    volume: null,
    best: 3,
    clicks: 0,
    impressions: 0,
    change1d: { value: 1, direction: "down" },
    change7d: { value: 1, direction: "down" },
    change15d: null,
    serp: null,
    tags: [],
    date: "Oct 02 2025",
    timeAgo: "13 hours ago",
    country: "IN",
  },
  {
    id: 2,
    keyword: "medical oncology",
    url: "hindujahospital.com",
    rank: null,
    rankDisplay: ">30",
    volume: 5400,
    best: 23,
    clicks: 0,
    impressions: 0,
    change1d: null,
    change7d: null,
    change15d: null,
    serp: null,
    tags: [],
    date: "Oct 03 2025",
    timeAgo: "13 hours ago",
    country: "IN",
  },
  {
    id: 3,
    keyword: "best liver transplant hospital in mumbai",
    url: "hindujahospital.com",
    rank: null,
    rankDisplay: ">30",
    volume: 110,
    volumeChange: "down",
    best: 18,
    clicks: 0,
    impressions: 0,
    change1d: null,
    change7d: null,
    change15d: null,
    serp: null,
    tags: [],
    date: "Oct 03 2025",
    timeAgo: "13 hours ago",
    country: "IN",
  },
];

const comparisonData = [
  { status: "Top 1", today: 0, yesterday: 0, best: 0 },
  { status: "Top 3", today: 0, yesterday: 1, best: 1 },
  { status: "Top 10", today: 1, yesterday: 1, best: 1 },
  { status: "Top 50", today: 1, yesterday: 1, best: 3 },
  { status: "Top 100", today: 1, yesterday: 1, best: 3 },
  { status: "Not Ranked", today: 2, yesterday: 2, best: 0 },
];

const SeoRankings = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [showOverview, setShowOverview] = useState(true);
  const [selectedKeywords, setSelectedKeywords] = useState<number[]>([]);

  const toggleKeywordSelection = (id: number) => {
    setSelectedKeywords((prev) =>
      prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
    );
  };

  const toggleAllKeywords = () => {
    if (selectedKeywords.length === mockKeywords.length) {
      setSelectedKeywords([]);
    } else {
      setSelectedKeywords(mockKeywords.map((k) => k.id));
    }
  };

  const formatVolume = (volume: number | null) => {
    if (volume === null) return "NA";
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Keyword Rankings</h1>
          <p className="text-muted-foreground mt-2">
            Track your organic search rankings and keyword performance
          </p>
        </div>
        <Button className="gradient-primary shadow-md shadow-primary/20">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh Data
        </Button>
      </div>

      {/* Overview Section */}
      <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <CardHeader className="flex flex-row items-center justify-between py-3 px-4">
          <CardTitle className="text-lg font-semibold">Overview</CardTitle>
          <div className="flex items-center gap-2">
            <Label htmlFor="hide-overview" className="text-sm text-muted-foreground">Hide</Label>
            <Switch id="hide-overview" checked={showOverview} onCheckedChange={setShowOverview} />
          </div>
        </CardHeader>
        {showOverview && (
          <CardContent className="pt-0 px-4 pb-4">
            {/* Overview Cards - Competitor Style */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

              {/* Comparison Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Comparison</h3>
                      <p className="text-sm text-muted-foreground">Ranking distribution</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <BarChart3 className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 3</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 10</p>
                      <p className="text-lg font-bold font-inter">1</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Top 50</p>
                      <p className="text-lg font-bold font-inter">1</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Not Ranked</p>
                      <p className="text-lg font-bold font-inter">2</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Best</span>
                      <span className="font-semibold">3 keywords</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Device Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Device</h3>
                      <p className="text-sm text-muted-foreground">Keywords by device</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <Monitor className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Desktop</p>
                      <p className="text-lg font-bold font-inter">3</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Mobile</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Tablet</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Total</p>
                      <p className="text-lg font-bold font-inter">3</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Tracking</span>
                      <span className="font-semibold">3 keywords</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Today's Performance Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Performance</h3>
                      <p className="text-sm text-muted-foreground">Today's changes</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-primary">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                      <p className="text-xs text-green-600 mb-1 uppercase tracking-wider">Improved</p>
                      <p className="text-lg font-bold font-inter text-green-600">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                      <p className="text-xs text-red-600 mb-1 uppercase tracking-wider">Declined</p>
                      <p className="text-lg font-bold font-inter text-red-600">1</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">No Change</p>
                      <p className="text-lg font-bold font-inter">2</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">New</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Trend</span>
                      <div className="flex items-center gap-1">
                        <TrendingDown className="h-4 w-4 text-destructive" />
                        <span className="font-semibold text-destructive">-1</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Rankmax Score Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Rankmax Score</h3>
                      <p className="text-sm text-muted-foreground">Overall performance</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-base font-inter bg-red-500">
                      0
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Current</p>
                      <p className="text-lg font-bold font-inter">0</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Best</p>
                      <p className="text-lg font-bold font-inter">20</p>
                    </div>
                    <div className="p-2 rounded-lg bg-muted/30 border border-border">
                      <p className="text-xs text-muted-foreground mb-1 uppercase tracking-wider">Average</p>
                      <p className="text-lg font-bold font-inter">15</p>
                    </div>
                    <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                      <p className="text-xs text-red-600 mb-1 uppercase tracking-wider">Status</p>
                      <p className="text-lg font-bold font-inter text-red-600">Low</p>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Trend</span>
                      <div className="flex items-center gap-1">
                        <TrendingDown className="h-4 w-4 text-destructive" />
                        <span className="font-semibold text-destructive">Dropping</span>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Second Row - SERP Features & Google Ads */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {/* SERP Features Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">SERP Features</h3>
                      <p className="text-sm text-muted-foreground">Your search result ratings</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-yellow-500">
                      <Star className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star
                            key={i}
                            className={`h-4 w-4 ${i < 2 ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground/30"}`}
                          />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(0-2 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">3</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star
                            key={i}
                            className={`h-4 w-4 ${i < 4 ? "text-yellow-500 fill-yellow-500" : "text-muted-foreground/30"}`}
                          />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(2-4 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">0</span>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((_, i) => (
                          <Star key={i} className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                        ))}
                        <span className="text-xs text-muted-foreground ml-2">(4-5 stars)</span>
                      </div>
                      <span className="text-lg font-bold font-inter">0</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Total Features</span>
                      <span className="font-semibold">3</span>
                    </div>
                  </div>
                </div>
              </Card>

              {/* Google Search Ads Card */}
              <Card className="p-4 transition-all duration-300 backdrop-blur-sm bg-card/80 border border-border hover:border-primary">
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold font-inter">Google Search Ads</h3>
                      <p className="text-sm text-muted-foreground">Ad placement comparison</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg shadow-glow flex items-center justify-center font-bold text-white text-sm font-inter bg-blue-500">
                      <LayoutGrid className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Above & below the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Above the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border">
                      <span className="text-sm font-medium">Below the fold</span>
                      <div className="flex items-center gap-4">
                        <span className="text-xs text-muted-foreground">You: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                        <span className="text-xs text-muted-foreground">Others: <span className="text-lg font-bold font-inter text-foreground">0</span></span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Your Ads</span>
                      <span className="font-semibold">0 placements</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Keywords Section */}
      <div className="space-y-3">
        <h2 className="text-xl font-semibold">Total keywords ({mockKeywords.length})</h2>

        {/* Toolbar */}
        <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80 p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search keywords..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-[220px] bg-background"
                />
              </div>
              <Button variant="outline" className="gap-2">
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon">
                <Tag className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button variant="outline" className="gap-2">
                <Columns className="h-4 w-4" />
                Column
              </Button>
              <div className="flex items-center border border-border rounded-lg overflow-hidden">
                <Button
                  variant={viewMode === "list" ? "default" : "ghost"}
                  size="sm"
                  className={`rounded-none gap-1 ${viewMode === "list" ? "gradient-primary" : ""}`}
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-4 w-4" />
                  List
                </Button>
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="sm"
                  className={`rounded-none gap-1 ${viewMode === "grid" ? "gradient-primary" : ""}`}
                  onClick={() => setViewMode("grid")}
                >
                  <LayoutGrid className="h-4 w-4" />
                  Grid
                </Button>
              </div>
            </div>
          </div>
        </Card>

        {/* Keywords Table */}
        <Card className="shadow-elegant border border-border backdrop-blur-sm bg-card/80">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="w-10 py-2">
                    <Checkbox
                      checked={selectedKeywords.length === mockKeywords.length}
                      onCheckedChange={toggleAllKeywords}
                    />
                  </TableHead>
                  <TableHead className="w-20 text-xs font-semibold py-2">ACTIONS</TableHead>
                  <TableHead className="text-xs font-semibold py-2">KEYWORD</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-14">RANK</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-16">VOLUME</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">BEST</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">CLKS</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">IMPS</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">1D</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">7D</TableHead>
                  <TableHead className="text-center text-xs font-semibold py-2 w-12">15D</TableHead>
                  <TableHead className="text-xs font-semibold py-2 w-20">DATE</TableHead>
                  <TableHead className="w-8 py-2"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockKeywords.map((keyword) => (
                  <TableRow key={keyword.id} className="hover:bg-muted/30">
                    <TableCell className="py-1.5">
                      <Checkbox
                        checked={selectedKeywords.includes(keyword.id)}
                        onCheckedChange={() => toggleKeywordSelection(keyword.id)}
                      />
                    </TableCell>
                    <TableCell className="py-1.5">
                      <div className="flex items-center gap-0">
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <span className="text-red-500 font-bold text-xs">G</span>
                        </Button>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          <Star className="h-3.5 w-3.5 text-muted-foreground" />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell className="py-1.5">
                      <div className="flex items-center gap-2">
                        <img
                          src={`https://flagcdn.com/16x12/${keyword.country.toLowerCase()}.png`}
                          alt={keyword.country}
                          className="w-4 h-3 object-cover rounded-sm shadow-sm flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="font-medium text-sm truncate">{keyword.keyword}</p>
                          <p className="text-xs text-muted-foreground flex items-center gap-1 truncate">
                            {keyword.url}
                            <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-center py-1.5">
                      {keyword.rankDisplay ? (
                        <span className="text-muted-foreground text-sm">{keyword.rankDisplay}</span>
                      ) : (
                        <span className="font-semibold text-sm">{keyword.rank}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center py-1.5">
                      <div className="flex items-center justify-center gap-0.5">
                        <span className="text-sm">{formatVolume(keyword.volume)}</span>
                        {keyword.volumeChange === "down" && (
                          <TrendingDown className="h-3 w-3 text-red-500" />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center font-semibold py-1.5 text-sm">{keyword.best}</TableCell>
                    <TableCell className="text-center py-1.5 text-sm">{keyword.clicks}</TableCell>
                    <TableCell className="text-center py-1.5 text-sm">{keyword.impressions}</TableCell>
                    <TableCell className="text-center py-1.5">
                      {keyword.change1d ? (
                        <div className="flex items-center justify-center gap-0.5">
                          <span className={`text-sm ${keyword.change1d.direction === "down" ? "text-red-500 font-medium" : "text-green-500 font-medium"}`}>
                            {keyword.change1d.value}
                          </span>
                          {keyword.change1d.direction === "down" ? (
                            <TrendingDown className="h-3 w-3 text-red-500" />
                          ) : (
                            <TrendingUp className="h-3 w-3 text-green-500" />
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center py-1.5">
                      {keyword.change7d ? (
                        <div className="flex items-center justify-center gap-0.5">
                          <span className={`text-sm ${keyword.change7d.direction === "down" ? "text-red-500 font-medium" : "text-green-500 font-medium"}`}>
                            {keyword.change7d.value}
                          </span>
                          {keyword.change7d.direction === "down" ? (
                            <TrendingDown className="h-3 w-3 text-red-500" />
                          ) : (
                            <TrendingUp className="h-3 w-3 text-green-500" />
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-sm">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center py-1.5 text-sm">
                      {keyword.change15d !== null ? keyword.change15d : <span className="text-muted-foreground">-</span>}
                    </TableCell>
                    <TableCell className="py-1.5">
                      <p className="text-xs text-muted-foreground whitespace-nowrap">{keyword.date}</p>
                    </TableCell>
                    <TableCell className="py-1.5">
                      <Button variant="ghost" size="icon" className="h-6 w-6">
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SeoRankings;
