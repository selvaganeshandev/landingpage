import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { 
  Globe,
  Plus,
  TrendingUp,
  TrendingDown,
  MapPin,
  Languages
} from "lucide-react";
import { AddLanguageDialog } from "@/components/AddLanguageDialog";
import { ConfigureLanguagesDialog } from "@/components/ConfigureLanguagesDialog";
import { 
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend 
} from "recharts";

const languages = [
  { code: "en", name: "English", mentions: 221, visibility: 94, sentiment: 74, trend: 15, color: "hsl(var(--chart-1))" },
  { code: "es", name: "Spanish", mentions: 87, visibility: 78, sentiment: 71, trend: 22, color: "hsl(var(--chart-2))" },
  { code: "fr", name: "French", mentions: 54, visibility: 72, sentiment: 68, trend: 8, color: "hsl(var(--chart-3))" },
  { code: "de", name: "German", mentions: 48, visibility: 75, sentiment: 73, trend: 12, color: "hsl(var(--chart-4))" },
  { code: "pt", name: "Portuguese", mentions: 39, visibility: 68, sentiment: 70, trend: 18, color: "hsl(var(--chart-5))" },
  { code: "it", name: "Italian", mentions: 31, visibility: 65, sentiment: 69, trend: 5, color: "hsl(var(--success))" },
];

const regions = [
  { name: "North America", mentions: 285, share: 48, languages: ["English", "Spanish"] },
  { name: "Europe", mentions: 178, share: 30, languages: ["English", "French", "German", "Italian"] },
  { name: "Latin America", mentions: 95, share: 16, languages: ["Spanish", "Portuguese"] },
  { name: "Asia Pacific", mentions: 37, share: 6, languages: ["English"] },
];

const languageTrends = [
  { month: "Jul", en: 195, es: 72, fr: 48, de: 42 },
  { month: "Aug", en: 202, es: 75, fr: 50, de: 44 },
  { month: "Sep", en: 208, es: 78, fr: 51, de: 46 },
  { month: "Oct", en: 215, es: 82, fr: 53, de: 47 },
  { month: "Nov", en: 221, es: 87, fr: 54, de: 48 },
];

const crossCulturalInsights = [
  {
    language: "Spanish",
    insight: "Higher engagement with 'natural ingredients' messaging",
    sentiment: 71,
    opportunity: "Expand organic/natural product positioning"
  },
  {
    language: "French",
    insight: "Strong association with 'sustainable' and 'eco-friendly'",
    sentiment: 68,
    opportunity: "Highlight environmental certifications"
  },
  {
    language: "German",
    insight: "Focus on 'quality' and 'scientific backing'",
    sentiment: 73,
    opportunity: "Provide more research citations and testing data"
  },
  {
    language: "Portuguese",
    insight: "Growing interest in 'weight loss' applications",
    sentiment: 70,
    opportunity: "Create localized weight management content"
  },
];

const topPromptsByLanguage = {
  "English": [
    { prompt: "best vegan protein powder", mentions: 89 },
    { prompt: "plant-based protein for athletes", mentions: 67 },
    { prompt: "organic vegan protein", mentions: 45 }
  ],
  "Spanish": [
    { prompt: "mejor proteína vegana", mentions: 34 },
    { prompt: "proteína vegetal para deportistas", mentions: 28 },
    { prompt: "proteína orgánica vegana", mentions: 18 }
  ],
  "French": [
    { prompt: "meilleure protéine végane", mentions: 22 },
    { prompt: "protéine végétale bio", mentions: 18 },
    { prompt: "protéine pour sportifs végans", mentions: 12 }
  ],
  "German": [
    { prompt: "beste vegane proteinpulver", mentions: 20 },
    { prompt: "pflanzliches protein", mentions: 16 },
    { prompt: "bio veganes protein", mentions: 10 }
  ],
};

