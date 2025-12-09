import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Settings, FileText, ArrowLeft, Globe } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import CMSProviderManager from "@/components/CMSProviderManager";

const AutomationSettings = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSave = () => {
    toast({
      title: "Settings Saved",
      description: "Your automation preferences have been updated successfully.",
    });
  };


  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigate(-1)}
            className="border-border"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight font-inter">CMS Settings</h1>
            <p className="text-muted-foreground mt-1">
              Configure CMS providers and publishing preferences
            </p>
          </div>
        </div>
      </div>

      {/* CMS Provider Management */}
      <Card className="p-6 border border-border">
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Globe className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-1">CMS Provider Management</h3>
              <p className="text-sm text-muted-foreground">
                Configure and manage CMS providers for publishing content
              </p>
            </div>
          </div>

          <Separator />

          <CMSProviderManager />
        </div>
      </Card>

    </div>
  );
};

export default AutomationSettings;
