import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ArrowLeft,
  Monitor,
  Smartphone,
  Upload,
  FileUp,
  X,
  Plus,
  Loader2,
  Info,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";

const regionToIsocode = (region: string): string => {
  const regionMap: Record<string, string> = {
    'google.com': 'us', 'google.co.uk': 'gb', 'google.ca': 'ca', 'google.com.au': 'au',
    'google.co.in': 'in', 'google.de': 'de', 'google.fr': 'fr', 'google.es': 'es',
    'google.it': 'it', 'google.co.jp': 'jp', 'google.com.br': 'br', 'google.com.mx': 'mx',
    'google.nl': 'nl', 'google.pl': 'pl', 'google.se': 'se', 'google.com.sg': 'sg',
    'google.co.za': 'za', 'google.com.ng': 'ng', 'google.co.nz': 'nz', 'google.ie': 'ie',
    'google.at': 'at', 'google.be': 'be', 'google.ch': 'ch', 'google.dk': 'dk',
    'google.fi': 'fi', 'google.no': 'no', 'google.pt': 'pt', 'google.com.ar': 'ar',
    'google.cl': 'cl', 'google.co.il': 'il', 'google.com.ph': 'ph', 'google.com.pk': 'pk',
    'google.com.eg': 'eg', 'google.ae': 'ae', 'google.co.th': 'th', 'google.com.my': 'my',
    'google.co.id': 'id', 'google.com.vn': 'vn', 'google.co.kr': 'kr', 'google.com.tw': 'tw',
    'google.com.hk': 'hk', 'google.ru': 'ru', 'google.com.ua': 'ua', 'google.com.tr': 'tr',
    'google.com.sa': 'sa', 'google.co.ke': 'ke',
  };
  return regionMap[region] || 'us';
};

