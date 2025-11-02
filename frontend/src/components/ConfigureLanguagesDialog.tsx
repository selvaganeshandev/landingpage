import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Languages, Settings, Bell, TrendingUp, Trash2 } from "lucide-react";

interface ConfigureLanguagesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const activeLanguages = [
  { code: "en", name: "English", enabled: true, priority: "high" },
  { code: "es", name: "Spanish", enabled: true, priority: "high" },
  { code: "fr", name: "French", enabled: true, priority: "medium" },
  { code: "de", name: "German", enabled: true, priority: "medium" },
  { code: "pt", name: "Portuguese", enabled: true, priority: "medium" },
  { code: "it", name: "Italian", enabled: true, priority: "low" },
];

export const ConfigureLanguagesDialog = ({ open, onOpenChange }: ConfigureLanguagesDialogProps) => {
  const { toast } = useToast();
  
  // General Settings
  const [autoDetect, setAutoDetect] = useState(true);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [updateFrequency, setUpdateFrequency] = useState("daily");

  // Language States
  const [languages, setLanguages] = useState(
    activeLanguages.map(lang => ({
      ...lang,
      alertsEnabled: true,
    }))
  );

  const toggleLanguage = (code: string) => {
    setLanguages(prev =>
      prev.map(lang =>
        lang.code === code ? { ...lang, enabled: !lang.enabled } : lang
      )
    );
  };

  const updatePriority = (code: string, priority: string) => {
    setLanguages(prev =>
      prev.map(lang =>
        lang.code === code ? { ...lang, priority } : lang
      )
    );
  };

  const toggleLanguageAlerts = (code: string) => {
    setLanguages(prev =>
      prev.map(lang =>
        lang.code === code ? { ...lang, alertsEnabled: !lang.alertsEnabled } : lang
      )
    );
  };

  const removeLanguage = (code: string) => {
    setLanguages(prev => prev.filter(lang => lang.code !== code));
    toast({
      title: "Language Removed",
      description: `Language has been removed from monitoring.`,
    });
  };

  const handleSave = () => {
    const enabledCount = languages.filter(l => l.enabled).length;
    toast({
      title: "Settings Saved",
      description: `Configuration updated for ${enabledCount} language(s).`,
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Settings className="h-6 w-6 text-primary" />
            Language Configuration
          </DialogTitle>
          <DialogDescription>
            Manage your multilingual monitoring settings and preferences
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="languages" className="py-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="languages">Languages</TabsTrigger>
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
          </TabsList>

          {/* Languages Tab */}
          <TabsContent value="languages" className="space-y-4 mt-6">
            <div className="space-y-3">
              {languages.map((language) => (
                <Card key={language.code} className="p-4">
                  <div className="flex items-center gap-4">
                    <Switch
                      checked={language.enabled}
                      onCheckedChange={() => toggleLanguage(language.code)}
                    />
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h4 className="font-semibold">{language.name}</h4>
                        <Badge variant="outline" className="text-xs">
                          {language.code.toUpperCase()}
                        </Badge>
                        {!language.enabled && (
                          <Badge variant="secondary" className="text-xs">
                            Disabled
                          </Badge>
                        )}
                      </div>
                      
                      {language.enabled && (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">Monitoring Priority</Label>
                            <Select
                              value={language.priority}
                              onValueChange={(value) => updatePriority(language.code, value)}
                            >
                              <SelectTrigger className="h-8 text-sm">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="high">High Priority</SelectItem>
                                <SelectItem value="medium">Medium Priority</SelectItem>
                                <SelectItem value="low">Low Priority</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          
                          <div className="space-y-2">
                            <Label className="text-xs text-muted-foreground">Language Alerts</Label>
                            <div className="flex items-center gap-2 h-8">
                              <Switch
                                checked={language.alertsEnabled}
                                onCheckedChange={() => toggleLanguageAlerts(language.code)}
                                className="scale-75"
                              />
                              <span className="text-sm">
                                {language.alertsEnabled ? "Enabled" : "Disabled"}
                              </span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeLanguage(language.code)}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>

            {languages.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Languages className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No languages configured. Add languages to start monitoring.</p>
              </div>
            )}
          </TabsContent>

          {/* General Settings Tab */}
          <TabsContent value="general" className="space-y-6 mt-6">
            <Card className="p-6 border border-border">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label className="text-base">Auto-Detect Languages</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically detect and suggest new languages from mentions
                    </p>
                  </div>
                  <Switch
                    checked={autoDetect}
                    onCheckedChange={setAutoDetect}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Update Frequency</Label>
                  <Select value={updateFrequency} onValueChange={setUpdateFrequency}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="realtime">Real-time</SelectItem>
                      <SelectItem value="hourly">Hourly</SelectItem>
                      <SelectItem value="daily">Daily</SelectItem>
                      <SelectItem value="weekly">Weekly</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    How often to check for new mentions across languages
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-muted/30 border border-border">
                  <div className="flex items-start gap-3">
                    <TrendingUp className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <p className="text-sm font-medium mb-1">Growth Tracking</p>
                      <p className="text-xs text-muted-foreground">
                        Monitor language-specific growth trends and receive notifications 
                        when a language shows significant increase in mentions.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          {/* Alerts Tab */}
          <TabsContent value="alerts" className="space-y-6 mt-6">
            <Card className="p-6 border border-border">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Bell className="h-4 w-4 text-primary" />
                      <Label className="text-base">Language-Specific Alerts</Label>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Receive notifications for language-specific changes
                    </p>
                  </div>
                  <Switch
                    checked={alertsEnabled}
                    onCheckedChange={setAlertsEnabled}
                  />
                </div>

                {alertsEnabled && (
                  <div className="space-y-4 pt-4 border-t border-border">
                    <div className="space-y-3">
                      <Label className="text-sm">Alert Conditions</Label>
                      
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <span className="text-sm">New language detected</span>
                          <Switch defaultChecked />
                        </div>
                        
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <span className="text-sm">Language visibility drops {'>'} 10%</span>
                          <Switch defaultChecked />
                        </div>
                        
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <span className="text-sm">Sentiment changes {'>'} 15%</span>
                          <Switch defaultChecked />
                        </div>
                        
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border">
                          <span className="text-sm">Growth spike in any language</span>
                          <Switch defaultChecked />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex gap-3 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
            Cancel
          </Button>
          <Button onClick={handleSave} className="gradient-primary flex-1">
            Save Configuration
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
