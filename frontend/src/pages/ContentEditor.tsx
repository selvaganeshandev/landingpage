import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import {
  ArrowLeft,
  Save,
  Eye,
  Share2,
  Settings,
  MoreVertical,
  Heading2,
  Bold,
  Italic,
  Underline,
  List,
  ListOrdered,
  Link,
  Image as ImageIcon,
  Table,
  Undo,
  Redo,
  AlignLeft,
  Sparkles
} from "lucide-react";
import { apiClient } from "@/services/api";

const ContentEditor = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const editorRef = useRef<HTMLDivElement>(null);

  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [contentData, setContentData] = useState<any>(null);

  // Content metrics
  const [wordCount, setWordCount] = useState(0);
  const [headingsCount, setHeadingsCount] = useState(0);
  const [paragraphsCount, setParagraphsCount] = useState(0);
  const [imagesCount, setImagesCount] = useState(0);
  const [contentScore, setContentScore] = useState(0);

  // Keywords tracking
  const [keywords, setKeywords] = useState<Array<{
    term: string;
    current: number;
    target: string;
    color: string;
  }>>([]);

  // Count keyword occurrences in text
  const countKeywordOccurrences = (text: string, keyword: string): number => {
    const regex = new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    const matches = text.match(regex);
    return matches ? matches.length : 0;
  };

  // Get color based on current vs target
  const getKeywordColor = (current: number, target: string): string => {
    const [min, max] = target.split('-').map(n => parseInt(n));
    if (current >= min && current <= max) {
      return "bg-green-500/20 text-green-700 border-green-500";
    } else if (current > 0 && current < min) {
      return "bg-yellow-500/20 text-yellow-700 border-yellow-500";
    } else {
      return "bg-red-500/20 text-red-700 border-red-500";
    }
  };

  // Load content
  useEffect(() => {
    const loadContent = async () => {
      if (!id) return;

      try {
        setLoading(true);
        const data = await apiClient.getGeneratedContent(parseInt(id));

        if (data) {
          setContentData(data);
          setTitle(data.title);

          const htmlContent = data.content_html || "";
          setContent(htmlContent);

          // Extract keywords and count occurrences
          if (data.keywords) {
            const keywordList = data.keywords.split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0);
            const contentText = data.content_html?.replace(/<[^>]*>/g, ' ').toLowerCase() || '';

            const keywordStats = keywordList.map((keyword: string) => {
              const count = countKeywordOccurrences(contentText, keyword);
              // Estimate target range based on word count (1-3 times per 500 words as baseline)
              const wordCount = contentText.split(/\s+/).filter((w: string) => w.length > 0).length;
              const targetMin = Math.max(1, Math.floor(wordCount / 500));
              const targetMax = Math.max(3, Math.floor(wordCount / 250));
              const target = `${targetMin}-${targetMax}`;

              return {
                term: keyword,
                current: count,
                target: `${count}/${target}`,
                color: getKeywordColor(count, target)
              };
            });

            setKeywords(keywordStats);
          }

          // Calculate initial metrics and content score
          updateMetrics(data.content_html || "");
        }
      } catch (error) {
        console.error("Error loading content:", error);
        toast({
          title: "Error",
          description: "Failed to load content",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [id, toast]);

  // Set the HTML content when it changes
  useEffect(() => {
    if (editorRef.current && content && editorRef.current.innerHTML !== content) {
      editorRef.current.innerHTML = content;
    }
  }, [content]);

  // Update content metrics
  const updateMetrics = (html: string) => {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // Word count
    const text = tempDiv.textContent || "";
    const words = text.trim().split(/\s+/).filter(w => w.length > 0);
    const wc = words.length;
    setWordCount(wc);

    // Headings count
    const h2Count = (html.match(/<h2/gi) || []).length;
    const h3Count = (html.match(/<h3/gi) || []).length;
    const hc = h2Count + h3Count;
    setHeadingsCount(hc);

    // Paragraphs count
    const pCount = (html.match(/<p/gi) || []).length;
    setParagraphsCount(pCount);

    // Images count
    const imgCount = (html.match(/<img/gi) || []).length;
    setImagesCount(imgCount);

    // Calculate content score (0-100)
    let score = 0;

    // Word count score (30 points max) - ideal range: 1500-2500 words
    if (wc >= 1500 && wc <= 2500) {
      score += 30;
    } else if (wc >= 1000 && wc < 1500) {
      score += 20;
    } else if (wc >= 800 && wc < 1000) {
      score += 15;
    } else if (wc > 2500 && wc <= 3500) {
      score += 25;
    } else if (wc > 500) {
      score += 10;
    }

    // Headings score (20 points max) - ideal: 1 heading per 200-300 words
    const idealHeadings = Math.floor(wc / 250);
    if (hc >= idealHeadings - 2 && hc <= idealHeadings + 2) {
      score += 20;
    } else if (hc >= idealHeadings - 5 && hc <= idealHeadings + 5) {
      score += 15;
    } else if (hc > 0) {
      score += 10;
    }

    // Paragraphs score (15 points max) - should have good paragraph structure
    if (pCount >= 5) {
      score += 15;
    } else if (pCount >= 3) {
      score += 10;
    } else if (pCount > 0) {
      score += 5;
    }

    // Images score (10 points max)
    if (imgCount >= 2) {
      score += 10;
    } else if (imgCount >= 1) {
      score += 5;
    }

    // Keyword usage score (25 points max)
    if (keywords.length > 0) {
      const keywordsMeetingTarget = keywords.filter(k =>
        k.color === "bg-green-500/20 text-green-700 border-green-500"
      ).length;
      const keywordScore = (keywordsMeetingTarget / keywords.length) * 25;
      score += Math.round(keywordScore);
    } else {
      score += 15; // Give some points if no keywords defined yet
    }

    setContentScore(Math.min(100, Math.round(score)));
  };

  // Handle content changes
  const handleContentChange = () => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      setContent(html);
      updateMetrics(html);
    }
  };

  // Formatting functions
  const execCommand = (command: string, value?: string) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
  };

  // Save content
  const handleSave = async () => {
    if (!id) return;

    try {
      setSaving(true);

      await apiClient.updateGeneratedContent(parseInt(id), {
        title,
        content_html: content
      });

      toast({
        title: "Success",
        description: "Content saved successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save content",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading content...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/content-calendar")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Content Editor /</span>
              <span className="text-sm font-medium truncate max-w-md">{title || "Loading..."}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button variant="outline" size="sm">
              <Eye className="h-4 w-4 mr-2" />
              Preview
            </Button>
            <Button variant="default" size="sm">
              <Share2 className="h-4 w-4 mr-2" />
              Export
            </Button>
            <Button variant="default" size="sm">
              <Sparkles className="h-4 w-4 mr-2" />
              Repurpose
            </Button>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Toolbar */}
          <div className="border-b border-border bg-card p-3">
            <div className="flex items-center gap-1 flex-wrap">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('formatBlock', '<h2>')}
                title="Heading 2"
              >
                H2
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('bold')}
                title="Bold"
              >
                <Bold className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('italic')}
                title="Italic"
              >
                <Italic className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('underline')}
                title="Underline"
              >
                <Underline className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('insertUnorderedList')}
                title="Bullet List"
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('insertOrderedList')}
                title="Numbered List"
              >
                <ListOrdered className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('justifyLeft')}
                title="Align Left"
              >
                <AlignLeft className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const url = prompt('Enter URL:');
                  if (url) execCommand('createLink', url);
                }}
                title="Insert Link"
              >
                <Link className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                title="Insert Image"
              >
                <ImageIcon className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                title="Insert Table"
              >
                <Table className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('undo')}
                title="Undo"
              >
                <Undo className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('redo')}
                title="Redo"
              >
                <Redo className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              <Button variant="ghost" size="sm">
                <Sparkles className="h-4 w-4 mr-2" />
                AI Assistant
              </Button>
            </div>
          </div>

          {/* Content Editor */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              {/* Rich Text Editor */}
              <div
                ref={editorRef}
                contentEditable
                onInput={handleContentChange}
                className="prose prose-lg prose-slate max-w-none min-h-[600px] focus:outline-none"
                style={{
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  fontSize: '16px',
                  lineHeight: '1.75',
                  color: 'hsl(var(--foreground))'
                }}
                suppressContentEditableWarning
              />
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="w-80 border-l border-border bg-card overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Content Score */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Content Score</h3>
                <Button variant="ghost" size="sm">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>

              <div className="relative flex items-center justify-center mb-4">
                <div className="relative w-32 h-32">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="hsl(var(--muted))"
                      strokeWidth="12"
                      fill="none"
                    />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke={contentScore >= 70 ? "#22c55e" : contentScore >= 50 ? "#f59e0b" : "#ef4444"}
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${(contentScore / 100) * 351.86} 351.86`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-3xl font-bold">{contentScore}</div>
                      <div className="text-xs text-muted-foreground">/100</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Avg <span className="font-medium">72</span></span>
                <span className="text-muted-foreground">Top <span className="font-medium">85</span></span>
              </div>

              <Button className="w-full mt-4" variant="default">
                <Sparkles className="h-4 w-4 mr-2" />
                Auto-Optimize
              </Button>
            </div>

            <Separator />

            {/* Content Structure */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Content Structure</h3>
                <Button variant="ghost" size="sm">
                  Adjust
                </Button>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-sm text-muted-foreground mb-1">WORDS</div>
                  <div className="text-lg font-bold">{wordCount}</div>
                  <div className={`text-xs ${contentData?.word_count ? (wordCount >= contentData.word_count * 0.9 && wordCount <= contentData.word_count * 1.1 ? 'text-success' : 'text-warning') : 'text-muted-foreground'}`}>
                    {contentData?.word_count ? `${Math.floor(contentData.word_count * 0.9)}-${Math.ceil(contentData.word_count * 1.1)}` : 'No target'}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground mb-1">HEADINGS</div>
                  <div className="text-lg font-bold">{headingsCount}</div>
                  <div className={`text-xs ${wordCount > 0 ? (headingsCount >= Math.floor(wordCount / 300) && headingsCount <= Math.ceil(wordCount / 150) ? 'text-success' : 'text-warning') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `${Math.floor(wordCount / 300)}-${Math.ceil(wordCount / 150)}` : 'No target'}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground mb-1">PARAGRAPHS</div>
                  <div className="text-lg font-bold">{paragraphsCount}</div>
                  <div className={`text-xs ${wordCount > 0 ? (paragraphsCount >= Math.floor(wordCount / 150) ? 'text-success' : 'text-warning') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `at least ${Math.floor(wordCount / 150)}` : 'No target'}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-sm text-muted-foreground mb-1">IMAGES</div>
                  <div className="text-lg font-bold">{imagesCount}</div>
                  <div className={`text-xs ${wordCount > 0 ? (imagesCount >= 1 ? 'text-success' : 'text-warning') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `${Math.floor(wordCount / 500)}-${Math.ceil(wordCount / 200)}` : 'No target'}
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Terms */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Terms</h3>
                <Button variant="ghost" size="sm">
                  Adjust
                </Button>
              </div>

              <div className="flex gap-2 mb-4">
                <Button variant="secondary" size="sm" className="text-xs">
                  All <Badge variant="secondary" className="ml-1">80</Badge>
                </Button>
                <Button variant="outline" size="sm" className="text-xs">
                  Headings <Badge variant="secondary" className="ml-1">3</Badge>
                </Button>
                <Button variant="outline" size="sm" className="text-xs">
                  NLP <Badge variant="secondary" className="ml-1">31</Badge>
                </Button>
              </div>

              <div className="space-y-2">
                {keywords.map((keyword, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <Badge variant="outline" className={`${keyword.color} text-xs px-2 py-1 border`}>
                      {keyword.term}
                    </Badge>
                    <span className="text-xs text-muted-foreground">{keyword.target}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContentEditor;
