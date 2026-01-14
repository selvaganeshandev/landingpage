import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import PublishDialog from "@/components/PublishDialog";
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
  ChevronDown,
  Send,
  Info,
  Bot,
  User,
  Loader2,
  RefreshCw
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
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/services/api";

const ContentEditor = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const editorRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLTextAreaElement>(null);
  const isInitialLoad = useRef(true);

  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [contentData, setContentData] = useState<any>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);

  // Undo/Redo history - using refs to avoid stale closure issues
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const isUndoRedoAction = useRef(false);
  const [, forceUpdate] = useState(0); // Used to trigger re-render for button states

  // Image modal state
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [imageAlt, setImageAlt] = useState("");
  const savedSelectionRef = useRef<Range | null>(null);

  // Content metrics
  const [wordCount, setWordCount] = useState(0);
  const [headingsCount, setHeadingsCount] = useState(0);
  const [paragraphsCount, setParagraphsCount] = useState(0);
  const [imagesCount, setImagesCount] = useState(0);
  const [contentScore, setContentScore] = useState(0);
  const [scoreInfoOpen, setScoreInfoOpen] = useState(false);

  // Keywords tracking
  const [keywords, setKeywords] = useState<Array<{
    term: string;
    current: number;
    target: string;
    color: string;
  }>>([]);
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const originalContentRef = useRef<string>("");

  // AI Detection state
  const [aiDetecting, setAiDetecting] = useState(false);
  const [aiDetectionResult, setAiDetectionResult] = useState<{
    ai_score: number;
    human_score: number;
    label: string;
    confidence: number;
  } | null>(null);

  // Rewrite state
  const [hasSelection, setHasSelection] = useState(false);
  const [rewriteDialogOpen, setRewriteDialogOpen] = useState(false);
  const [rewritePrompt, setRewritePrompt] = useState("");
  const [isRewriting, setIsRewriting] = useState(false);
  const [selectedTextForDialog, setSelectedTextForDialog] = useState("");
  const selectedTextRef = useRef<string>("");
  const selectedRangeRef = useRef<Range | null>(null);

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

          // Strip H1 from content since title is now shown separately
          // Also remove any inline line-height styles that might cause inconsistent spacing
          let htmlContent = contentRecord.content_html || "";
          htmlContent = htmlContent.replace(/<h1[^>]*>.*?<\/h1>/gi, '').trim();
          // Remove line-height from inline styles
          htmlContent = htmlContent.replace(/line-height:\s*[^;"}]+;?/gi, '');
          // Remove empty style attributes
          htmlContent = htmlContent.replace(/\s*style="\s*"/gi, '');
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
          // Initialize undo/redo history with the loaded content
          historyRef.current = [content];
          historyIndexRef.current = 0;
          isInitialLoad.current = false;
          forceUpdate(n => n + 1); // Update button states
        }
      }, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [content, loading]);

  // Auto-resize title textarea when title changes
  useEffect(() => {
    if (titleRef.current && title) {
      titleRef.current.style.height = 'auto';
      titleRef.current.style.height = titleRef.current.scrollHeight + 'px';
    }
  }, [title]);

  // MutationObserver to remove inline line-height styles added by browser
  useEffect(() => {
    if (!editorRef.current) return;

    let isProcessing = false;

    const removeInlineLineHeight = (element: Element) => {
      if (element.hasAttribute('style')) {
        const style = element.getAttribute('style') || '';
        if (style.includes('line-height')) {
          const newStyle = style.replace(/line-height:\s*[^;]+;?/gi, '').trim();
          if (newStyle) {
            element.setAttribute('style', newStyle);
          } else {
            element.removeAttribute('style');
          }
        }
      }
    };

    const observer = new MutationObserver((mutations) => {
      if (isProcessing) return;
      isProcessing = true;

      try {
        mutations.forEach((mutation) => {
          // Check modified element
          if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
            removeInlineLineHeight(mutation.target as Element);
          }
          // Check added nodes
          if (mutation.type === 'childList') {
            mutation.addedNodes.forEach((node) => {
              if (node.nodeType === Node.ELEMENT_NODE) {
                removeInlineLineHeight(node as Element);
                // Also check children
                (node as Element).querySelectorAll('[style]').forEach(removeInlineLineHeight);
              }
            });
          }
        });
      } finally {
        // Use setTimeout to reset flag after current call stack
        setTimeout(() => {
          isProcessing = false;
        }, 0);
      }
    });

    observer.observe(editorRef.current, {
      attributes: true,
      attributeFilter: ['style'],
      childList: true,
      subtree: true,
    });

    return () => observer.disconnect();
  }, [loading]);

  // Track text selection in editor for rewrite button
  useEffect(() => {
    const handleSelectionChange = () => {
      // Don't update selection tracking when rewrite dialog is open
      // This preserves the selection data for the rewrite operation
      if (rewriteDialogOpen) {
        return;
      }

      const selection = window.getSelection();
      if (selection && editorRef.current) {
        const selectedText = selection.toString().trim();
        // Check if selection is within the editor
        if (selectedText && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          if (editorRef.current.contains(range.commonAncestorContainer)) {
            setHasSelection(true);
            selectedTextRef.current = selectedText;
            selectedRangeRef.current = range.cloneRange();
            return;
          }
        }
      }
      setHasSelection(false);
      selectedTextRef.current = "";
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, [rewriteDialogOpen]);

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

      // Add to history only if this is not an undo/redo action
      if (!isUndoRedoAction.current) {
        const lastContent = historyRef.current[historyIndexRef.current] || '';
        // Only add to history if content actually changed
        if (html !== lastContent) {
          // Remove any future states if we're not at the end
          historyRef.current = historyRef.current.slice(0, historyIndexRef.current + 1);
          // Add new state (limit history to 50 entries to save memory)
          historyRef.current.push(html);
          if (historyRef.current.length > 50) {
            historyRef.current = historyRef.current.slice(-50);
          }
          historyIndexRef.current = historyRef.current.length - 1;
          // Force re-render for button states
          forceUpdate(n => n + 1);
        }
      }
      isUndoRedoAction.current = false;

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

  // Undo function
  const handleUndo = () => {
    if (historyIndexRef.current > 0) {
      isUndoRedoAction.current = true;
      historyIndexRef.current = historyIndexRef.current - 1;
      const previousContent = historyRef.current[historyIndexRef.current];

      if (editorRef.current && previousContent !== undefined) {
        editorRef.current.innerHTML = previousContent;
        setContent(previousContent);
        updateMetrics(previousContent);
        editorRef.current.focus();
        // Force re-render for button states
        forceUpdate(n => n + 1);
      }
    }
  };

  // Redo function
  const handleRedo = () => {
    if (historyIndexRef.current < historyRef.current.length - 1) {
      isUndoRedoAction.current = true;
      historyIndexRef.current = historyIndexRef.current + 1;
      const nextContent = historyRef.current[historyIndexRef.current];

      if (editorRef.current && nextContent !== undefined) {
        editorRef.current.innerHTML = nextContent;
        setContent(nextContent);
        updateMetrics(nextContent);
        editorRef.current.focus();
        // Force re-render for button states
        forceUpdate(n => n + 1);
      }
    }
  };

  // Check if can undo/redo
  const canUndo = historyIndexRef.current > 0;
  const canRedo = historyIndexRef.current < historyRef.current.length - 1;

  // AI Detection function
  const handleAiDetection = async () => {
    const currentContent = editorRef.current?.innerHTML || content;

    if (!currentContent || currentContent.length < 50) {
      toast({
        title: "Not enough content",
        description: "Please add at least 50 characters of content to analyze.",
        variant: "destructive"
      });
      return;
    }

    try {
      setAiDetecting(true);
      setAiDetectionResult(null);

      const response = await apiClient.detectAiContent(currentContent);

      if (response.status === 'success') {
        setAiDetectionResult({
          ai_score: response.ai_score,
          human_score: response.human_score,
          label: response.label,
          confidence: response.confidence
        });
      } else if (response.status === 'loading') {
        toast({
          title: "Model Loading",
          description: response.message || "AI detection model is loading. Please try again in a few seconds.",
        });
      } else {
        toast({
          title: "Detection Failed",
          description: response.message || "Failed to analyze content",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      console.error("AI detection error:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to analyze content for AI detection",
        variant: "destructive"
      });
    } finally {
      setAiDetecting(false);
    }
  };

  // Open rewrite dialog
  const handleOpenRewriteDialog = () => {
    if (!hasSelection || !selectedTextRef.current) {
      toast({
        title: "No text selected",
        description: "Please select some text to rewrite.",
        variant: "destructive"
      });
      return;
    }
    setSelectedTextForDialog(selectedTextRef.current);
    setRewritePrompt("");
    setRewriteDialogOpen(true);
  };

  // Handle rewrite submission
  const handleRewrite = async () => {
    if (!rewritePrompt.trim()) {
      toast({
        title: "Prompt required",
        description: "Please enter instructions for how to rewrite the text.",
        variant: "destructive"
      });
      return;
    }

    if (!selectedTextRef.current || !selectedRangeRef.current) {
      toast({
        title: "Selection lost",
        description: "Please select the text again and try.",
        variant: "destructive"
      });
      setRewriteDialogOpen(false);
      return;
    }

    try {
      setIsRewriting(true);

      const response = await apiClient.rewriteContent({
        original_text: selectedTextRef.current,
        prompt: rewritePrompt,
        domain_id: contentData?.domain_id
      });

      if (response.status === 'success' && response.rewritten_text) {
        // Focus editor and restore selection
        editorRef.current?.focus();

        const selection = window.getSelection();
        if (selection && selectedRangeRef.current) {
          selection.removeAllRanges();
          selection.addRange(selectedRangeRef.current);

          // Replace selected text with rewritten content
          document.execCommand('insertText', false, response.rewritten_text);

          // Update content state
          handleContentChange();

          toast({
            title: "Content rewritten",
            description: "The selected text has been rewritten successfully.",
          });
        }
      } else {
        toast({
          title: "Rewrite failed",
          description: response.message || "Failed to rewrite content",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      console.error("Rewrite error:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to rewrite content",
        variant: "destructive"
      });
    } finally {
      setIsRewriting(false);
      setRewriteDialogOpen(false);
      setRewritePrompt("");
      selectedTextRef.current = "";
      selectedRangeRef.current = null;
      setHasSelection(false);
    }
  };

  // Formatting functions
  const execCommand = (command: string, value?: string) => {
    // Use custom undo/redo handlers
    if (command === 'undo') {
      handleUndo();
      return;
    }
    if (command === 'redo') {
      handleRedo();
      return;
    }

    // Ensure editor has focus before executing command
    editorRef.current?.focus();
    document.execCommand(command, false, value);
    // Update content state and history after command
    if (editorRef.current) {
      handleContentChange();
    }
  };

  // Handle opening image modal - save selection first
  const handleOpenImageModal = () => {
    // Save current selection before opening modal
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      savedSelectionRef.current = selection.getRangeAt(0).cloneRange();
    }
    setImageModalOpen(true);
  };

  // Handle image insertion
  const handleInsertImage = () => {
    if (imageUrl && editorRef.current) {
      const imgHtml = `<img src="${imageUrl}" alt="${imageAlt || 'Image'}" style="max-width: 100%; height: auto;" />`;

      // Focus the editor first
      editorRef.current.focus();

      // Try to restore the saved selection
      let inserted = false;
      if (savedSelectionRef.current) {
        try {
          const selection = window.getSelection();
          if (selection) {
            selection.removeAllRanges();
            selection.addRange(savedSelectionRef.current);
            // Insert the image at cursor position
            inserted = document.execCommand('insertHTML', false, imgHtml);
          }
        } catch (e) {
          console.log('Could not restore selection, appending to end');
        }
      }

      // Fallback: append to end of editor if insertion failed
      if (!inserted) {
        editorRef.current.innerHTML += imgHtml;
      }

      // Update content state and add to undo history
      handleContentChange();

      // Clear saved selection
      savedSelectionRef.current = null;
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

  // Save as draft (so it can be published later)
  const handleSaveAsDraft = async () => {
    if (!id) return;

    try {
      setSaving(true);

      // Get latest content
      const currentContent = editorRef.current?.innerHTML || content;

      await apiClient.updateGeneratedContent(parseInt(id), {
        title,
        content_html: currentContent,
        status: "draft",
        scheduled_date: null,
      });

      // Update local state
      setContent(currentContent);
      setContentData((prev: any) =>
        prev ? { ...prev, status: "draft", scheduled_date: null } : prev
      );

      toast({
        title: "Saved as Draft",
        description: "You can publish this content later.",
      });
    } catch (error) {
      console.error("Error saving draft:", error);
      toast({
        title: "Error",
        description: "Failed to save draft",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  // Handle publish button click - opens dialog
  const handlePublishClick = async () => {
    if (!id) return;

    // Save content first to ensure latest version is in database
    const currentContent = editorRef.current?.innerHTML || content;
    const currentTitle = title;

    try {
      await apiClient.updateGeneratedContent(parseInt(id), {
        title: currentTitle,
        content_html: currentContent
      });
      
      // Open publish dialog
      setPublishDialogOpen(true);
    } catch (error: any) {
      toast({
        title: "Error",
        description: "Failed to save content before publishing",
        variant: "destructive"
      });
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
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveAsDraft}
              disabled={saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? "Saving..." : "Save as Draft"}
            </Button>
            {(contentData?.status === "draft" || contentData?.status === "generated" || !contentData?.status) && (
              <Button
                variant="default"
                size="sm"
                onClick={handlePublishClick}
                className="gradient-primary"
              >
                <Send className="h-4 w-4 mr-2" />
                Publish
              </Button>
            )}
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
              {/* Lists Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="gap-1" title="Lists">
                    <List className="h-4 w-4" />
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => execCommand('insertUnorderedList')}>
                    <List className="h-4 w-4 mr-2" />
                    Bullet List
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('insertOrderedList')}>
                    <ListOrdered className="h-4 w-4 mr-2" />
                    Numbered List
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              {/* Alignment Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="gap-1" title="Alignment">
                    <AlignLeft className="h-4 w-4" />
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => execCommand('justifyLeft')}>
                    <AlignLeft className="h-4 w-4 mr-2" />
                    Align Left
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('justifyCenter')}>
                    <AlignCenter className="h-4 w-4 mr-2" />
                    Align Center
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => execCommand('justifyRight')}>
                    <AlignRight className="h-4 w-4 mr-2" />
                    Align Right
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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
                onClick={handleOpenImageModal}
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
                disabled={!canUndo}
                title="Undo (Ctrl+Z)"
                className={!canUndo ? 'opacity-50' : ''}
              >
                <Undo className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => execCommand('redo')}
                disabled={!canRedo}
                title="Redo (Ctrl+Y)"
                className={!canRedo ? 'opacity-50' : ''}
              >
                <Redo className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* AI Rewrite */}
              <Button
                variant={hasSelection ? "default" : "ghost"}
                size="sm"
                onClick={handleOpenRewriteDialog}
                disabled={!hasSelection}
                title="Rewrite selected text with AI"
                className={`gap-1 ${hasSelection ? 'bg-primary text-primary-foreground' : 'opacity-50'}`}
              >
                <RefreshCw className="h-4 w-4" />
                Rewrite
              </Button>
            </div>
          </div>

          {/* Content Editor */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-4xl mx-auto p-8">
              {/* Article Title (H1) */}
              <textarea
                ref={titleRef}
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  // Auto-resize textarea
                  e.target.style.height = 'auto';
                  e.target.style.height = e.target.scrollHeight + 'px';
                }}
                onFocus={(e) => {
                  // Ensure proper height on focus
                  e.target.style.height = 'auto';
                  e.target.style.height = e.target.scrollHeight + 'px';
                }}
                placeholder="Enter article title..."
                rows={1}
                className="w-full text-4xl font-bold mb-6 bg-transparent border-none outline-none focus:outline-none placeholder:text-muted-foreground/50 resize-none overflow-hidden"
                style={{
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  lineHeight: '1.2',
                  color: 'hsl(var(--foreground))',
                }}
              />
              {/* Rich Text Editor */}
              <style>{`
                .content-editor,
                .content-editor *:not(h1):not(h2):not(h3):not(h4):not(h5):not(strong):not(b):not(th) {
                  font-size: 16px !important;
                  font-weight: 400 !important;
                  line-height: 1.6 !important;
                }
                .content-editor [style] {
                  line-height: 1.6 !important;
                }
                .content-editor p[style],
                .content-editor div[style],
                .content-editor span[style] {
                  font-size: 16px !important;
                  font-weight: 400 !important;
                  line-height: 1.6 !important;
                }
                .content-editor {
                  color: hsl(var(--foreground));
                }
                .content-editor p {
                  margin-top: 0 !important;
                  margin-bottom: 1rem !important;
                }
                .content-editor h1 {
                  font-size: 2.25rem !important;
                  font-weight: 700 !important;
                  margin-top: 2rem !important;
                  margin-bottom: 1rem !important;
                  line-height: 1.2 !important;
                  color: hsl(var(--foreground));
                }
                .content-editor h2 {
                  font-size: 1.75rem !important;
                  font-weight: 600 !important;
                  margin-top: 1.75rem !important;
                  margin-bottom: 0.75rem !important;
                  line-height: 1.3 !important;
                  color: hsl(var(--foreground));
                }
                .content-editor h3 {
                  font-size: 1.35rem !important;
                  font-weight: 600 !important;
                  margin-top: 1.5rem !important;
                  margin-bottom: 0.5rem !important;
                  line-height: 1.4 !important;
                  color: hsl(var(--foreground));
                }
                .content-editor h4 {
                  font-size: 1.15rem !important;
                  font-weight: 600 !important;
                  margin-top: 1.25rem !important;
                  margin-bottom: 0.5rem !important;
                  line-height: 1.5 !important;
                  color: hsl(var(--foreground));
                }
                .content-editor h5 {
                  font-size: 1rem !important;
                  font-weight: 600 !important;
                  margin-top: 1rem !important;
                  margin-bottom: 0.5rem !important;
                  line-height: 1.5 !important;
                  color: hsl(var(--foreground));
                }
                .content-editor strong, .content-editor b {
                  font-weight: 700 !important;
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
                  font-weight: 600 !important;
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
                onKeyDown={(e) => {
                  // Handle Ctrl+Z for undo
                  if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                    e.preventDefault();
                    handleUndo();
                  }
                  // Handle Ctrl+Y or Ctrl+Shift+Z for redo
                  if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
                    e.preventDefault();
                    handleRedo();
                  }
                  // Handle backspace/delete on empty heading elements
                  if (e.key === 'Backspace' || e.key === 'Delete') {
                    const selection = window.getSelection();
                    if (selection && selection.rangeCount > 0) {
                      const range = selection.getRangeAt(0);

                      // If there's a text selection, let browser handle it normally
                      if (!range.collapsed) {
                        return;
                      }

                      let currentNode = range.startContainer;

                      // Find parent heading element
                      while (currentNode && currentNode !== editorRef.current) {
                        if (currentNode.nodeType === Node.ELEMENT_NODE) {
                          const tagName = (currentNode as Element).tagName?.toLowerCase();
                          if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
                            const heading = currentNode as HTMLElement;
                            const textContent = heading.textContent || '';

                            // Only remove if heading is completely empty
                            if (textContent === '') {
                              e.preventDefault();

                              // Get next sibling to place cursor
                              const nextElement = heading.nextElementSibling;
                              const prevElement = heading.previousElementSibling;

                              // Remove the empty heading
                              heading.remove();

                              // Place cursor at start of next element or end of previous
                              if (nextElement) {
                                const newRange = document.createRange();
                                newRange.setStart(nextElement, 0);
                                newRange.collapse(true);
                                selection.removeAllRanges();
                                selection.addRange(newRange);
                              } else if (prevElement) {
                                const newRange = document.createRange();
                                newRange.selectNodeContents(prevElement);
                                newRange.collapse(false);
                                selection.removeAllRanges();
                                selection.addRange(newRange);
                              }

                              handleContentChange();
                              return;
                            }
                            break;
                          }
                        }
                        currentNode = currentNode.parentNode as Node;
                      }
                    }
                  }
                }}
                className="content-editor min-h-[600px] focus:outline-none"
                style={{
                  fontFamily: 'system-ui, -apple-system, sans-serif',
                  fontSize: '16px',
                  fontWeight: 400,
                  lineHeight: '1.6',
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
            <div className="flex items-center gap-4">
              <div className="relative w-16 h-16 flex-shrink-0">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke="hsl(var(--muted))"
                    strokeWidth="6"
                    fill="none"
                  />
                  <circle
                    cx="32"
                    cy="32"
                    r="28"
                    stroke={contentScore >= 70 ? "#22c55e" : contentScore >= 50 ? "#f59e0b" : "#ef4444"}
                    strokeWidth="6"
                    fill="none"
                    strokeDasharray={`${(contentScore / 100) * 175.93} 175.93`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-lg font-bold">{contentScore}</span>
                </div>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-1">
                  <h3 className="font-semibold">Content Score</h3>
                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => setScoreInfoOpen(true)}>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {contentScore >= 70 ? "Great content!" : contentScore >= 50 ? "Good progress" : "Needs improvement"}
                </p>
              </div>
            </div>

            <Separator />

            {/* AI Detection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">AI Detection</h3>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleAiDetection}
                  disabled={aiDetecting}
                >
                  {aiDetecting ? (
                    <>
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Bot className="h-3 w-3 mr-1" />
                      Analyze
                    </>
                  )}
                </Button>
              </div>

              {aiDetectionResult ? (
                <div className="space-y-3">
                  {/* Result Label */}
                  <div className={`p-3 rounded-lg border ${
                    aiDetectionResult.label === "Human-written"
                      ? "bg-green-500/10 border-green-500/30"
                      : "bg-amber-500/10 border-amber-500/30"
                  }`}>
                    <div className="flex items-center gap-2">
                      {aiDetectionResult.label === "Human-written" ? (
                        <User className="h-5 w-5 text-green-500" />
                      ) : (
                        <Bot className="h-5 w-5 text-amber-500" />
                      )}
                      <div>
                        <p className={`font-semibold text-sm ${
                          aiDetectionResult.label === "Human-written"
                            ? "text-green-600"
                            : "text-amber-600"
                        }`}>
                          {aiDetectionResult.label}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {aiDetectionResult.confidence.toFixed(1)}% confidence
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Score Bars */}
                  <div className="space-y-2">
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="flex items-center gap-1">
                          <User className="h-3 w-3" /> Human
                        </span>
                        <span className="font-medium">{aiDetectionResult.human_score.toFixed(1)}%</span>
                      </div>
                      <Progress
                        value={aiDetectionResult.human_score}
                        className="h-2"
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="flex items-center gap-1">
                          <Bot className="h-3 w-3" /> AI
                        </span>
                        <span className="font-medium">{aiDetectionResult.ai_score.toFixed(1)}%</span>
                      </div>
                      <Progress
                        value={aiDetectionResult.ai_score}
                        className="h-2"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Click "Analyze" to check if content appears AI-generated
                </p>
              )}
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

      {/* Rewrite Dialog */}
      <Dialog open={rewriteDialogOpen} onOpenChange={setRewriteDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Rewrite with AI
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label>Selected Text</Label>
              <div className="p-3 bg-muted rounded-lg text-sm max-h-32 overflow-y-auto">
                {selectedTextForDialog || "No text selected"}
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="rewritePrompt">How would you like to rewrite this?</Label>
              <Textarea
                id="rewritePrompt"
                placeholder="e.g., Make it more concise, Add more detail, Change tone to professional, Simplify the language..."
                value={rewritePrompt}
                onChange={(e) => setRewritePrompt(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRewriteDialogOpen(false);
                setRewritePrompt("");
              }}
              disabled={isRewriting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRewrite}
              disabled={!rewritePrompt.trim() || isRewriting}
            >
              {isRewriting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Rewriting...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Rewrite
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Publish Dialog */}
      {id && (
        <PublishDialog
          open={publishDialogOpen}
          onOpenChange={(open) => {
            setPublishDialogOpen(open);
            if (!open) {
              // Reload content to get updated status
              if (id) {
                const loadContent = async () => {
                  try {
                    const data = await apiClient.getGeneratedContent(parseInt(id));
                    if (data?.data) {
                      setContentData(data.data);
                    }
                  } catch (error) {
                    console.error("Error reloading content:", error);
                  }
                };
                loadContent();
              }
            }
          }}
          contentId={parseInt(id)}
          contentTitle={title}
        />
      )}

      {/* Content Score Info Dialog */}
      <Dialog open={scoreInfoOpen} onOpenChange={setScoreInfoOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>How Content Score is Calculated</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground">
              Your content score is calculated based on 5 key factors:
            </p>

            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex-shrink-0 w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">30</span>
                </div>
                <div>
                  <h4 className="font-medium">Word Count</h4>
                  <p className="text-xs text-muted-foreground">1500-2500 words is ideal. Shorter or longer content scores lower.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex-shrink-0 w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">25</span>
                </div>
                <div>
                  <h4 className="font-medium">Keyword Usage</h4>
                  <p className="text-xs text-muted-foreground">Use target keywords naturally throughout your content within the recommended range.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex-shrink-0 w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">20</span>
                </div>
                <div>
                  <h4 className="font-medium">Headings Structure</h4>
                  <p className="text-xs text-muted-foreground">Aim for 1 heading per 200-300 words to improve readability.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex-shrink-0 w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">15</span>
                </div>
                <div>
                  <h4 className="font-medium">Paragraph Structure</h4>
                  <p className="text-xs text-muted-foreground">Use 5+ paragraphs to break up content and improve readability.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex-shrink-0 w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">10</span>
                </div>
                <div>
                  <h4 className="font-medium">Images</h4>
                  <p className="text-xs text-muted-foreground">Include at least 2 images to enhance visual appeal and engagement.</p>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Total possible score:</span>
                <span className="font-bold">100 points</span>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContentEditor;
