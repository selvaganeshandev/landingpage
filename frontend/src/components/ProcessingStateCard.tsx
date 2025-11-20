import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Loader2, CheckCircle2, Clock } from "lucide-react";
import { Domain } from "@/stores/domainStore";

interface ProcessingStateCardProps {
  domain: Domain;
}

const getProcessingProgress = (status: string, message?: string | null): number => {
  // Calculate progress based on status and message content
  if (status === 'INIT') return 10;
  if (status === 'SCHD') return 20;

  if (status === 'PROC') {
    if (!message) return 30;

    // Parse message to determine current step
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('keyword') || lowerMessage.includes('scraping')) return 40;
    if (lowerMessage.includes('prompt') && lowerMessage.includes('generat')) return 60;
    if (lowerMessage.includes('group') || lowerMessage.includes('cluster')) return 75;
    if (lowerMessage.includes('analytic')) return 85;

    return 50; // Default for PROC
  }

  return 30;
};

const getEstimatedTime = (progress: number): string => {
  if (progress < 30) return "3-5 minutes";
  if (progress < 50) return "2-4 minutes";
  if (progress < 70) return "1-3 minutes";
  return "1-2 minutes";
};

const getProcessingSteps = (status: string, message?: string | null) => {
  const lowerMessage = message?.toLowerCase() || '';

  return [
    {
      label: "Initializing domain",
      completed: status !== 'INIT',
      current: status === 'INIT',
    },
    {
      label: "Scraping keywords",
      completed: lowerMessage.includes('prompt') || lowerMessage.includes('group') || lowerMessage.includes('analytic'),
      current: status === 'PROC' && (lowerMessage.includes('keyword') || lowerMessage.includes('scraping')),
    },
    {
      label: "Generating prompts",
      completed: lowerMessage.includes('group') || lowerMessage.includes('analytic'),
      current: status === 'PROC' && lowerMessage.includes('prompt') && lowerMessage.includes('generat'),
    },
    {
      label: "Grouping & clustering",
      completed: lowerMessage.includes('analytic'),
      current: status === 'PROC' && (lowerMessage.includes('group') || lowerMessage.includes('cluster')),
    },
    {
      label: "Processing analytics",
      completed: false,
      current: status === 'PROC' && lowerMessage.includes('analytic'),
    },
  ];
};

export const ProcessingStateCard = ({ domain }: ProcessingStateCardProps) => {
  const progress = getProcessingProgress(domain.processing_status || 'INIT', domain.track_message);
  const estimatedTime = getEstimatedTime(progress);
  const steps = getProcessingSteps(domain.processing_status || 'INIT', domain.track_message);

  console.log('📊 ProcessingStateCard rendered:', {
    domain: domain.name,
    status: domain.processing_status,
    message: domain.track_message,
    progress: progress + '%',
    estimatedTime
  });

  const getStatusMessage = () => {
    if (domain.track_message) {
      return domain.track_message;
    }

    switch (domain.processing_status) {
      case 'INIT':
        return 'Initializing brand tracking...';
      case 'SCHD':
        return 'Queued for processing...';
      case 'PROC':
        return 'Processing your brand data...';
      default:
        return 'Processing...';
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-200px)] p-4">
      <Card className="max-w-2xl w-full p-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-center gap-3">
            <div className="relative">
              <div className="w-12 h-12 rounded-full border-4 border-primary/20 flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold">Processing Your Brand</h2>
              <p className="text-sm text-muted-foreground">{domain.name}</p>
            </div>
          </div>

          {/* Current Status Message */}
          <div className="bg-muted/50 rounded-lg p-4">
            <p className="text-sm font-medium text-center">{getStatusMessage()}</p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          {/* Estimated Time */}
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Estimated time remaining: {estimatedTime}</span>
          </div>

          {/* Processing Steps */}
          <div className="space-y-3 pt-4">
            <p className="text-sm font-medium text-muted-foreground">Processing Steps:</p>
            <div className="space-y-2">
              {steps.map((step, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    {step.completed ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : step.current ? (
                      <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      step.completed
                        ? 'text-muted-foreground line-through'
                        : step.current
                        ? 'text-foreground font-medium'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Information Box */}
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium">What happens during processing?</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Scraping up to 50 relevant keywords for your brand</li>
              <li>Generating AI prompts from discovered keywords</li>
              <li>Grouping similar prompts using NLP clustering</li>
              <li>Processing analytics and visibility metrics</li>
            </ul>
          </div>

          {/* Footer Message */}
          <div className="text-center text-sm text-muted-foreground pt-4 border-t">
            <p>You can navigate away from this page.</p>
            <p>Your brand will appear in the selector once processing is complete.</p>
          </div>
        </div>
      </Card>
    </div>
  );
};
