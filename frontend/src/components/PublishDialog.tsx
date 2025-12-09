import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { CalendarIcon, Clock, Send, CheckCircle2 } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

interface CMSProvider {
  id: number;
  name: string;
  provider_type: string;
  is_default: boolean;
}

interface PublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  contentId: number;
  contentTitle: string;
}

const PublishDialog = ({ open, onOpenChange, contentId, contentTitle }: PublishDialogProps) => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();
  const [publishing, setPublishing] = useState(false);
  const [cmsProviders, setCmsProviders] = useState<CMSProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<number | null>(null);
  const [publishNow, setPublishNow] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [selectedTime, setSelectedTime] = useState("00:00");
  const [timezone, setTimezone] = useState("UTC");

  useEffect(() => {
    if (open && selectedDomain) {
      loadCMSProviders();
    }
  }, [open, selectedDomain]);

  useEffect(() => {
    if (cmsProviders.length > 0 && !selectedProvider) {
      const defaultProvider = cmsProviders.find(p => p.is_default) || cmsProviders[0];
      setSelectedProvider(defaultProvider.id);
    }
  }, [cmsProviders]);

  const loadCMSProviders = async () => {
    if (!selectedDomain) return;

    try {
      const response = await apiClient.getCMSProviders({ domain_id: selectedDomain.id });
      if (response.status === "success") {
        const providers = response.results || [];
        setCmsProviders(providers);
        if (providers.length === 0) {
          toast({
            title: "No CMS Providers",
            description: "Please configure a CMS provider in Automation Settings first",
            variant: "destructive",
          });
        }
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to load CMS providers",
        variant: "destructive",
      });
    }
  };

  const handlePublish = async () => {
    if (!selectedProvider) {
      toast({
        title: "Error",
        description: "Please select a CMS provider",
        variant: "destructive",
      });
      return;
    }

    try {
      setPublishing(true);

      let scheduledAt: string | undefined;
      if (!publishNow && selectedDate) {
        const [hours, minutes] = selectedTime.split(":");
        const scheduledDate = new Date(selectedDate);
        scheduledDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
        scheduledAt = scheduledDate.toISOString();
      }

      const response = await apiClient.publishContent({
        content_id: contentId,
        cms_provider_id: selectedProvider,
        publish_now: publishNow,
        scheduled_at: scheduledAt,
      });

      if (response.status === "success") {
        toast({
          title: publishNow ? "Published Successfully" : "Scheduled Successfully",
          description: publishNow
            ? "Your content has been published"
            : `Content scheduled for ${format(selectedDate || new Date(), "PPP 'at' p")}`,
        });
        onOpenChange(false);
        // Reset form
        setPublishNow(true);
        setSelectedDate(new Date());
        setSelectedTime("00:00");
      }
    } catch (error: any) {
      toast({
        title: "Publish Failed",
        description: error.message || "Failed to publish content",
        variant: "destructive",
      });
    } finally {
      setPublishing(false);
    }
  };

  const getCurrentTimezone = () => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "UTC";
    }
  };

  useEffect(() => {
    setTimezone(getCurrentTimezone());
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">{contentTitle}</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* CMS Provider Selection */}
          <div>
            <Label className="text-base mb-2 block">Select CMS Provider</Label>
            <Select
              value={selectedProvider?.toString() || ""}
              onValueChange={(value) => setSelectedProvider(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a CMS provider" />
              </SelectTrigger>
              <SelectContent>
                {cmsProviders.map((provider) => (
                  <SelectItem key={provider.id} value={provider.id.toString()}>
                    {provider.name} {provider.is_default && "(Default)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {cmsProviders.length === 0 && (
              <p className="text-sm text-muted-foreground mt-2">
                No CMS providers configured.{" "}
                <a href="/automation" className="text-primary underline">
                  Configure one here
                </a>
              </p>
            )}
          </div>

          {/* Schedule Section */}
          {!publishNow && (
            <div className="space-y-4 border-t pt-4">
              <div>
                <Label className="text-base mb-2 block">Schedule</Label>
                <p className="text-sm text-muted-foreground mb-4">
                  Select a date and time to make your content public.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Date Picker */}
                <div>
                  <Label className="text-sm mb-2 block">Date</Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className={cn(
                          "w-full justify-start text-left font-normal",
                          !selectedDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {selectedDate ? (
                          format(selectedDate, "PPP")
                        ) : (
                          <span>Pick a date</span>
                        )}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={selectedDate}
                        onSelect={setSelectedDate}
                        disabled={(date) => date < new Date()}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {/* Time Picker */}
                <div>
                  <Label className="text-sm mb-2 block">Time</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="time"
                      value={selectedTime}
                      onChange={(e) => setSelectedTime(e.target.value)}
                      className="flex-1"
                    />
                    <div className="text-sm text-muted-foreground">
                      {timezone}
                    </div>
                  </div>
                </div>
              </div>

              {selectedDate && (
                <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-md">
                  <p>
                    Content will be private before publishing on{" "}
                    <strong>
                      {format(selectedDate, "PPP")} at {selectedTime}
                    </strong>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Publish Now Checkbox */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="publish-now"
              checked={publishNow}
              onCheckedChange={(checked) => {
                setPublishNow(checked as boolean);
                if (checked) {
                  setSelectedDate(undefined);
                } else {
                  setSelectedDate(new Date());
                }
              }}
            />
            <Label
              htmlFor="publish-now"
              className="text-base font-medium cursor-pointer"
            >
              Publish Now
            </Label>
          </div>

          {/* Status Info */}
          <div className="flex items-start gap-3 p-4 bg-muted/30 rounded-lg">
            <CheckCircle2 className="h-5 w-5 text-success mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium">Ready to publish</p>
              <p className="text-xs text-muted-foreground mt-1">
                {publishNow
                  ? "Your content will be published immediately"
                  : selectedDate
                  ? `Scheduled for ${format(selectedDate, "PPP 'at' p")}`
                  : "Please select a date and time"}
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handlePublish}
            disabled={publishing || !selectedProvider || (!publishNow && !selectedDate)}
            className="gradient-primary"
          >
            {publishing ? (
              <>
                <Clock className="h-4 w-4 mr-2 animate-spin" />
                {publishNow ? "Publishing..." : "Scheduling..."}
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                {publishNow ? "Publish Now" : "Schedule"}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default PublishDialog;

