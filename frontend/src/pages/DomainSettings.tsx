import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import {
  ArrowLeft,
  Plus,
  Globe,
  Loader2,
  X,
  Upload,
  FileText,
  Palette,
  Link2,
  Info,
} from "lucide-react";

export default function DomainSettings() {
  const { domainId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Domain state
  const [domain, setDomain] = useState<{
    id: number;
    name: string;
    url: string;
    organisation: number;
    total_mentions: number;
    total_citations: number;
    visibility_score: string;
    average_position: string;
    active_alerts: number;
    sentiment: string;
    sentiment_score: string;
    created_at: string;
    modified_at: string;
    processing_status?: string;
    track_message?: string;
  } | null>(null);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Keywords state for Add Keywords dialog
  const [newKeywordsInput, setNewKeywordsInput] = useState("");
  const [newKeywordsList, setNewKeywordsList] = useState<string[]>([]);
  const [isAddingKeywords, setIsAddingKeywords] = useState(false);
  const [showAddKeywords, setShowAddKeywords] = useState(false);

  const MAX_KEYWORD_LENGTH = 255;

  // Load domain data
  useEffect(() => {
    if (domainId) {
      loadDomainData();
    }
  }, [domainId]);

  const loadDomainData = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getDomains();
      const foundDomain = data.domains.find((d: any) => d.id === parseInt(domainId!));

      if (!foundDomain) {
        toast({
          title: "Domain not found",
          description: "The requested domain could not be found.",
          variant: "destructive",
        });
        navigate("/organization-settings");
        return;
      }

      setDomain(foundDomain);
    } catch (error: any) {
      toast({
        title: "Error loading domain",
        description: error.message || "Failed to load domain information.",
        variant: "destructive",
      });
      navigate("/organization-settings");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddKeywordToList = () => {
    const trimmedInput = newKeywordsInput.trim();
    if (!trimmedInput) return;

    const newKeywords = trimmedInput
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(k => {
        if (k.length === 0) return false;
        if (k.length > MAX_KEYWORD_LENGTH) {
          toast({
            title: "Keyword too long",
            description: `"${k}" exceeds ${MAX_KEYWORD_LENGTH} characters.`,
            variant: "destructive",
          });
          return false;
        }
        return true;
      })
      .filter(k => !newKeywordsList.includes(k));

    if (newKeywords.length > 0) {
      setNewKeywordsList([...newKeywordsList, ...newKeywords]);
      setNewKeywordsInput("");
    }
  };

  const handleRemoveKeywordFromList = (keyword: string) => {
    setNewKeywordsList(newKeywordsList.filter(k => k !== keyword));
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const fileName = file.name.toLowerCase();
    const isCSV = fileName.endsWith('.csv');
    const isXLSX = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');

    if (!isCSV && !isXLSX) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV or XLSX file.",
        variant: "destructive",
      });
      return;
    }

    try {
      let keywords: string[] = [];

      if (isCSV) {
        const text = await file.text();
        const lines = text.split(/\r?\n/);
        for (const line of lines) {
          if (!line.trim()) continue;
          const values: string[] = [];
          let current = '';
          let inQuotes = false;

          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
              values.push(current.trim());
              current = '';
            } else {
              current += char;
            }
          }
          values.push(current.trim());

          for (const value of values) {
            const cleaned = value.replace(/^"|"$/g, '').trim().toLowerCase();
            if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
              keywords.push(cleaned);
            }
          }
        }
      } else if (isXLSX) {
        try {
          const XLSX = await import('xlsx');
          const arrayBuffer = await file.arrayBuffer();
          const workbook = XLSX.read(arrayBuffer, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const data = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });

          for (const row of data) {
            if (Array.isArray(row)) {
              for (const cell of row) {
                if (cell && typeof cell === 'string') {
                  const cleaned = cell.trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                } else if (typeof cell === 'number') {
                  const cleaned = String(cell).trim().toLowerCase();
                  if (cleaned && cleaned.length <= MAX_KEYWORD_LENGTH) {
                    keywords.push(cleaned);
                  }
                }
              }
            }
          }
        } catch (xlsxError: any) {
          toast({
            title: "XLSX parsing error",
            description: xlsxError?.message || "Failed to parse XLSX file.",
            variant: "destructive",
          });
          return;
        }
      }

      const uniqueKeywords = [...new Set(keywords.filter(k => k.length > 0))];
      const newKeywords = uniqueKeywords.filter(k => !newKeywordsList.includes(k));

      if (newKeywords.length === 0) {
        toast({
          title: "No new keywords",
          description: "All keywords from the file are already added or the file is empty.",
          variant: "default",
        });
        return;
      }

      setNewKeywordsList([...newKeywordsList, ...newKeywords]);

      toast({
        title: "Keywords uploaded",
        description: `Added ${newKeywords.length} keyword(s) from ${file.name}`,
        variant: "default",
      });
    } catch (error: any) {
      toast({
        title: "Upload error",
        description: error.message || "Failed to process the file.",
        variant: "destructive",
      });
    } finally {
      event.target.value = '';
    }
  };

  const handleAddKeywordsToDomain = async () => {
    if (!domain || newKeywordsList.length === 0) {
      toast({
        title: "Keywords required",
        description: "Please add at least one keyword.",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsAddingKeywords(true);

      let successCount = 0;
      let errorCount = 0;

      for (const keywordText of newKeywordsList) {
        try {
          await apiClient.createKeyword({
            keyword: keywordText,
            domain: domain.id,
          });
          successCount++;
        } catch (error: any) {
          errorCount++;
          console.error(`Failed to add keyword "${keywordText}":`, error);
        }
      }

      setNewKeywordsInput("");
      setNewKeywordsList([]);
      setShowAddKeywords(false);

      if (errorCount === 0) {
        toast({
          title: "Keywords added successfully!",
          description: `Added ${successCount} keyword(s) to ${domain.name}.`,
        });
      } else {
        toast({
          title: "Partially successful",
          description: `Added ${successCount} keyword(s), ${errorCount} failed (may already exist).`,
          variant: "default",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error adding keywords",
        description: error.message || "Failed to add keywords.",
        variant: "destructive",
      });
    } finally {
      setIsAddingKeywords(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading domain settings...</span>
        </div>
      </div>
    );
  }

  if (!domain) {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto text-center">
          <h1 className="text-2xl font-bold mb-4">Domain Not Found</h1>
          <Button onClick={() => navigate("/organization-settings")}>
            Back to Organization Settings
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 bg-background animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/organization-settings")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-3">
            <img
              src={`https://www.google.com/s2/favicons?domain=${domain.url}&sz=32`}
              alt={`${domain.name} favicon`}
              className="h-8 w-8 rounded"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            <div>
              <h1 className="text-3xl font-bold capitalize">{domain.name}</h1>
              <p className="text-muted-foreground">
                Configure settings for {domain.url}
              </p>
            </div>
          </div>
        </div>
        <Button onClick={() => setShowAddKeywords(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Keywords
        </Button>
      </div>

      {/* Add Keywords Section (Collapsible) */}
      {showAddKeywords && (
        <Card className="border border-border">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Add Keywords</CardTitle>
                <CardDescription>
                  Add additional keywords to track for this domain
                </CardDescription>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setShowAddKeywords(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div
                className="flex flex-wrap gap-2 min-h-[100px] max-h-[200px] overflow-y-auto p-3 border border-input rounded-md bg-background text-sm"
              >
                {newKeywordsList.map((keyword, index) => (
                  <Badge
                    key={index}
                    variant="default"
                    className="gap-1 pr-1 h-7"
                  >
                    {keyword}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-4 w-4 p-0 hover:bg-background/20"
                      onClick={() => handleRemoveKeywordFromList(keyword)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </Badge>
                ))}
                <Input
                  type="text"
                  placeholder={newKeywordsList.length === 0 ? "Enter keywords and press Enter" : "Add more..."}
                  value={newKeywordsInput}
                  onChange={(e) => setNewKeywordsInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === ",") {
                      e.preventDefault();
                      handleAddKeywordToList();
                    }
                  }}
                  className="flex-1 min-w-[200px] border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0 h-7"
                />
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="keyword-file-upload-domain"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0"
                  onClick={() => document.getElementById('keyword-file-upload-domain')?.click()}
                  title="Upload keywords from CSV or XLSX"
                >
                  <Upload className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Type keywords and press Enter, or upload CSV/XLSX files.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => {
                setShowAddKeywords(false);
                setNewKeywordsList([]);
                setNewKeywordsInput("");
              }}>
                Cancel
              </Button>
              <Button onClick={handleAddKeywordsToDomain} disabled={isAddingKeywords || newKeywordsList.length === 0}>
                {isAddingKeywords ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Adding...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Keywords
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="basic-info" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic-info" className="gap-2">
            <Info className="h-4 w-4" />
            Basic Info
          </TabsTrigger>
          <TabsTrigger value="content-guidelines" className="gap-2">
            <FileText className="h-4 w-4" />
            Content Guidelines
          </TabsTrigger>
          <TabsTrigger value="brand-identity" className="gap-2">
            <Palette className="h-4 w-4" />
            Brand Identity
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-2">
            <Link2 className="h-4 w-4" />
            Integrations
          </TabsTrigger>
        </TabsList>

        {/* Basic Info Tab */}
        <TabsContent value="basic-info" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>
                View and manage the basic details of your domain
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="domain-name">Domain Name</Label>
                  <Input
                    id="domain-name"
                    value={domain.name}
                    disabled
                    className="bg-muted"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="domain-url">Domain URL</Label>
                  <Input
                    id="domain-url"
                    value={domain.url}
                    disabled
                    className="bg-muted"
                  />
                </div>
              </div>
              <Separator />
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 border rounded-lg text-center">
                  <p className="text-2xl font-bold">{domain.total_mentions || 0}</p>
                  <p className="text-sm text-muted-foreground">Total Mentions</p>
                </div>
                <div className="p-4 border rounded-lg text-center">
                  <p className="text-2xl font-bold">{domain.total_citations || 0}</p>
                  <p className="text-sm text-muted-foreground">Total Citations</p>
                </div>
                <div className="p-4 border rounded-lg text-center">
                  <p className="text-2xl font-bold">{domain.visibility_score || '0'}%</p>
                  <p className="text-sm text-muted-foreground">Visibility Score</p>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">
                <p>Created: {new Date(domain.created_at).toLocaleDateString()}</p>
                <p>Last Modified: {new Date(domain.modified_at).toLocaleDateString()}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Content Guidelines Tab */}
        <TabsContent value="content-guidelines" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Content Guidelines</CardTitle>
              <CardDescription>
                Define content guidelines and tone of voice for AI-generated content
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tone-of-voice">Tone of Voice</Label>
                <Textarea
                  id="tone-of-voice"
                  placeholder="Describe your brand's tone of voice (e.g., professional, friendly, authoritative...)"
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="content-style">Content Style</Label>
                <Textarea
                  id="content-style"
                  placeholder="Describe your preferred content style (e.g., concise, detailed, technical...)"
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="key-messages">Key Messages</Label>
                <Textarea
                  id="key-messages"
                  placeholder="List key messages or themes to emphasize in content..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="avoid-topics">Topics to Avoid</Label>
                <Textarea
                  id="avoid-topics"
                  placeholder="List topics or themes to avoid in content..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="flex justify-end">
                <Button disabled>
                  <Loader2 className="h-4 w-4 mr-2 hidden" />
                  Save Guidelines
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Brand Identity Tab */}
        <TabsContent value="brand-identity" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Brand Identity</CardTitle>
              <CardDescription>
                Configure your brand's visual identity and assets
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="brand-description">Brand Description</Label>
                <Textarea
                  id="brand-description"
                  placeholder="Provide a brief description of your brand..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target-audience">Target Audience</Label>
                <Textarea
                  id="target-audience"
                  placeholder="Describe your target audience demographics and preferences..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="brand-values">Brand Values</Label>
                <Textarea
                  id="brand-values"
                  placeholder="List your brand's core values..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="competitors-brand">Key Competitors</Label>
                <Textarea
                  id="competitors-brand"
                  placeholder="List your main competitors..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="flex justify-end">
                <Button disabled>
                  Save Brand Identity
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Integrations</CardTitle>
              <CardDescription>
                Connect external services and data sources
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
                      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium">Google Analytics</p>
                      <p className="text-sm text-muted-foreground">Track website traffic and user behavior</p>
                    </div>
                  </div>
                  <Button variant="outline" disabled>Connect</Button>
                </div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-green-100 flex items-center justify-center">
                      <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium">Google Search Console</p>
                      <p className="text-sm text-muted-foreground">Monitor search performance and queries</p>
                    </div>
                  </div>
                  <Button variant="outline" disabled>Connect</Button>
                </div>
              </div>
              <div className="text-sm text-muted-foreground text-center py-4">
                More integrations coming soon...
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