const Multilingual = () => {
  const { toast } = useToast();
  const [configureDialogOpen, setConfigureDialogOpen] = useState(false);
  const [addLanguageDialogOpen, setAddLanguageDialogOpen] = useState(false);

  const handleConfigureLanguages = () => {
    setConfigureDialogOpen(true);
  };

  const handleAddLanguage = () => {
    setAddLanguageDialogOpen(true);
  };

  const pieData = languages.map(l => ({
    name: l.name,
    value: l.mentions,
    color: l.color
  }));

  return (
    <div className="p-8 space-y-8 bg-background">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Multilingual Monitoring</h1>
          <p className="text-muted-foreground mt-2">
            Global brand tracking across languages and regions
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={handleConfigureLanguages}>
            <Languages className="h-4 w-4 mr-2" />
            Configure Languages
          </Button>
          <Button onClick={handleAddLanguage} className="gradient-primary shadow-md shadow-primary/20">
            <Plus className="h-4 w-4 mr-2" />
            Add Language
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Languages Tracked</p>
            <Globe className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">{languages.length}</h3>
          <p className="text-xs text-muted-foreground mt-1">Active monitoring</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Total Mentions</p>
            <MapPin className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">595</h3>
          <p className="text-xs text-muted-foreground mt-1">Across all languages</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Fastest Growing</p>
            <TrendingUp className="h-5 w-5 text-success" />
          </div>
          <h3 className="text-3xl font-bold">Spanish</h3>
          <p className="text-xs text-success mt-1">+22% this month</p>
        </Card>

        <Card className="p-6 transition-all duration-300 border border-border hover:border-primary">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted-foreground font-medium">Avg Sentiment</p>
            <Languages className="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 className="text-3xl font-bold">71%</h3>
          <p className="text-xs text-muted-foreground mt-1">Global average</p>
        </Card>
      </div>

      {/* Language Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-6 border border-border">
          <h3 className="text-lg font-semibold mb-6">Language Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 lg:col-span-2">
          <h3 className="text-lg font-semibold mb-6">Language Growth Trends</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={languageTrends}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip 
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="en" name="English" stroke="hsl(var(--chart-1))" strokeWidth={3} />
              <Line type="monotone" dataKey="es" name="Spanish" stroke="hsl(var(--chart-2))" strokeWidth={2} />
              <Line type="monotone" dataKey="fr" name="French" stroke="hsl(var(--chart-3))" strokeWidth={2} />
              <Line type="monotone" dataKey="de" name="German" stroke="hsl(var(--chart-4))" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Language Performance */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Language Performance</h3>
        <div className="space-y-6">
          {languages.map((language) => (
            <div key={language.code} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg" style={{ backgroundColor: language.color, opacity: 0.2 }}>
                    {language.code.toUpperCase()}
                  </div>
                  <div>
                    <h4 className="font-semibold">{language.name}</h4>
                    <p className="text-sm text-muted-foreground">{language.mentions} mentions</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Visibility</p>
                    <p className="text-lg font-bold">{language.visibility}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Sentiment</p>
                    <p className="text-lg font-bold">{language.sentiment}%</p>
                  </div>
                  <div className="text-right min-w-[80px]">
                    <p className="text-sm text-muted-foreground">Trend</p>
                    <div className="flex items-center justify-end gap-1">
                      {language.trend > 0 ? (
                        <TrendingUp className="h-4 w-4 text-success" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-destructive" />
                      )}
                      <span className={`text-lg font-bold ${language.trend > 0 ? 'text-success' : 'text-destructive'}`}>
                        {language.trend > 0 ? '+' : ''}{language.trend}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <Progress value={language.visibility} className="h-2" />
                <Progress value={language.sentiment} className="h-2" />
                <Progress value={Math.abs(language.trend) * 5} className="h-2" />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Regional Distribution */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Regional Distribution</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {regions.map((region) => (
            <div key={region.name} className="space-y-3">
              <div className="flex items-center gap-3 mb-2">
                <MapPin className="h-5 w-5 text-primary" />
                <h4 className="font-semibold">{region.name}</h4>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Mentions</span>
                  <span className="font-bold">{region.mentions}</span>
                </div>
                <Progress value={region.share} className="h-2" />
                <p className="text-xs text-muted-foreground">{region.share}% of total</p>
              </div>
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">Languages:</p>
                <div className="flex flex-wrap gap-1">
                  {region.languages.map((lang) => (
                    <Badge key={lang} variant="secondary" className="text-xs">
                      {lang}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Cross-Cultural Insights */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Cross-Cultural Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {crossCulturalInsights.map((insight, idx) => (
            <div key={idx} className="p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-3">
                <h4 className="font-semibold">{insight.language}</h4>
                <Badge variant="secondary">{insight.sentiment}% sentiment</Badge>
              </div>
              <p className="text-sm mb-3">{insight.insight}</p>
              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                <p className="text-xs font-medium text-primary mb-1">Opportunity:</p>
                <p className="text-sm">{insight.opportunity}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Top Prompts by Language */}
      <Card className="p-6 border border-border">
        <h3 className="text-lg font-semibold mb-6">Top Prompts by Language</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(topPromptsByLanguage).map(([language, prompts]) => (
            <div key={language} className="space-y-3">
              <h4 className="font-semibold">{language}</h4>
              <div className="space-y-2">
                {prompts.map((prompt, idx) => (
                  <div key={idx} className="p-3 rounded-lg border border-border">
                    <p className="text-sm font-mono mb-1">{prompt.prompt}</p>
                    <p className="text-xs text-muted-foreground">{prompt.mentions} mentions</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Dialogs */}
      <AddLanguageDialog
        open={addLanguageDialogOpen}
        onOpenChange={setAddLanguageDialogOpen}
      />
      <ConfigureLanguagesDialog
        open={configureDialogOpen}
        onOpenChange={setConfigureDialogOpen}
      />
    </div>
  );
};

export default Multilingual;
