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
  Bold,
  Italic,
  Underline,
  Strikethrough,
  List,
  ListOrdered,
  Link,
  Image as ImageIcon,
  Table,
  Undo,
  Redo,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Quote,
  Code,
  Sparkles,
  ChevronDown
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/services/api";

const ContentEditor = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const editorRef = useRef<HTMLDivElement>(null);
  const isInitialLoad = useRef(true);

  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [contentData, setContentData] = useState<any>(null);

  // Image modal state
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [imageAlt, setImageAlt] = useState("");

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
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const originalContentRef = useRef<string>("");

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
      // Success - using theme success color
      return "bg-success/10 text-success border-success/50";
    } else if (current > 0 && current < min) {
      // Warning - using theme warning color
      return "bg-warning/10 text-warning border-warning/50";
    } else {
      // Destructive/Error - using theme destructive color
      return "bg-destructive/10 text-destructive border-destructive/50";
    }
  };

  // Highlight keyword in editor
  const highlightKeywordInEditor = (keyword: string | null) => {
    if (!editorRef.current) return;

    // If no keyword selected, restore original content
    if (!keyword) {
      if (originalContentRef.current) {
        editorRef.current.innerHTML = originalContentRef.current;
      }
      return;
    }

    // Store original content if not already stored
    if (!originalContentRef.current) {
      originalContentRef.current = editorRef.current.innerHTML;
    } else {
      // Restore original before applying new highlight
      editorRef.current.innerHTML = originalContentRef.current;
    }

    // Create a TreeWalker to find text nodes
    const walker = document.createTreeWalker(
      editorRef.current,
      NodeFilter.SHOW_TEXT,
      null
    );

    const textNodes: Text[] = [];
    let node;
    while ((node = walker.nextNode())) {
      textNodes.push(node as Text);
    }

    // Highlight keyword in each text node
    const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');

    textNodes.forEach((textNode) => {
      const text = textNode.textContent || '';
      if (regex.test(text)) {
        const span = document.createElement('span');
        span.innerHTML = text.replace(regex, '<mark class="keyword-highlight">$1</mark>');
        textNode.parentNode?.replaceChild(span, textNode);
      }
    });
  };

  // Handle keyword selection
  const handleKeywordClick = (keyword: string) => {
    if (selectedKeyword === keyword) {
      // Deselect if clicking the same keyword
      setSelectedKeyword(null);
      highlightKeywordInEditor(null);
    } else {
      setSelectedKeyword(keyword);
      highlightKeywordInEditor(keyword);
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
          // API returns {status: 'success', data: {...}}
          const contentRecord = data.data || data;

          setContentData(contentRecord);
          setTitle(contentRecord.title);

          const htmlContent = contentRecord.content_html || "";
          setContent(htmlContent);

          // Extract keywords and count occurrences
          let keywordStats: typeof keywords = [];
          if (contentRecord.keywords) {
            const keywordList = contentRecord.keywords.split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0);
            const contentText = contentRecord.content_html?.replace(/<[^>]*>/g, ' ').toLowerCase() || '';

            keywordStats = keywordList.map((keyword: string) => {
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

          // Calculate initial metrics and content score with keywords
          updateMetrics(contentRecord.content_html || "", keywordStats);
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

  // Set the HTML content only on initial load
  useEffect(() => {
    if (editorRef.current && content && !loading && isInitialLoad.current) {
      // Use a small delay to ensure the contentEditable div is fully ready
      const timeoutId = setTimeout(() => {
        if (editorRef.current) {
          editorRef.current.innerHTML = content;
          originalContentRef.current = content; // Store original content for keyword highlighting
          isInitialLoad.current = false;
        }
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [content, loading]);

  // Update content metrics
  const updateMetrics = (html: string, keywordsList?: typeof keywords) => {
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
    // Use passed keywordsList if available, otherwise use state
    const kw = keywordsList || keywords;
    if (kw.length > 0) {
      const keywordsMeetingTarget = kw.filter(k =>
        k.color === "bg-success/10 text-success border-success/50"
      ).length;
      const keywordScore = (keywordsMeetingTarget / kw.length) * 25;
      score += Math.round(keywordScore);
      console.log("Keywords meeting target:", keywordsMeetingTarget, "/", kw.length, "Score added:", Math.round(keywordScore));
    } else {
      score += 15; // Give some points if no keywords defined yet
    }

    console.log("Final content score:", Math.min(100, Math.round(score)), "Word count:", wc, "Headings:", hc, "Paragraphs:", pCount, "Images:", imgCount);
    setContentScore(Math.min(100, Math.round(score)));
  };

  // Handle content changes
  const handleContentChange = () => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      setContent(html);

      // Recalculate keyword stats based on new content
      const contentText = html.replace(/<[^>]*>/g, ' ').toLowerCase();
      const wordCount = contentText.split(/\s+/).filter((w: string) => w.length > 0).length;

      const updatedKeywords = keywords.map(kw => {
        const count = countKeywordOccurrences(contentText, kw.term);
        const targetMin = Math.max(1, Math.floor(wordCount / 500));
        const targetMax = Math.max(3, Math.floor(wordCount / 250));
        const target = `${targetMin}-${targetMax}`;

        return {
          ...kw,
          current: count,
          target: `${count}/${target}`,
          color: getKeywordColor(count, target)
        };
      });

      setKeywords(updatedKeywords);
      updateMetrics(html, updatedKeywords);

      // Update original content ref when user edits (only if no keyword is selected)
      if (!selectedKeyword) {
        originalContentRef.current = html;
      }
    }
  };

  // Formatting functions
  const execCommand = (command: string, value?: string) => {
    // Ensure editor has focus before executing command
    editorRef.current?.focus();
    document.execCommand(command, false, value);
    // Update content state after command
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      setContent(html);
      updateMetrics(html);
    }
  };

  // Handle image insertion
  const handleInsertImage = () => {
    if (imageUrl) {
      const imgHtml = `<img src="${imageUrl}" alt="${imageAlt || 'Image'}" style="max-width: 100%; height: auto;" />`;
      editorRef.current?.focus();
      document.execCommand('insertHTML', false, imgHtml);
      // Update content state
      if (editorRef.current) {
        const html = editorRef.current.innerHTML;
        setContent(html);
        updateMetrics(html);
      }
    }
    setImageModalOpen(false);
    setImageUrl("");
    setImageAlt("");
  };

  // Save content
  const handleSave = async () => {
    if (!id) return;

    try {
      setSaving(true);

      // Get the latest content directly from the editor
      const currentContent = editorRef.current?.innerHTML || content;

      await apiClient.updateGeneratedContent(parseInt(id), {
        title,
        content_html: currentContent
      });

      // Update the content state with the saved content
      setContent(currentContent);

      toast({
        title: "Success",
        description: "Content saved successfully",
      });
    } catch (error) {
      console.error("Error saving content:", error);
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
            <Button variant="default" size="sm">
              <Share2 className="h-4 w-4 mr-2" />
              Export
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
              {/* Heading Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="gap-1">
                    Heading
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => execCommand('formatBlock', '<p>')}>
                    <span className="text-sm">Normal Text</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('formatBlock', '<h2>')}>
                    <span className="text-lg font-semibold">Heading 2</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('formatBlock', '<h3>')}>
                    <span className="text-base font-semibold">Heading 3</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('formatBlock', '<h4>')}>
                    <span className="text-sm font-semibold">Heading 4</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('formatBlock', '<h5>')}>
                    <span className="text-xs font-semibold">Heading 5</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Text Formatting */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('bold')}
                title="Bold (Ctrl+B)"
              >
                <Bold className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('italic')}
                title="Italic (Ctrl+I)"
              >
                <Italic className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('underline')}
                title="Underline (Ctrl+U)"
              >
                <Underline className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('strikeThrough')}
                title="Strikethrough"
              >
                <Strikethrough className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Lists */}
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
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Alignment */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('justifyLeft')}
                title="Align Left"
              >
                <AlignLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('justifyCenter')}
                title="Align Center"
              >
                <AlignCenter className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('justifyRight')}
                title="Align Right"
              >
                <AlignRight className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Block Elements */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('formatBlock', '<blockquote>')}
                title="Blockquote"
              >
                <Quote className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const selection = window.getSelection();
                  if (selection && selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const code = document.createElement('code');
                    code.appendChild(range.extractContents());
                    range.insertNode(code);
                  }
                }}
                title="Inline Code"
              >
                <Code className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Insert Elements */}
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
                onClick={() => setImageModalOpen(true)}
                title="Insert Image"
              >
                <ImageIcon className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const rows = prompt('Number of rows:', '3');
                  const cols = prompt('Number of columns:', '3');
                  if (rows && cols) {
                    const numRows = parseInt(rows);
                    const numCols = parseInt(cols);
                    let tableHtml = '<table><thead><tr>';
                    for (let c = 0; c < numCols; c++) {
                      tableHtml += '<th>Header ' + (c + 1) + '</th>';
                    }
                    tableHtml += '</tr></thead><tbody>';
                    for (let r = 0; r < numRows - 1; r++) {
                      tableHtml += '<tr>';
                      for (let c = 0; c < numCols; c++) {
                        tableHtml += '<td>Cell</td>';
                      }
                      tableHtml += '</tr>';
                    }
                    tableHtml += '</tbody></table>';
                    execCommand('insertHTML', tableHtml);
                  }
                }}
                title="Insert Table"
              >
                <Table className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Undo/Redo */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('undo')}
                title="Undo (Ctrl+Z)"
              >
                <Undo className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('redo')}
                title="Redo (Ctrl+Y)"
              >
                <Redo className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Content Editor */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              {/* Rich Text Editor */}
              <style>{`
                .content-editor h1 {
                  font-size: 2.25rem;
                  font-weight: 700;
                  margin-top: 2rem;
                  margin-bottom: 1rem;
                  line-height: 1.2;
                  color: hsl(var(--foreground));
                }
                .content-editor h2 {
                  font-size: 1.75rem;
                  font-weight: 600;
                  margin-top: 1.75rem;
                  margin-bottom: 0.75rem;
                  line-height: 1.3;
                  color: hsl(var(--foreground));
                  border-bottom: 1px solid hsl(var(--border));
                  padding-bottom: 0.5rem;
                }
                .content-editor h3 {
                  font-size: 1.35rem;
                  font-weight: 600;
                  margin-top: 1.5rem;
                  margin-bottom: 0.5rem;
                  line-height: 1.4;
                  color: hsl(var(--foreground));
                }
                .content-editor h4 {
                  font-size: 1.15rem;
                  font-weight: 600;
                  margin-top: 1.25rem;
                  margin-bottom: 0.5rem;
                  color: hsl(var(--foreground));
                }
                .content-editor h5 {
                  font-size: 1rem;
                  font-weight: 600;
                  margin-top: 1rem;
                  margin-bottom: 0.5rem;
                  color: hsl(var(--foreground));
                }
                .content-editor p {
                  margin-bottom: 1rem;
                  line-height: 1.75;
                }
                .content-editor strong, .content-editor b {
                  font-weight: 700;
                }
                .content-editor em, .content-editor i {
                  font-style: italic;
                }
                .content-editor u {
                  text-decoration: underline;
                }
                .content-editor s, .content-editor strike {
                  text-decoration: line-through;
                }
                .content-editor ul {
                  list-style-type: disc;
                  margin-left: 1.5rem;
                  margin-bottom: 1rem;
                }
                .content-editor ol {
                  list-style-type: decimal;
                  margin-left: 1.5rem;
                  margin-bottom: 1rem;
                }
                .content-editor li {
                  margin-bottom: 0.5rem;
                  line-height: 1.6;
                }
                .content-editor a {
                  color: hsl(var(--primary));
                  text-decoration: underline;
                }
                .content-editor blockquote {
                  border-left: 4px solid hsl(var(--primary));
                  padding-left: 1rem;
                  margin: 1rem 0;
                  font-style: italic;
                  color: hsl(var(--muted-foreground));
                }
                .content-editor code {
                  background: hsl(var(--muted));
                  padding: 0.2rem 0.4rem;
                  border-radius: 0.25rem;
                  font-family: monospace;
                  font-size: 0.9em;
                }
                .content-editor pre {
                  background: hsl(var(--muted));
                  padding: 1rem;
                  border-radius: 0.5rem;
                  overflow-x: auto;
                  margin: 1rem 0;
                }
                .content-editor table {
                  width: 100%;
                  border-collapse: collapse;
                  margin: 1rem 0;
                }
                .content-editor th, .content-editor td {
                  border: 1px solid hsl(var(--border));
                  padding: 0.5rem;
                  text-align: left;
                }
                .content-editor th {
                  background: hsl(var(--muted));
                  font-weight: 600;
                }
                .content-editor:focus {
                  outline: none;
                  caret-color: hsl(var(--foreground));
                }
                .content-editor .keyword-highlight,
                .content-editor mark.keyword-highlight {
                  background: hsl(var(--primary) / 0.3);
                  color: inherit;
                  padding: 0.1rem 0.2rem;
                  border-radius: 0.25rem;
                  border-bottom: 2px solid hsl(var(--primary));
                }
              `}</style>
              <div
                ref={editorRef}
                contentEditable
                onInput={handleContentChange}
                className="content-editor min-h-[600px] focus:outline-none"
                style={{
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  fontSize: '16px',
                  lineHeight: '1.75',
                  color: 'hsl(var(--foreground))',
                  caretColor: 'hsl(var(--foreground))',
                  cursor: 'text'
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
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Content Structure</h3>
              </div>

              <div className="grid grid-cols-4 gap-1.5">
                <div className="bg-muted/30 rounded-md p-1.5 text-center">
                  <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Words</div>
                  <div className="text-sm font-bold leading-tight">{wordCount}</div>
                  <div className={`text-[9px] leading-tight ${contentData?.word_count ? (wordCount >= contentData.word_count * 0.9 && wordCount <= contentData.word_count * 1.1 ? 'text-green-600' : 'text-amber-600') : 'text-muted-foreground'}`}>
                    {contentData?.word_count ? `${Math.floor(contentData.word_count * 0.9)}-${Math.ceil(contentData.word_count * 1.1)}` : '—'}
                  </div>
                </div>
                <div className="bg-muted/30 rounded-md p-1.5 text-center">
                  <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Heads</div>
                  <div className="text-sm font-bold leading-tight">{headingsCount}</div>
                  <div className={`text-[9px] leading-tight ${wordCount > 0 ? (headingsCount >= Math.floor(wordCount / 300) && headingsCount <= Math.ceil(wordCount / 150) ? 'text-green-600' : 'text-amber-600') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `${Math.floor(wordCount / 300)}-${Math.ceil(wordCount / 150)}` : '—'}
                  </div>
                </div>
                <div className="bg-muted/30 rounded-md p-1.5 text-center">
                  <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Paras</div>
                  <div className="text-sm font-bold leading-tight">{paragraphsCount}</div>
                  <div className={`text-[9px] leading-tight ${wordCount > 0 ? (paragraphsCount >= Math.floor(wordCount / 150) ? 'text-green-600' : 'text-amber-600') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `≥${Math.floor(wordCount / 150)}` : '—'}
                  </div>
                </div>
                <div className="bg-muted/30 rounded-md p-1.5 text-center">
                  <div className="text-[9px] uppercase tracking-wider text-muted-foreground">Imgs</div>
                  <div className="text-sm font-bold leading-tight">{imagesCount}</div>
                  <div className={`text-[9px] leading-tight ${wordCount > 0 ? (imagesCount >= 1 ? 'text-green-600' : 'text-amber-600') : 'text-muted-foreground'}`}>
                    {wordCount > 0 ? `${Math.floor(wordCount / 500)}-${Math.ceil(wordCount / 200)}` : '—'}
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* Terms */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Terms</h3>
                <span className="text-[10px] text-muted-foreground">{keywords.length} keywords</span>
              </div>

              <div className="flex flex-wrap gap-1.5 mb-3">
                <Button variant="secondary" size="sm" className="h-6 text-[10px] px-2">
                  All <Badge variant="secondary" className="ml-1 h-4 text-[10px] px-1">{keywords.length}</Badge>
                </Button>
                <Button variant="outline" size="sm" className="h-6 text-[10px] px-2">
                  Used <Badge variant="secondary" className="ml-1 h-4 text-[10px] px-1">{keywords.filter(k => k.current > 0).length}</Badge>
                </Button>
                <Button variant="outline" size="sm" className="h-6 text-[10px] px-2">
                  Missing <Badge variant="secondary" className="ml-1 h-4 text-[10px] px-1">{keywords.filter(k => k.current === 0).length}</Badge>
                </Button>
              </div>

              {/* Tag Cloud */}
              <div className="flex flex-wrap gap-1.5">
                {keywords.map((keyword, index) => (
                  <span
                    key={index}
                    onClick={() => handleKeywordClick(keyword.term)}
                    className={`inline-flex items-center px-2 py-0.5 rounded-full border cursor-pointer transition-all hover:scale-105 text-[11px] ${
                      selectedKeyword === keyword.term
                        ? 'bg-primary text-primary-foreground border-primary ring-2 ring-primary/30'
                        : keyword.color
                    }`}
                    title={`${keyword.term}: ${keyword.current} uses (target: ${keyword.target}) - Click to highlight`}
                  >
                    {keyword.term}
                    <span className="ml-1 opacity-70">{keyword.current}</span>
                  </span>
                ))}
              </div>
              {selectedKeyword && (
                <p className="text-[10px] text-muted-foreground mt-2">
                  Click keyword again to deselect
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Image Insert Modal */}
      <Dialog open={imageModalOpen} onOpenChange={setImageModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Insert Image</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="imageUrl">Image URL</Label>
              <Input
                id="imageUrl"
                placeholder="https://example.com/image.jpg"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="imageAlt">Alt Text (optional)</Label>
              <Input
                id="imageAlt"
                placeholder="Description of the image"
                value={imageAlt}
                onChange={(e) => setImageAlt(e.target.value)}
              />
            </div>
            {imageUrl && (
              <div className="border rounded-lg p-2">
                <p className="text-sm text-muted-foreground mb-2">Preview:</p>
                <img
                  src={imageUrl}
                  alt={imageAlt || "Preview"}
                  className="max-w-full h-auto max-h-48 object-contain mx-auto"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setImageModalOpen(false);
              setImageUrl("");
              setImageAlt("");
            }}>
              Cancel
            </Button>
            <Button onClick={handleInsertImage} disabled={!imageUrl}>
              Insert Image
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContentEditor;
