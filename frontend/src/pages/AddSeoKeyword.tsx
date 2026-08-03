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
  Search,
  RotateCcw,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { useDomainStore } from "@/stores/domainStore";
import { useSidebar } from "@/contexts/SidebarContext";

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

const regionFlagMap: Record<string, string> = {
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

// The domain records the country it was set up for, but this form always opened
// on google.com — so 51 of the 63 domains, all set to India, had to have their
// country re-picked on every visit, and a missed pick silently tracked rankings
// from the wrong country.
//
// Keyed on the country name Domain.country stores, which is a display string
// ("United States", not "US"), so the lookup matches on exactly that.
const countryToRegion: Record<string, string> = {
  'India': 'google.co.in',
  'United States': 'google.com',
  'United Kingdom': 'google.co.uk',
  'Canada': 'google.ca',
  'Australia': 'google.com.au',
  'Germany': 'google.de',
  'France': 'google.fr',
  'Spain': 'google.es',
  'Italy': 'google.it',
  'Japan': 'google.co.jp',
  'Brazil': 'google.com.br',
  'Mexico': 'google.com.mx',
  'Netherlands': 'google.nl',
  'Poland': 'google.pl',
  'Sweden': 'google.se',
  'Singapore': 'google.com.sg',
  'South Africa': 'google.co.za',
  'Nigeria': 'google.com.ng',
  'New Zealand': 'google.co.nz',
  'Ireland': 'google.ie',
  'Austria': 'google.at',
  'Belgium': 'google.be',
  'Switzerland': 'google.ch',
  'Denmark': 'google.dk',
  'Finland': 'google.fi',
  'Norway': 'google.no',
  'Portugal': 'google.pt',
  'Argentina': 'google.com.ar',
  'Chile': 'google.cl',
  'Israel': 'google.co.il',
  'Philippines': 'google.com.ph',
  'Pakistan': 'google.com.pk',
  'Egypt': 'google.com.eg',
  'United Arab Emirates': 'google.ae',
  'Thailand': 'google.co.th',
  'Malaysia': 'google.com.my',
  'Indonesia': 'google.co.id',
  'Vietnam': 'google.com.vn',
  'South Korea': 'google.co.kr',
  'Taiwan': 'google.com.tw',
  'Hong Kong': 'google.com.hk',
  'Russia': 'google.ru',
  'Ukraine': 'google.com.ua',
  'Turkey': 'google.com.tr',
  'Saudi Arabia': 'google.com.sa',
  'Kenya': 'google.co.ke',
};

const regionForCountry = (country?: string | null): string =>
  (country && countryToRegion[country.trim()]) || 'google.com';

const AddSeoKeyword = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { selectedDomain } = useDomainStore();
  const { isOpen: sidebarOpen } = useSidebar();
  const activeDomainId = selectedDomain?.id?.toString() || "";

  const [loading, setLoading] = useState(false);
  const [keywordText, setKeywordText] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [inputMode, setInputMode] = useState<"text" | "csv">("text");
  const [file, setFile] = useState<File | null>(null);
  const [urlSlug, setUrlSlug] = useState("");
  const [region, setRegion] = useState(() => regionForCountry(selectedDomain?.country));
  const [language, setLanguage] = useState("en");
  const [platform, setPlatform] = useState("desktop");
  const [tagsEnabled, setTagsEnabled] = useState(true);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [allDomainTags, setAllDomainTags] = useState<string[]>([]);

  // CSV preview flow state
  const [csvStep, setCsvStep] = useState<"idle" | "select-column" | "preview">("idle");
  const [csvColumns, setCsvColumns] = useState<string[][]>([]); // columns[colIndex][rowIndex]
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvSelectedCol, setCsvSelectedCol] = useState<number>(0);
  const [csvParsedKeywords, setCsvParsedKeywords] = useState<string[]>([]);
  const [csvSearch, setCsvSearch] = useState("");


  useEffect(() => {
    if (activeDomainId) {
      apiClient.getSeoKeywordTags(activeDomainId)
        .then((res: any) => setAllDomainTags(res.all_tags || []))
        .catch(() => {});
    }
  }, [activeDomainId]);

  // Follow the domain's country until the user picks a region themselves.
  // useState's initialiser runs once, so without this the default is wrong
  // whenever the domain resolves after mount — a page refresh, or switching
  // domains from the sidebar with this form already open.
  const [regionTouched, setRegionTouched] = useState(false);
  useEffect(() => {
    if (!regionTouched) {
      setRegion(regionForCountry(selectedDomain?.country));
    }
  }, [selectedDomain?.country, regionTouched]);


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
      if (!tags.includes(tag) && tags.length < 20) {
        setTags(prev => [...prev, tag]);
      }
      setTagInput("");
    }
  };

  // --- CSV Preview Flow ---
  const handleCsvFileSelected = (f: File) => {
    setFile(f);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (!text) return;

      const lines = text.split(/\r?\n/).filter(l => l.trim());
      if (lines.length === 0) return;

      // Simple CSV parse (handles quoted fields)
      const parseLine = (line: string): string[] => {
        const result: string[] = [];
        let current = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {
          const ch = line[i];
          if (ch === '"') { inQuotes = !inQuotes; continue; }
          if (ch === ',' && !inQuotes) { result.push(current.trim()); current = ''; continue; }
          current += ch;
        }
        result.push(current.trim());
        return result;
      };

      const rows = lines.map(parseLine);
      const maxCols = Math.max(...rows.map(r => r.length));

      // Build column arrays
      const cols: string[][] = [];
      for (let c = 0; c < maxCols; c++) {
        cols.push(rows.map(r => r[c] || ''));
      }

      // Detect if first row is a header
      const firstRow = rows[0] || [];
      const hasHeader = firstRow.some(cell =>
        /^(keyword|keywords|query|queries|search.term|term|phrase)$/i.test(cell)
      );

      setCsvHeaders(hasHeader ? firstRow : firstRow.map((_, i) => `Column ${i + 1}`));
      // If header row, skip it from column data
      const dataCols: string[][] = [];
      for (let c = 0; c < maxCols; c++) {
        dataCols.push((hasHeader ? rows.slice(1) : rows).map(r => r[c] || '').filter(v => v));
      }
      setCsvColumns(dataCols);

      // Auto-select the keyword column
      const kwColIdx = hasHeader
        ? firstRow.findIndex(h => /^(keyword|keywords|query|term)$/i.test(h))
        : 0;
      setCsvSelectedCol(kwColIdx >= 0 ? kwColIdx : 0);
      setCsvStep("select-column");
    };
    reader.readAsText(f);
  };

  const handleCsvNextStep = () => {
    const col = csvColumns[csvSelectedCol] || [];
    const unique = [...new Set(col.map(k => k.trim().toLowerCase()).filter(k => k.length > 0 && k.length <= 255))];
    setCsvParsedKeywords(unique);
    setCsvSearch("");
    setCsvStep("preview");
  };

  const handleCsvConfirm = () => {
    setKeywords(csvParsedKeywords);
    setInputMode("text"); // Switch to text mode to show the keywords
    setCsvStep("idle");
    setCsvColumns([]);
    setCsvHeaders([]);
    setCsvParsedKeywords([]);
    setFile(null);
  };

  const handleCsvClose = () => {
    setCsvStep("idle");
    setCsvColumns([]);
    setCsvHeaders([]);
    setCsvParsedKeywords([]);
    setFile(null);
  };

  const filteredCsvKeywords = csvSearch
    ? csvParsedKeywords.filter(k => k.includes(csvSearch.toLowerCase()))
    : csvParsedKeywords;

  const handleSubmit = async () => {
    if (!activeDomainId) return;
    setLoading(true);

    try {
      if (keywords.length === 0) {
        toast({ title: "No keywords", description: "Enter at least one keyword", variant: "destructive" });
        setLoading(false);
        return;
      }

      const isocode = regionToIsocode(region);
      const res: any = await apiClient.importSeoKeywords({
        domain_id: Number(activeDomainId),
        keywords,
        platform,
        region,
        isocode,
        language_code: language,
        target_url: urlSlug.trim() || undefined,
        tags: tagsEnabled && tags.length > 0 ? tags : undefined,
      });

      toast({
        title: "Keywords added",
        description: `${res.seo_created_count} keyword(s) added to SEO tracking`,
      });
      navigate('/seo-rankings');
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



  return (
    <div className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full">
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

      {/* 3-column layout like RankMax */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-6">

        {/* ============ LEFT COLUMN: Project Settings ============ */}
        <div className="space-y-5">
          <div>
            <Label className="text-sm font-medium">
              Project domain <span className="text-destructive">*</span>
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
              placeholder="blog/rank-higher-on-google/"
            />
          </div>

          <div>
            <Label className="text-sm font-medium">
              Region <span className="text-destructive">*</span>
            </Label>
            <div className="relative mt-1.5">
              <img
                src={`https://flagcdn.com/20x15/${regionFlagMap[region] || 'us'}.png`}
                alt=""
                className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-3.5 rounded-sm object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
              <select
                className="w-full rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring appearance-none"
                value={region}
                onChange={(e) => { setRegion(e.target.value); setRegionTouched(true); }}
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
              <svg className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
              </svg>
            </div>
          </div>

          <div>
            <Label className="text-sm font-medium">
              Language <span className="text-destructive">*</span>
            </Label>
            <div className="relative mt-1.5">
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring appearance-none"
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
              <svg className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
              </svg>
            </div>
          </div>

          <div>
            <Label className="text-sm font-medium">
              Platform <span className="text-destructive">*</span>
            </Label>
            <div className="flex gap-3 mt-1.5">
              <button
                type="button"
                className={`flex flex-col items-center justify-center w-20 h-20 rounded-lg border-2 transition-all ${platform === 'desktop' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
                onClick={() => setPlatform('desktop')}
              >
                <Monitor className={`h-7 w-7 mb-1 ${platform === 'desktop' ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className={`text-xs font-medium ${platform === 'desktop' ? 'text-primary' : 'text-muted-foreground'}`}>Desktop</span>
              </button>
              <button
                type="button"
                className={`flex flex-col items-center justify-center w-20 h-20 rounded-lg border-2 transition-all ${platform === 'mobile' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'}`}
                onClick={() => setPlatform('mobile')}
              >
                <Smartphone className={`h-7 w-7 mb-1 ${platform === 'mobile' ? 'text-primary' : 'text-muted-foreground'}`} />
                <span className={`text-xs font-medium ${platform === 'mobile' ? 'text-primary' : 'text-muted-foreground'}`}>Mobile</span>
              </button>
            </div>
          </div>
        </div>

        {/* ============ CENTER COLUMN: Keywords ============ */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-sm font-medium">
                Keywords <span className="text-destructive">*</span>
              </Label>
              <p className="text-xs text-muted-foreground mt-0.5">Keywords will be limited as per your plan</p>
            </div>
            <button
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${inputMode === 'csv' ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-input hover:bg-muted'}`}
              onClick={() => setInputMode(inputMode === 'csv' ? 'text' : 'csv')}
            >
              <Upload className="h-3 w-3" />
              CSV or Text
            </button>
          </div>

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
                <div className="min-h-[250px] max-h-[350px] overflow-y-auto p-3">
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
                    handleCsvFileSelected(f);
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
                    if (f) handleCsvFileSelected(f);
                  }}
                />
                <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground">Drag & drop CSV/TXT file, or click to browse</p>
                <p className="text-xs text-muted-foreground mt-1">One keyword per line or "keyword" column</p>
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

        {/* ============ RIGHT COLUMN: Tags ============ */}
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

      {/* Footer Actions */}
      <div className="flex items-center justify-center gap-3 mt-8">
        <Button variant="outline" size="lg" onClick={() => navigate('/seo-rankings')}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={loading || keywords.length === 0}
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
      </div>

      {/* ================================================================ */}
      {/* CSV UPLOAD OVERLAY — Step 1: Column Selection */}
      {/* ================================================================ */}
      {csvStep === "select-column" && (
        <div className="fixed top-0 right-0 bottom-0 z-50 bg-background flex flex-col transition-all duration-150" style={{ left: sidebarOpen ? '256px' : '64px' }}>
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div>
              <h2 className="text-2xl font-bold">CSV Upload</h2>
              <p className="text-muted-foreground text-sm">Select the appropriate column which has all your keywords</p>
            </div>
            <button onClick={handleCsvClose} className="h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-6">
            <div className="max-w-4xl mx-auto">
              {csvColumns.length > 1 ? (
                // Multi-column CSV: show columns as selectable radio options
                <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(csvColumns.length, 5)}, 1fr)` }}>
                  {csvColumns.map((col, colIdx) => (
                    <div key={colIdx}>
                      <label className="flex items-center gap-2 p-3 rounded-lg border border-border cursor-pointer hover:border-primary/50 transition-colors mb-2">
                        <input
                          type="radio"
                          name="csv-col"
                          checked={csvSelectedCol === colIdx}
                          onChange={() => setCsvSelectedCol(colIdx)}
                          className="accent-primary"
                        />
                        <span className="text-sm font-semibold">{csvHeaders[colIdx] || `Column ${colIdx + 1}`}</span>
                      </label>
                      <div className="space-y-1 max-h-[400px] overflow-y-auto">
                        {col.slice(0, 50).map((val, rowIdx) => (
                          <div key={rowIdx} className="py-2 px-3 text-sm border-b border-border/30 text-center">
                            {val}
                          </div>
                        ))}
                        {col.length > 50 && (
                          <p className="text-xs text-muted-foreground text-center py-2">...and {col.length - 50} more</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                // Single column: just list the values
                <div className="max-w-lg mx-auto rounded-lg border border-border overflow-hidden">
                  {(csvColumns[0] || []).slice(0, 100).map((val, i) => (
                    <div key={i} className="py-3 px-4 text-sm text-center border-b border-border/30 last:border-0">
                      {i === 0 && (
                        <span className="inline-flex items-center gap-2">
                          <input type="radio" checked readOnly className="accent-primary" />
                          <span className="font-medium">{val}</span>
                        </span>
                      )}
                      {i !== 0 && val}
                    </div>
                  ))}
                  {(csvColumns[0] || []).length > 100 && (
                    <p className="text-xs text-muted-foreground text-center py-3">...and {(csvColumns[0] || []).length - 100} more</p>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 p-6 border-t border-border">
            <Button variant="outline" size="lg" onClick={handleCsvClose}>Cancel</Button>
            <Button className="gradient-primary" size="lg" onClick={handleCsvNextStep}>Next</Button>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* CSV UPLOAD OVERLAY — Step 2: Keyword Preview */}
      {/* ================================================================ */}
      {csvStep === "preview" && (
        <div className="fixed top-0 right-0 bottom-0 z-50 bg-background flex flex-col transition-all duration-150" style={{ left: sidebarOpen ? '256px' : '64px' }}>
          <div className="flex items-center justify-between p-6 border-b border-border">
            <div className="flex items-center gap-3">
              <button
                className="h-10 w-10 rounded-full border border-border flex items-center justify-center hover:bg-muted"
                onClick={() => setCsvStep("select-column")}
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div>
                <h2 className="text-2xl font-bold">CSV Upload</h2>
                <p className="text-muted-foreground text-sm">Select the appropriate column which has all your keywords</p>
              </div>
            </div>
            <button onClick={handleCsvClose} className="h-8 w-8 flex items-center justify-center rounded-full hover:bg-muted">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="p-6 flex-1 overflow-hidden flex flex-col max-w-5xl mx-auto w-full">
            {/* Search + Remaining + Reset row */}
            <div className="flex items-center gap-4 mb-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  value={csvSearch}
                  onChange={(e) => setCsvSearch(e.target.value)}
                  placeholder="Search"
                  className="pl-9"
                />
              </div>
              <div className="flex-1" />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const col = csvColumns[csvSelectedCol] || [];
                  const unique = [...new Set(col.map(k => k.trim().toLowerCase()).filter(k => k.length > 0 && k.length <= 255))];
                  setCsvParsedKeywords(unique);
                  setCsvSearch("");
                }}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1" />
                Reset
              </Button>
            </div>

            {/* Keywords badges area */}
            <div className="flex-1 overflow-y-auto rounded-lg border border-border p-4">
              {filteredCsvKeywords.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {filteredCsvKeywords.map((kw, i) => (
                    <Badge
                      key={`${kw}-${i}`}
                      className="py-1.5 px-3 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 cursor-default"
                    >
                      {kw}
                      <button
                        className="ml-1.5 hover:opacity-70"
                        onClick={() => setCsvParsedKeywords(prev => prev.filter(k => k !== kw))}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  No keywords found
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 p-6 border-t border-border">
            <Button variant="outline" size="lg" onClick={handleCsvClose}>Cancel</Button>
            <Button
              className="gradient-primary"
              size="lg"
              onClick={handleCsvConfirm}
              disabled={csvParsedKeywords.length === 0}
            >
              Confirm
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddSeoKeyword;
