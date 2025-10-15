import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { 
  FileText,
  Plus,
  Download,
  Calendar,
  Eye,
  Share2,
  Clock,
  Settings
} from "lucide-react";

const reports = [
  {
    id: 1,
    name: "Monthly Performance Report",
    description: "Comprehensive overview of visibility, mentions, and sentiment",
    schedule: "Monthly - 1st of month",
    lastGenerated: "Nov 1, 2024",
    format: ["PDF", "Excel"],
    recipients: ["team@vegfitpro.com", "marketing@vegfitpro.com"],
    status: "active"
  },
  {
    id: 2,
    name: "Weekly Competitor Analysis",
    description: "Competitive benchmarking and market position tracking",
    schedule: "Weekly - Monday 9 AM",
    lastGenerated: "Nov 11, 2024",
    format: ["PDF"],
    recipients: ["strategy@vegfitpro.com"],
    status: "active"
  },
  {
    id: 3,
    name: "Real-Time Alert Digest",
    description: "Daily summary of alerts and significant changes",
    schedule: "Daily - 8 AM",
    lastGenerated: "Today",
    format: ["Email"],
    recipients: ["alerts@vegfitpro.com"],
    status: "active"
  },
  {
    id: 4,
    name: "Executive Summary",
    description: "High-level KPIs and strategic insights for leadership",
    schedule: "Quarterly",
    lastGenerated: "Oct 1, 2024",
    format: ["PDF", "PowerPoint"],
    recipients: ["exec@vegfitpro.com"],
    status: "active"
  },
];

const recentReports = [
  {
    id: 1,
    name: "Performance Report - November 2024",
    generatedAt: "2 hours ago",
    size: "2.4 MB",
    pages: 24,
    format: "PDF"
  },
  {
    id: 2,
    name: "Competitor Analysis - Week 45",
    generatedAt: "1 day ago",
    size: "1.8 MB",
    pages: 18,
    format: "PDF"
  },
  {
    id: 3,
    name: "Alert Digest - Nov 11",
    generatedAt: "1 day ago",
    size: "0.5 MB",
    pages: 6,
    format: "PDF"
  },
  {
    id: 4,
    name: "Sentiment Deep Dive - October",
    generatedAt: "5 days ago",
    size: "3.1 MB",
    pages: 32,
    format: "PDF"
  },
];

const templates = [
  {
    id: 1,
    name: "Executive Dashboard",
    description: "High-level KPIs with visual charts",
    sections: 6,
    preview: true
  },
  {
    id: 2,
    name: "Detailed Analytics",
    description: "In-depth analysis with all metrics",
    sections: 12,
    preview: true
  },
  {
    id: 3,
    name: "Competitor Focus",
    description: "Competitive intelligence and benchmarking",
    sections: 8,
    preview: true
  },
  {
    id: 4,
    name: "Content Strategy",
    description: "Gap analysis and recommendations",
    sections: 10,
    preview: true
  },
];

const Reports = () => {
  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Custom Reports</h1>
          <p className="text-muted-foreground mt-2">
            Generate and automate branded reports
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            Manage Templates
          </Button>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Create Report
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Button variant="outline" className="h-24 flex flex-col gap-2">
          <FileText className="h-6 w-6" />
          <span className="font-medium">Generate Now</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2">
          <Calendar className="h-6 w-6" />
          <span className="font-medium">Schedule Report</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2">
          <Download className="h-6 w-6" />
          <span className="font-medium">Download All</span>
        </Button>
        <Button variant="outline" className="h-24 flex flex-col gap-2">
          <Share2 className="h-6 w-6" />
          <span className="font-medium">Share Report</span>
        </Button>
      </div>

      {/* Scheduled Reports */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Scheduled Reports</h3>
        <div className="space-y-4">
          {reports.map((report) => (
            <div key={report.id} className="p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="font-semibold">{report.name}</h4>
                    <Badge variant={report.status === "active" ? "default" : "secondary"}>
                      {report.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">{report.description}</p>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">{report.schedule}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">Last: {report.lastGenerated}</span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline">
                    <Eye className="h-3 w-3 mr-1" />
                    Preview
                  </Button>
                  <Button size="sm" variant="outline">Edit</Button>
                  <Button size="sm">Run Now</Button>
                </div>
              </div>
              <div className="flex items-center gap-4 pt-3 border-t border-border">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Formats:</span>
                  {report.format.map((fmt) => (
                    <Badge key={fmt} variant="outline" className="text-xs">
                      {fmt}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Recipients: {report.recipients.length}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent Reports */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Recent Reports</h3>
          <Button variant="outline" size="sm">View All</Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {recentReports.map((report) => (
            <div key={report.id} className="p-4 rounded-lg border border-border hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <Badge variant="secondary" className="text-xs">{report.format}</Badge>
              </div>
              <h4 className="font-medium text-sm mb-2 line-clamp-2">{report.name}</h4>
              <div className="space-y-1 text-xs text-muted-foreground mb-3">
                <p>{report.generatedAt}</p>
                <p>{report.pages} pages • {report.size}</p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" className="flex-1">
                  <Eye className="h-3 w-3 mr-1" />
                  View
                </Button>
                <Button size="sm" variant="outline" className="flex-1">
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Templates */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-6">Report Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {templates.map((template) => (
            <div key={template.id} className="p-4 rounded-lg border border-border hover:shadow-md transition-shadow">
              <div className="aspect-[4/3] rounded-lg bg-gradient-to-br from-primary/10 to-secondary/10 mb-4 flex items-center justify-center">
                <FileText className="h-12 w-12 text-muted-foreground" />
              </div>
              <h4 className="font-semibold mb-2">{template.name}</h4>
              <p className="text-sm text-muted-foreground mb-3">{template.description}</p>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground">{template.sections} sections</span>
                {template.preview && (
                  <Button size="sm" variant="outline">
                    <Eye className="h-3 w-3 mr-1" />
                    Preview
                  </Button>
                )}
              </div>
              <Button className="w-full" size="sm">Use Template</Button>
            </div>
          ))}
        </div>
      </Card>

      {/* API Access */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">API Access</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Integrate visibility data directly into your systems with our REST API
        </p>
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-muted/50">
            <p className="text-sm font-medium mb-2">API Endpoint</p>
            <code className="text-xs bg-background px-3 py-2 rounded block">
              https://api.aivis ibilitypro.com/v1/reports
            </code>
          </div>
          <div className="flex gap-3">
            <Button variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              View Documentation
            </Button>
            <Button variant="outline">Generate API Key</Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Reports;
