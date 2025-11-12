import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Settings, Zap, Clock, Tag, FileText, Sparkles } from "lucide-react";
import { Separator } from "@/components/ui/separator";

const AutomationSettings = () => {
  const { toast } = useToast();
  
  const [settings, setSettings] = useState({
    automationEnabled: true,
    autoGenerateTopics: true,
    postingFrequency: "twice-daily",
    preferredTime: "morning",
    keywordClusters: [] as string[],
    cmsProvider: "ghost",
    sections: ["faq", "conclusion", "cta"],
    preferredArticleType: "any",
    contentLength: "1500-2000",
    tone: "auto",
    style: "auto",
    goal: "auto",
    targetAudience: "auto",
    contentDepth: "auto"
  });

  const handleSave = () => {
    toast({
      title: "Settings Saved",
      description: "Your automation preferences have been updated successfully.",
    });
  };

  const toggleSection = (section: string) => {
    setSettings(prev => ({
      ...prev,
      sections: prev.sections.includes(section)
        ? prev.sections.filter(s => s !== section)
        : [...prev.sections, section]
    }));
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight font-outfit">Automation Settings</h1>
          <p className="text-muted-foreground mt-1">
            Configure automation behavior for generated articles
          </p>
        </div>
        <Button onClick={handleSave} className="gradient-primary shadow-md shadow-primary/20">
          <Settings className="h-4 w-4 mr-2" />
          Save Changes
        </Button>
      </div>

      {/* Content Automation */}
      <Card className="p-6 border border-border">
        <div className="space-y-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold">Content Automation</h3>
                  <Badge variant="secondary" className="text-xs">
                    <Sparkles className="h-3 w-3 mr-1" />
                    100 credits per generation
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Enable or disable automated content generation
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={settings.automationEnabled}
                onCheckedChange={(checked) => 
                  setSettings(prev => ({ ...prev, automationEnabled: checked }))
                }
              />
              <Badge variant={settings.automationEnabled ? "default" : "secondary"}>
                {settings.automationEnabled ? "Automation Enabled" : "Disabled"}
              </Badge>
            </div>
          </div>

          <Separator />

          {/* Auto Generate Topics */}
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-medium mb-1">Auto Generate Topics</h4>
              <p className="text-sm text-muted-foreground">
                Randomly pick an idea from topic suggestions when automation runs. Enabled by default and disabled if keyword clusters are selected.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={settings.autoGenerateTopics}
                onCheckedChange={(checked) => 
                  setSettings(prev => ({ ...prev, autoGenerateTopics: checked }))
                }
                disabled={!settings.automationEnabled}
              />
              <Badge variant={settings.autoGenerateTopics ? "default" : "secondary"}>
                {settings.autoGenerateTopics ? "Enabled" : "Disabled"}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* Posting Configuration */}
      <Card className="p-6 border border-border">
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Clock className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-1">Posting Configuration</h3>
              <p className="text-sm text-muted-foreground">
                Configure when and how often content should be generated
              </p>
            </div>
          </div>

          <Separator />

          {/* Posting Frequency */}
          <div>
            <Label className="text-base">Posting Frequency</Label>
            <p className="text-sm text-muted-foreground mb-3">
              How often should automated content be generated
            </p>
            <Select 
              value={settings.postingFrequency}
              onValueChange={(value) => setSettings(prev => ({ ...prev, postingFrequency: value }))}
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="twice-daily">Twice Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="twice-weekly">Twice Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <span className="text-warning">⚠</span>
              Changes to Posting Frequency may affect current automation schedules
            </p>
          </div>

          {/* Preferred Posting Time */}
          <div>
            <Label className="text-base">Preferred Posting Time (UTC+0:00)</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Choose the best time to publish automated content
            </p>
            <Select 
              value={settings.preferredTime}
              onValueChange={(value) => setSettings(prev => ({ ...prev, preferredTime: value }))}
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="morning">Morning (5:00 AM - 12:00 PM)</SelectItem>
                <SelectItem value="afternoon">Afternoon (12:00 PM - 5:00 PM)</SelectItem>
                <SelectItem value="evening">Evening (5:00 PM - 10:00 PM)</SelectItem>
                <SelectItem value="night">Night (10:00 PM - 5:00 AM)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Content Configuration */}
      <Card className="p-6 border border-border">
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-1">Content Configuration</h3>
              <p className="text-sm text-muted-foreground">
                Set default preferences for article generation
              </p>
            </div>
          </div>

          <Separator />

          {/* Keyword Clusters */}
          <div>
            <Label className="text-base">Keyword Clusters for Automation</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Select which keyword clusters to use for automated content generation
            </p>
            <Select 
              value="select-clusters"
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select clusters" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="plant-protein">Plant Protein</SelectItem>
                <SelectItem value="vegan-supplements">Vegan Supplements</SelectItem>
                <SelectItem value="nutrition">Nutrition & Health</SelectItem>
                <SelectItem value="fitness">Fitness & Training</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* CMS Provider */}
          <div>
            <Label className="text-base">Preferred CMS Provider</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Select which CMS provider to use by default when publishing
            </p>
            <Select 
              value={settings.cmsProvider}
              onValueChange={(value) => setSettings(prev => ({ ...prev, cmsProvider: value }))}
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ghost">Ghost CMS</SelectItem>
                <SelectItem value="wordpress">WordPress</SelectItem>
                <SelectItem value="contentful">Contentful</SelectItem>
                <SelectItem value="strapi">Strapi</SelectItem>
                <SelectItem value="webflow">Webflow</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Sections */}
          <div>
            <Label className="text-base">Sections</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Choose which concluding sections to include in generated articles
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { id: "faq", label: "FAQ" },
                { id: "conclusion", label: "Conclusion" },
                { id: "cta", label: "CTA" },
                { id: "summary", label: "Summary" },
                { id: "takeaways", label: "Key Takeaways" },
                { id: "resources", label: "Additional Resources" }
              ].map((section) => (
                <Badge
                  key={section.id}
                  variant={settings.sections.includes(section.id) ? "default" : "outline"}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => toggleSection(section.id)}
                >
                  {section.label}
                  {settings.sections.includes(section.id) && " ✓"}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {settings.sections.length} sections selected
            </p>
          </div>

          {/* Preferred Article Type */}
          <div>
            <Label className="text-base">Preferred Article Type</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Choose the type of article to generate by default
            </p>
            <Select 
              value={settings.preferredArticleType}
              onValueChange={(value) => setSettings(prev => ({ ...prev, preferredArticleType: value }))}
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any</SelectItem>
                <SelectItem value="blog">Blog Post</SelectItem>
                <SelectItem value="guide">How-to Guide</SelectItem>
                <SelectItem value="comparison">Comparison Article</SelectItem>
                <SelectItem value="listicle">Listicle</SelectItem>
                <SelectItem value="technical">Technical Article</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Content Length */}
          <div>
            <Label className="text-base">Content Length</Label>
            <p className="text-sm text-muted-foreground mb-3">
              Set the default content length for your articles
            </p>
            <Select 
              value={settings.contentLength}
              onValueChange={(value) => setSettings(prev => ({ ...prev, contentLength: value }))}
              disabled={!settings.automationEnabled}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="500-1000">500-1,000 words</SelectItem>
                <SelectItem value="1000-1500">1,000-1,500 words</SelectItem>
                <SelectItem value="1500-2000">1,500-2,000 words</SelectItem>
                <SelectItem value="2000-3000">2,000-3,000 words</SelectItem>
                <SelectItem value="3000+">3,000+ words</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {/* Advanced Content Settings */}
      <Card className="p-6 border border-border">
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Tag className="h-6 w-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-1">Advanced Content Settings</h3>
              <p className="text-sm text-muted-foreground">
                Fine-tune content generation preferences
              </p>
            </div>
          </div>

          <Separator />

          <div className="grid grid-cols-2 gap-6">
            {/* Tone */}
            <div>
              <Label>Tone</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Choose the voice and personality
              </p>
              <Select 
                value={settings.tone}
                onValueChange={(value) => setSettings(prev => ({ ...prev, tone: value }))}
                disabled={!settings.automationEnabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="professional">Professional</SelectItem>
                  <SelectItem value="casual">Casual</SelectItem>
                  <SelectItem value="friendly">Friendly</SelectItem>
                  <SelectItem value="authoritative">Authoritative</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Style */}
            <div>
              <Label>Style</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Define the writing approach
              </p>
              <Select 
                value={settings.style}
                onValueChange={(value) => setSettings(prev => ({ ...prev, style: value }))}
                disabled={!settings.automationEnabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="informative">Informative</SelectItem>
                  <SelectItem value="persuasive">Persuasive</SelectItem>
                  <SelectItem value="storytelling">Storytelling</SelectItem>
                  <SelectItem value="analytical">Analytical</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Goal */}
            <div>
              <Label>Goal</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Set the content objective
              </p>
              <Select 
                value={settings.goal}
                onValueChange={(value) => setSettings(prev => ({ ...prev, goal: value }))}
                disabled={!settings.automationEnabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="educate">Educate</SelectItem>
                  <SelectItem value="convert">Convert</SelectItem>
                  <SelectItem value="engage">Engage</SelectItem>
                  <SelectItem value="inform">Inform</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Target Audience */}
            <div>
              <Label>Target Audience</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Define your readers
              </p>
              <Select 
                value={settings.targetAudience}
                onValueChange={(value) => setSettings(prev => ({ ...prev, targetAudience: value }))}
                disabled={!settings.automationEnabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="general">General Public</SelectItem>
                  <SelectItem value="beginners">Beginners</SelectItem>
                  <SelectItem value="professionals">Professionals</SelectItem>
                  <SelectItem value="experts">Experts</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Content Depth */}
            <div className="col-span-2">
              <Label>Content Depth</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Set the detail level
              </p>
              <Select 
                value={settings.contentDepth}
                onValueChange={(value) => setSettings(prev => ({ ...prev, contentDepth: value }))}
                disabled={!settings.automationEnabled}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="overview">Overview</SelectItem>
                  <SelectItem value="detailed">Detailed</SelectItem>
                  <SelectItem value="comprehensive">Comprehensive</SelectItem>
                  <SelectItem value="extensive">Extensive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} size="lg" className="gradient-primary shadow-md shadow-primary/20">
          <Settings className="h-4 w-4 mr-2" />
          Save All Settings
        </Button>
      </div>
    </div>
  );
};

export default AutomationSettings;
