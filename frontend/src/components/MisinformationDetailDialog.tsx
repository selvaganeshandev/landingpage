import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
  AlertTriangle,
  Eye,
  LinkIcon,
  FileText
} from "lucide-react";

interface MisinformationAlert {
  id: number;
  alert_type: 'misinformation' | 'broken_link' | 'outdated';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'reviewed' | 'resolved' | 'dismissed';
  llm_claim: string;
  source_content?: string;
  explanation?: string;
  created_at: string;
  reviewed_at?: string;
  citation_url?: {
    url: string;
    crawl_status: string;
  };
  prompt?: {
    id: number;
    prompt_text: string;
  };
}

interface MisinformationDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  misinformationCase: MisinformationAlert | null;
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case "critical":
      return "bg-destructive text-destructive-foreground";
    case "high":
      return "bg-destructive/80 text-destructive-foreground";
    case "medium":
      return "bg-warning text-warning-foreground";
    case "low":
      return "bg-success text-success-foreground";
    default:
      return "bg-muted";
  }
};

const alertTypeLabels: Record<string, string> = {
  misinformation: 'Misinformation',
  broken_link: 'Broken Link',
  outdated: 'Outdated Information'
};

const getAlertTypeIcon = (alertType: string) => {
  switch (alertType) {
    case 'broken_link':
      return LinkIcon;
    case 'outdated':
      return Clock;
    default:
      return AlertTriangle;
  }
};

const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return 'Just now';
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

export function MisinformationDetailDialog({
  open,
  onOpenChange,
  misinformationCase,
}: MisinformationDetailDialogProps) {
  if (!misinformationCase) return null;

  const AlertTypeIcon = getAlertTypeIcon(misinformationCase.alert_type);
  const alertTypeLabel = alertTypeLabels[misinformationCase.alert_type] || misinformationCase.alert_type;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-destructive/10 flex items-center justify-center">
              <AlertTypeIcon className="h-5 w-5 text-destructive" />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-xl mb-2">
                {alertTypeLabel}
              </DialogTitle>
              <DialogDescription>
                Case #{misinformationCase.id} • Detected {formatTimeAgo(misinformationCase.created_at)}
              </DialogDescription>
            </div>
            <Badge className={getSeverityColor(misinformationCase.severity)}>
              {misinformationCase.severity} severity
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Explanation */}
          {misinformationCase.explanation && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Issue Description</h3>
              <p className="text-sm text-muted-foreground">
                {misinformationCase.explanation}
              </p>
            </div>
          )}

          <Separator />

          {/* Key Information */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Alert Type</p>
                <Badge variant="secondary">{alertTypeLabel}</Badge>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Status</p>
                <Badge variant="outline">{misinformationCase.status}</Badge>
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Detected At</p>
                <p className="text-sm font-medium">{formatDate(misinformationCase.created_at)}</p>
              </div>
              {misinformationCase.reviewed_at && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Reviewed At</p>
                  <p className="text-sm font-medium">{formatDate(misinformationCase.reviewed_at)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Citation URL */}
          {misinformationCase.citation_url && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-semibold mb-2">Citation Source</h3>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <ExternalLink className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <a
                      href={misinformationCase.citation_url.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline break-all"
                    >
                      {misinformationCase.citation_url.url}
                    </a>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 ml-6">
                    Crawl status: {misinformationCase.citation_url.crawl_status}
                  </p>
                </div>
              </div>
            </>
          )}

          {/* Prompt Context */}
          {misinformationCase.prompt && (
            <>
              <Separator />
              <div>
                <h3 className="text-sm font-semibold mb-2">Prompt Context</h3>
                <div className="p-3 bg-muted rounded-lg">
                  <div className="flex items-start gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                    <p className="text-sm">{misinformationCase.prompt.prompt_text}</p>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* LLM Claim vs Source Content Comparison */}
          {(misinformationCase.llm_claim || misinformationCase.source_content) && (
            <>
              <Separator />
              <div className="space-y-4">
                <h3 className="text-sm font-semibold">Information Comparison</h3>

                {misinformationCase.llm_claim && (
                  <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                    <div className="flex items-start gap-2 mb-2">
                      <XCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                      <p className="text-sm font-medium text-destructive">What the LLM Claimed</p>
                    </div>
                    <p className="text-sm pl-6">{misinformationCase.llm_claim}</p>
                  </div>
                )}

                {misinformationCase.source_content && (
                  <div className="p-4 bg-success/10 border border-success/20 rounded-lg">
                    <div className="flex items-start gap-2 mb-2">
                      <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                      <p className="text-sm font-medium text-success">What the Source Actually Says</p>
                    </div>
                    <p className="text-sm pl-6">{misinformationCase.source_content}</p>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Timeline */}
          <Separator />
          <div>
            <h3 className="text-sm font-semibold mb-3">Detection Timeline</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Eye className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Issue Detected</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(misinformationCase.created_at)}
                  </p>
                </div>
              </div>
              {misinformationCase.reviewed_at && (
                <div className="flex items-start gap-3">
                  <div className="h-8 w-8 rounded-full bg-warning/10 flex items-center justify-center">
                    <AlertTriangle className="h-4 w-4 text-warning" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">Reviewed</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(misinformationCase.reviewed_at)}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Current Status: {misinformationCase.status}</p>
                  <p className="text-xs text-muted-foreground">
                    {misinformationCase.status === 'new' && 'Awaiting review'}
                    {misinformationCase.status === 'reviewed' && 'Under investigation'}
                    {misinformationCase.status === 'resolved' && 'Issue has been resolved'}
                    {misinformationCase.status === 'dismissed' && 'Marked as not an issue'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <div className="flex gap-2">
            {misinformationCase.citation_url && (
              <Button
                variant="outline"
                onClick={() => window.open(misinformationCase.citation_url?.url, '_blank')}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                View Source
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