const AddSeoKeyword = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const activeDomainId = selectedDomain?.id?.toString() || "";

  const [loading, setLoading] = useState(false);
  const [keywordText, setKeywordText] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [inputMode, setInputMode] = useState<"text" | "csv">("text");
  const [file, setFile] = useState<File | null>(null);
  const [urlSlug, setUrlSlug] = useState("");
  const [region, setRegion] = useState("google.com");
  const [language, setLanguage] = useState("en");
  const [platform, setPlatform] = useState("desktop");
  const [tagsEnabled, setTagsEnabled] = useState(true);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [allDomainTags, setAllDomainTags] = useState<string[]>([]);
  const [result, setResult] = useState<{
    seo_created_count: number;
    seo_skipped_count: number;
    total_processed: number;
  } | null>(null);

  useEffect(() => {
    if (activeDomainId) {
      apiClient.getSeoKeywordTags(activeDomainId)
        .then((res: any) => setAllDomainTags(res.all_tags || []))
        .catch(() => {});
    }
  }, [activeDomainId]);

  const handleKeywordInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === 'Enter' || e.key === ',') && keywordInput.trim()) {
      e.preventDefault();
      const newKeywords = keywordInput
        .split(/[,\n]+/)
        .map(k => k.trim())
        .filter(k => k.length > 0 && !keywords.includes(k));
      if (newKeywords.length > 0) {
        setKeywords(prev => [...prev, ...newKeywords]);
      }
      setKeywordInput("");
    }
  };

  const handleKeywordInputPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text');
    const newKeywords = pasted
      .split(/[,\n]+/)
      .map(k => k.trim())
      .filter(k => k.length > 0 && !keywords.includes(k));
    if (newKeywords.length > 0) {
      setKeywords(prev => [...prev, ...newKeywords]);
    }
    setKeywordInput("");
  };

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if ((e.key === 'Enter' || e.key === ',') && tagInput.trim()) {
      e.preventDefault();
      const tag = tagInput.trim().toLowerCase();
      if (!tags.includes(tag)) {
        setTags(prev => [...prev, tag]);
      }
      setTagInput("");
    }
  };

  const handleSubmit = async () => {
    if (!activeDomainId) return;
    setLoading(true);
    setResult(null);

    try {
      let res: any;

      if (inputMode === "csv" && file) {
        const formData = new FormData();
        formData.append('domain_id', activeDomainId);
        formData.append('file', file);
        formData.append('platform', platform);
        formData.append('region', region);
        formData.append('language_code', language);
        if (urlSlug.trim()) {
          formData.append('target_url', urlSlug.trim());
        }
        if (tagsEnabled && tags.length > 0) {
          formData.append('tags', JSON.stringify(tags));
        }
        const isocode = regionToIsocode(region);
        formData.append('isocode', isocode);
        res = await apiClient.importSeoKeywords(formData);
      } else {
        if (keywords.length === 0) {
          toast({ title: "No keywords", description: "Enter at least one keyword", variant: "destructive" });
          setLoading(false);
          return;
        }

        const isocode = regionToIsocode(region);
        res = await apiClient.importSeoKeywords({
          domain_id: Number(activeDomainId),
          keywords,
          platform,
          region,
          isocode,
          language_code: language,
          target_url: urlSlug.trim() || undefined,
          tags: tagsEnabled && tags.length > 0 ? tags : undefined,
        });
      }

      setResult(res);
      toast({
        title: "Keywords added",
        description: `${res.seo_created_count} keyword(s) added to SEO tracking`,
      });
    } catch (err: any) {
      toast({
        title: "Failed to add keywords",
        description: err?.message || "Could not add keywords. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setKeywordText("");
    setKeywords([]);
    setKeywordInput("");
    setInputMode("text");
    setFile(null);
    setUrlSlug("");
    setRegion("google.com");
    setLanguage("en");
    setPlatform("desktop");
    setTagsEnabled(true);
    setTagInput("");
    setTags([]);
    setResult(null);
  };

  return (
    <div className="flex-1 p-6 md:p-8 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          className="h-10 w-10 rounded-full border border-border flex items-center justify-center hover:bg-muted transition-colors"
          onClick={() => navigate('/seo-rankings')}
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold">Add Keyword</h1>
          <p className="text-muted-foreground text-sm">
            Enter the required details in all the specified fields below
          </p>
        </div>
      </div>

      {/* Card Container */}
      <div className="rounded-xl border border-border bg-card shadow-sm">

        {/* Section: Project Settings */}
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <Label className="text-sm font-medium">
                Project domain <span className="text-red-500">*</span>
              </Label>
              <Input
                value={selectedDomain?.url || ''}
                disabled
                className="mt-1.5 bg-muted/50"
                placeholder="https://www.example.com/"
              />
            </div>
            <div>
              <Label className="text-sm font-medium">URL slug</Label>
              <Input
                value={urlSlug}
                onChange={(e) => setUrlSlug(e.target.value)}
                className="mt-1.5"
                placeholder="blog/your-page-slug/"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <Label className="text-sm font-medium">
                Region <span className="text-red-500">*</span>
              </Label>
              <select
                className="w-full mt-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
              >
                <option value="google.com">google.com (United States)</option>
                <option value="google.co.uk">google.co.uk (United Kingdom)</option>
                <option value="google.ca">google.ca (Canada)</option>
                <option value="google.com.au">google.com.au (Australia)</option>
                <option value="google.co.in">google.co.in (India)</option>
                <option value="google.de">google.de (Germany)</option>
                <option value="google.fr">google.fr (France)</option>
                <option value="google.es">google.es (Spain)</option>
                <option value="google.it">google.it (Italy)</option>
                <option value="google.co.jp">google.co.jp (Japan)</option>
                <option value="google.com.br">google.com.br (Brazil)</option>
                <option value="google.com.mx">google.com.mx (Mexico)</option>
                <option value="google.nl">google.nl (Netherlands)</option>
                <option value="google.pl">google.pl (Poland)</option>
                <option value="google.se">google.se (Sweden)</option>
                <option value="google.com.sg">google.com.sg (Singapore)</option>
                <option value="google.co.za">google.co.za (South Africa)</option>
                <option value="google.co.nz">google.co.nz (New Zealand)</option>
                <option value="google.ie">google.ie (Ireland)</option>
                <option value="google.at">google.at (Austria)</option>
                <option value="google.be">google.be (Belgium)</option>
                <option value="google.ch">google.ch (Switzerland)</option>
                <option value="google.dk">google.dk (Denmark)</option>
                <option value="google.fi">google.fi (Finland)</option>
                <option value="google.no">google.no (Norway)</option>
                <option value="google.pt">google.pt (Portugal)</option>
                <option value="google.ae">google.ae (UAE)</option>
                <option value="google.com.sa">google.com.sa (Saudi Arabia)</option>
                <option value="google.com.tr">google.com.tr (Turkey)</option>
                <option value="google.ru">google.ru (Russia)</option>
                <option value="google.co.kr">google.co.kr (South Korea)</option>
                <option value="google.com.tw">google.com.tw (Taiwan)</option>
                <option value="google.com.hk">google.com.hk (Hong Kong)</option>
                <option value="google.co.id">google.co.id (Indonesia)</option>
                <option value="google.com.my">google.com.my (Malaysia)</option>
                <option value="google.co.th">google.co.th (Thailand)</option>
                <option value="google.com.ph">google.com.ph (Philippines)</option>
                <option value="google.com.vn">google.com.vn (Vietnam)</option>
                <option value="google.com.pk">google.com.pk (Pakistan)</option>
                <option value="google.com.eg">google.com.eg (Egypt)</option>
                <option value="google.co.ke">google.co.ke (Kenya)</option>
                <option value="google.com.ng">google.com.ng (Nigeria)</option>
                <option value="google.com.ar">google.com.ar (Argentina)</option>
                <option value="google.cl">google.cl (Chile)</option>
                <option value="google.co.il">google.co.il (Israel)</option>
                <option value="google.com.ua">google.com.ua (Ukraine)</option>
              </select>
            </div>

            <div>
              <Label className="text-sm font-medium">
                Language <span className="text-red-500">*</span>
              </Label>
              <select
                className="w-full mt-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="en">(English)</option>
                <option value="es">(Spanish)</option>
                <option value="fr">(French)</option>
                <option value="de">(German)</option>
                <option value="it">(Italian)</option>
                <option value="pt">(Portuguese)</option>
                <option value="nl">(Dutch)</option>
                <option value="pl">(Polish)</option>
                <option value="sv">(Swedish)</option>
                <option value="da">(Danish)</option>
                <option value="fi">(Finnish)</option>
                <option value="no">(Norwegian)</option>
                <option value="ja">(Japanese)</option>
                <option value="ko">(Korean)</option>
                <option value="zh">(Chinese)</option>
                <option value="ar">(Arabic)</option>
                <option value="hi">(Hindi)</option>
                <option value="ru">(Russian)</option>
                <option value="tr">(Turkish)</option>
                <option value="th">(Thai)</option>
                <option value="vi">(Vietnamese)</option>
                <option value="id">(Indonesian)</option>
                <option value="ms">(Malay)</option>
                <option value="tl">(Tagalog)</option>
                <option value="uk">(Ukrainian)</option>
                <option value="he">(Hebrew)</option>
              </select>
            </div>

            <div>
              <Label className="text-sm font-medium">
                Platform <span className="text-red-500">*</span>
              </Label>
              <div className="flex gap-2 mt-1.5">
                <Button
                  type="button"
                  variant={platform === 'desktop' ? 'default' : 'outline'}
                  size="sm"
                  className={platform === 'desktop' ? 'gradient-primary' : ''}
                  onClick={() => setPlatform('desktop')}
                >
                  <Monitor className="h-4 w-4 mr-1" />
                  Desktop
                </Button>
                <Button
                  type="button"
                  variant={platform === 'mobile' ? 'default' : 'outline'}
                  size="sm"
                  className={platform === 'mobile' ? 'gradient-primary' : ''}
                  onClick={() => setPlatform('mobile')}
                >
                  <Smartphone className="h-4 w-4 mr-1" />
                  Mobile
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-border" />

        {/* Section: Keywords & Tags */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Keywords */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">
                  Keywords <span className="text-red-500">*</span>
                </Label>
                <div className="flex rounded-md border border-input overflow-hidden">
                  <button
                    className={`px-3 py-1 text-xs font-medium transition-colors ${inputMode === 'csv' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-muted'}`}
                    onClick={() => setInputMode('csv')}
                  >
                    <Upload className="h-3 w-3 inline mr-1" />
                    CSV or Text
                  </button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Keywords will be limited as per your plan</p>

              {inputMode === 'text' ? (
                <div className="space-y-2">
                  <div className="rounded-lg border border-input bg-background overflow-hidden">
                    <Input
                      value={keywordInput}
                      onChange={(e) => setKeywordInput(e.target.value)}
                      onKeyDown={handleKeywordInputKeyDown}
                      onPaste={handleKeywordInputPaste}
                      placeholder="Use comma or press enter to separate your keywords"
                      className="text-sm border-0 focus-visible:ring-0 rounded-none"
                    />
                    <div className="min-h-[200px] max-h-[300px] overflow-y-auto p-3">
                      {keywords.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {keywords.map((kw, idx) => (
                            <Badge key={`${kw}-${idx}`} variant="secondary" className="gap-1 py-1 px-2.5">
                              {kw}
                              <button
                                className="ml-0.5 hover:text-destructive transition-colors"
                                onClick={() => setKeywords(prev => prev.filter((_, i) => i !== idx))}
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                          Type keywords above and press Enter
                        </div>
                      )}
                    </div>
                  </div>
                  {keywords.length > 0 && (
                    <p className="text-xs text-muted-foreground">{keywords.length} keyword(s) added</p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div
                    className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors min-h-[120px] flex flex-col items-center justify-center"
                    onClick={() => document.getElementById('add-kw-csv-input')?.click()}
                    onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      const f = e.dataTransfer.files?.[0];
                      if (f && (f.name.endsWith('.csv') || f.name.endsWith('.txt'))) {
                        setFile(f);
                      }
                    }}
                  >
                    <input
                      id="add-kw-csv-input"
                      type="file"
                      accept=".csv,.txt"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) setFile(f);
                      }}
                    />
                    {file ? (
                      <div className="flex items-center gap-2">
                        <FileUp className="h-5 w-5 text-primary" />
                        <span className="text-sm font-medium">{file.name}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-5 w-5"
                          onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ) : (
                      <>
                        <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                        <p className="text-sm text-muted-foreground">Drag & drop CSV/TXT file, or click to browse</p>
                        <p className="text-xs text-muted-foreground mt-1">One keyword per line or "keyword" column</p>
                      </>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-px bg-border" />
                    <span className="text-xs text-muted-foreground uppercase">or paste keywords</span>
                    <div className="flex-1 h-px bg-border" />
                  </div>

                  <textarea
                    className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
                    placeholder="Use comma or press enter to separate your keywords"
                    value={keywordText}
                    onChange={(e) => { setKeywordText(e.target.value); setFile(null); }}
                    disabled={!!file}
                  />
                </div>
              )}
            </div>

            {/* Tags */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Label className="text-sm font-medium">Add Tags</Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent>Tags help organize and filter your keywords</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <Switch
                  checked={tagsEnabled}
                  onCheckedChange={setTagsEnabled}
                />
              </div>
              <p className="text-xs text-muted-foreground">Enter multiple tags separated by comma</p>

              {tagsEnabled && (
                <>
                  <div className="rounded-lg border border-input bg-background overflow-hidden">
                    <Input
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={handleTagKeyDown}
                      placeholder="Use comma or press enter to separate your tags"
                      className="text-sm border-0 focus-visible:ring-0 rounded-none"
                    />
                    {tags.length > 0 && (
                      <div className="p-3 border-t border-input max-h-[150px] overflow-y-auto">
                        <div className="flex flex-wrap gap-1.5">
                          {tags.map(tag => (
                            <Badge key={tag} variant="secondary" className="gap-1 py-1 px-2.5">
                              {tag}
                              <button
                                className="ml-0.5 hover:text-destructive transition-colors"
                                onClick={() => setTags(prev => prev.filter(t => t !== tag))}
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {allDomainTags.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Other tags in this project</p>
                      <div className="flex flex-wrap gap-1.5">
                        {allDomainTags.filter(t => !tags.includes(t)).map(tag => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="cursor-pointer hover:bg-primary/10 transition-colors"
                            onClick={() => setTags(prev => [...prev, tag])}
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Result */}
        {result && (
          <>
            <div className="border-t border-border" />
            <div className="p-6">
              <div className="rounded-lg border border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-900 p-4 space-y-2">
                <p className="text-sm font-semibold text-green-700 dark:text-green-400">Keywords Added Successfully</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-muted-foreground max-w-xs">
                  <span>SEO tracking added:</span>
                  <span className="font-medium text-foreground">{result.seo_created_count}</span>
                  <span>Already tracked:</span>
                  <span className="font-medium text-foreground">{result.seo_skipped_count}</span>
                  <span>Total processed:</span>
                  <span className="font-medium text-foreground">{result.total_processed}</span>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Footer Actions */}
        <div className="border-t border-border" />
        <div className="flex items-center justify-end gap-3 p-6">
          <Button variant="outline" size="lg" onClick={() => navigate('/seo-rankings')}>
            Cancel
          </Button>
          {!result ? (
            <Button
              onClick={handleSubmit}
              disabled={loading || (keywords.length === 0 && !file)}
              className="gradient-primary"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Keyword
                </>
              )}
            </Button>
          ) : (
            <Button className="gradient-primary" size="lg" onClick={handleReset}>
              Add More
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddSeoKeyword;
