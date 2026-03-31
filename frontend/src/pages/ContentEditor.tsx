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
  RefreshCw,
  Link2,
  ExternalLink,
  Check,
  MessageSquare,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  Play,
  Wand2,
  Undo2,
  CircleDashed,
  FileText
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/services/api";

/**
 * Builds an HTML <table> from an array of pipe-delimited markdown rows.
 * Expects: rows[0] = header, rows[1] = separator (|---|---|), rows[2+] = body
 */
const buildHtmlTable = (rows: string[]): string => {
  let html = '<table>';

  // Header
  const headerCells = rows[0].split('|').filter(c => c.trim() !== '');
  html += '<thead><tr>';
  headerCells.forEach(cell => { html += `<th>${cell.trim()}</th>`; });
  html += '</tr></thead>';

  // Body (skip separator at index 1)
  if (rows.length > 2) {
    html += '<tbody>';
    for (let j = 2; j < rows.length; j++) {
      const cells = rows[j].split('|').filter(c => c.trim() !== '');
      html += '<tr>';
      cells.forEach(cell => { html += `<td>${cell.trim()}</td>`; });
      html += '</tr>';
    }
    html += '</tbody>';
  }

  html += '</table>';
  return html;
};

/**
 * Converts leftover markdown tables and images in HTML content to proper HTML elements.
 *
 * Problem: The AI backend sometimes returns content_html with markdown syntax:
 *   - Tables as pipe-delimited text: "| Col1 | Col2 |" (each row in its own <p> tag)
 *   - Images as markdown: "![alt](url)"
 *
 * This function detects and converts them to proper <table> and <img> HTML.
 */
const convertMarkdownInHtml = (html: string): string => {
  let result = html;

  // --- 1. Convert markdown images: ![alt](url) → <img> ---
  result = result.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    '<img src="$2" alt="$1" style="max-width:100%;height:auto;border-radius:0.5rem;margin:1rem 0;" />'
  );

  // --- 2. Convert markdown tables ---
  // Case A: Each table row is in its own <p> tag (most common from AI output)
  //   <p>| Step | Description |</p>
  //   <p>|------|--------------|</p>
  //   <p>| 1 | Do something |</p>
  result = result.replace(
    /(?:<p[^>]*>\s*\|[^<]*\|\s*<\/p>\s*){3,}/gi,
    (match) => {
      // Extract text content from each <p>
      const pRegex = /<p[^>]*>\s*(.*?)\s*<\/p>/gi;
      const lines: string[] = [];
      let m;
      while ((m = pRegex.exec(match)) !== null) {
        const text = m[1].trim();
        if (text.startsWith('|') && text.endsWith('|')) {
          lines.push(text);
        }
      }
      if (lines.length < 3) return match;
      // Verify second line is a separator (|---|---|)
      if (!/^\|[\s\-:|]+\|$/.test(lines[1])) return match;
      return buildHtmlTable(lines);
    }
  );

  // Case B: Table rows separated by <br> inside a single element
  //   <p>| Step | Description |<br>|---|---|<br>| 1 | Do something |</p>
  result = result.replace(
    /(<p[^>]*>)?\s*((?:\|[^<\n]*\|\s*(?:<br\s*\/?>)\s*){2,}\|[^<\n]*\|)\s*(<\/p>)?/gi,
    (fullMatch, _openP, tableBlock) => {
      const lines = tableBlock
        .split(/<br\s*\/?>/i)
        .map((l: string) => l.trim())
        .filter((l: string) => l.startsWith('|') && l.endsWith('|'));
      if (lines.length < 3) return fullMatch;
      if (!/^\|[\s\-:|]+\|$/.test(lines[1])) return fullMatch;
      return buildHtmlTable(lines);
    }
  );

  // Case C: Raw text with newlines (no <p> or <br> wrapping)
  result = result.replace(
    /((?:\|[^\n]*\|\s*\n\s*){2,}\|[^\n]*\|)/g,
    (fullMatch) => {
      const lines = fullMatch
        .split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('|') && l.endsWith('|'));
      if (lines.length < 3) return fullMatch;
      if (!/^\|[\s\-:|]+\|$/.test(lines[1])) return fullMatch;
      return buildHtmlTable(lines);
    }
  );

  return result;
};

// Humanise checklist rules displayed in the progress dialog
const HUMANISE_RULES = [
  "Remove em-dashes and en-dashes",
  "Apply sentence length variation",
  "Make tone conversational",
  "Distribute keywords evenly",
  "Apply curly quotes",
  "Vary section paragraph counts",
  "Remove banned words",
  "Remove buzzwords",
  "Remove clichés",
  "Remove rhetorical questions",
  "Enforce one idea per sentence",
  "Add natural human variation",
  "Optimise bullet point usage",
  "Enforce 2-item list rule",
  "Add forward-guiding endings",
  "Deduplicate descriptors",
  "Preserve HTML structure",
  "Preserve hyperlinks and keywords",
];

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

  // Auto-save: track dirty state and debounce saves (Issue 3: content not saving)
  const [isDirty, setIsDirty] = useState(false);
  const [autoSaveStatus, setAutoSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedContentRef = useRef<string>("");

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
    checked_at?: string;
  } | null>(null);

  // Rewrite state
  const [hasSelection, setHasSelection] = useState(false);
  const [rewriteDialogOpen, setRewriteDialogOpen] = useState(false);
  const [rewritePrompt, setRewritePrompt] = useState("");
  const [isRewriting, setIsRewriting] = useState(false);
  const [selectedTextForDialog, setSelectedTextForDialog] = useState("");
  const selectedTextRef = useRef<string>("");
  const selectedRangeRef = useRef<Range | null>(null);

  // Meta details dialog state
  const [metaDetailsDialogOpen, setMetaDetailsDialogOpen] = useState(false);
  const [editMetaTitle, setEditMetaTitle] = useState("");
  const [editMetaDescription, setEditMetaDescription] = useState("");
  const [isSavingMeta, setIsSavingMeta] = useState(false);

  // Link dialog state
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkText, setLinkText] = useState("");
  const [linkTarget, setLinkTarget] = useState<"_self" | "_blank">("_self");
  const [linkRel, setLinkRel] = useState<string>("dofollow"); // dofollow, nofollow, sponsored, ugc
  const [editingLinkElement, setEditingLinkElement] = useState<HTMLAnchorElement | null>(null);
  const linkSelectionRef = useRef<Range | null>(null);

  // Internal Links state
  const [internalLinks, setInternalLinks] = useState<Array<{
    id: number;
    topic: string;
    keywords: string;
    url: string;
  }>>([]);
  const [linkOpportunities, setLinkOpportunities] = useState<Array<{
    linkId: number;
    topic: string;
    keyword: string;
    url: string;
    count: number;
  }>>([]);
  const [appliedLinksCount, setAppliedLinksCount] = useState(0);
  const [totalLinkOpportunities, setTotalLinkOpportunities] = useState(0);
  const [isLoadingLinks, setIsLoadingLinks] = useState(false);
  const [isApplyingLinks, setIsApplyingLinks] = useState(false);
  const [linkOpportunitiesModalOpen, setLinkOpportunitiesModalOpen] = useState(false);
  const [selectedLinkOpportunities, setSelectedLinkOpportunities] = useState<Set<string>>(new Set());

  // Content Comments state (Google Docs-style)
  const [comments, setComments] = useState<Array<{
    id: number;
    author_name: string;
    author_email: string;
    selected_text: string;
    comment: string;
    suggestion: string | null;
    status: 'pending' | 'accepted' | 'rejected';
    resolved_by_name: string | null;
    resolved_at: string | null;
    created_at: string;
  }>>([]);
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [selectedText, setSelectedText] = useState('');
  const [showCommentDialog, setShowCommentDialog] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [suggestionText, setSuggestionText] = useState('');
  const [isSavingComment, setIsSavingComment] = useState(false);
  const [activeCommentId, setActiveCommentId] = useState<number | null>(null);
  const [viewingComment, setViewingComment] = useState<{
    id: number;
    author_name: string;
    selected_text: string;
    comment: string;
    suggestion: string | null;
    status: 'accepted' | 'rejected';
    resolved_by_name: string | null;
    resolved_at: string | null;
  } | null>(null);

  // Humanise state
  const [humaniseStatus, setHumaniseStatus] = useState<'idle' | 'processing' | 'completed' | 'failed'>('idle');
  const [humaniseError, setHumaniseError] = useState<string | null>(null);
  const [humaniseChecklistOpen, setHumaniseChecklistOpen] = useState(false);
  const [humaniseChecklistProgress, setHumaniseChecklistProgress] = useState(0);
  const humanisePollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const humaniseChecklistTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const preHumaniseContentRef = useRef<string | null>(null);
  const isHumaniseUpdateRef = useRef(false);

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
          // Convert any leftover markdown tables and images to proper HTML
          htmlContent = convertMarkdownInHtml(htmlContent);
          setContent(htmlContent);

          // Extract keywords and count occurrences
          // Use the cleaned htmlContent (same as what editor displays) for consistent scoring
          let keywordStats: typeof keywords = [];
          if (contentRecord.keywords) {
            const keywordList = contentRecord.keywords.split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0);
            const contentText = htmlContent.replace(/<[^>]*>/g, ' ').toLowerCase();

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
          // Use cleaned htmlContent to match what handleContentChange() computes
          updateMetrics(htmlContent, keywordStats);

          // Fetch internal links for the domain and find opportunities
          const domainId = contentRecord.domain_id || contentRecord.domain;
          if (domainId) {
            const links = await fetchInternalLinks(domainId);
            if (links.length > 0) {
              findLinkOpportunities(contentRecord.content_html || "", links);
            }
          }

          // Load saved AI detection results if available
          if (contentRecord.ai_detection_score !== null && contentRecord.ai_detection_score !== undefined) {
            setAiDetectionResult({
              ai_score: parseFloat(contentRecord.ai_detection_score),
              human_score: parseFloat(contentRecord.human_detection_score || 0),
              label: contentRecord.ai_detection_label || "Unknown",
              confidence: Math.max(
                parseFloat(contentRecord.ai_detection_score || 0),
                parseFloat(contentRecord.human_detection_score || 0)
              ),
              checked_at: contentRecord.ai_detection_checked_at
            });
          }

          // Restore humanise status
          if (contentRecord.humanise_status === 'processing') {
            setHumaniseStatus('processing');
            // Estimate checklist progress based on elapsed time since humanise started
            let resumeFrom = 0;
            if (contentRecord.humanise_started_at) {
              const elapsed = (Date.now() - new Date(contentRecord.humanise_started_at).getTime()) / 1000;
              // ~4 seconds per rule tick, cap at totalRules - 2 so it doesn't look done
              resumeFrom = Math.min(Math.floor(elapsed / 4), HUMANISE_RULES.length - 2);
            }
            startChecklistTimer(resumeFrom);
            startHumanisePolling(parseInt(id));
          } else if (contentRecord.humanise_status === 'completed' && contentRecord.pre_humanise_content) {
            setHumaniseStatus('completed');
            preHumaniseContentRef.current = contentRecord.pre_humanise_content;
          } else if (contentRecord.humanise_status === 'failed') {
            setHumaniseStatus('failed');
            setHumaniseError(contentRecord.humanise_error || 'Humanisation failed');
          }
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

  // Cleanup humanise polling and checklist timer on unmount
  useEffect(() => {
    return () => {
      if (humanisePollingRef.current) {
        clearInterval(humanisePollingRef.current);
      }
      if (humaniseChecklistTimerRef.current) {
        clearInterval(humaniseChecklistTimerRef.current);
      }
    };
  }, []);

  // Load comments
  useEffect(() => {
    const loadComments = async () => {
      if (!id) return;
      setIsLoadingComments(true);
      try {
        const response = await apiClient.getContentComments(parseInt(id));
        if (response.status === 'success') {
          setComments(response.data);
        }
      } catch (error) {
        console.error('Failed to load comments:', error);
      } finally {
        setIsLoadingComments(false);
      }
    };
    loadComments();
  }, [id]);

  // Handle text selection in editor
  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 0) {
      setSelectedText(selection.toString().trim());
      setActiveCommentId(null); // Clear active comment when selecting new text
    } else {
      setSelectedText('');
      // Don't clear activeCommentId here - only clear when explicitly clicking away
    }
  };

  // Open comment dialog with selected text
  const openCommentDialog = () => {
    if (!selectedText) return;
    setCommentText('');
    setSuggestionText('');
    setShowCommentDialog(true);
  };

  // Save new comment
  const saveComment = async () => {
    if (!id || !selectedText || !commentText.trim()) return;

    setIsSavingComment(true);
    try {
      const response = await apiClient.addContentComment(parseInt(id), {
        selected_text: selectedText,
        comment: commentText.trim(),
        suggestion: suggestionText.trim() || undefined
      });

      if (response.status === 'success') {
        // Refresh comments
        const commentsResponse = await apiClient.getContentComments(parseInt(id));
        if (commentsResponse.status === 'success') {
          setComments(commentsResponse.data);
        }

        setShowCommentDialog(false);
        setSelectedText('');
        setCommentText('');
        setSuggestionText('');
        toast({
          title: "Comment Added",
          description: "Your comment has been added",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add comment",
        variant: "destructive",
      });
    } finally {
      setIsSavingComment(false);
    }
  };

  // Accept a comment (apply suggestion if any)
  const acceptComment = async (commentId: number, suggestion: string | null) => {
    if (!id) return;

    try {
      // If there's a suggestion, apply it to the content
      if (suggestion && editorRef.current) {
        const comment = comments.find(c => c.id === commentId);
        if (comment) {
          const currentHtml = editorRef.current.innerHTML;
          const updatedHtml = currentHtml.replace(comment.selected_text, suggestion);
          editorRef.current.innerHTML = updatedHtml;
          handleContentChange();
        }
      }

      // Update comment status
      const response = await apiClient.updateContentComment(parseInt(id), commentId, {
        status: 'accepted'
      });

      if (response.status === 'success') {
        // Refresh comments
        const commentsResponse = await apiClient.getContentComments(parseInt(id));
        if (commentsResponse.status === 'success') {
          setComments(commentsResponse.data);
        }
        toast({
          title: "Comment Accepted",
          description: suggestion ? "Suggestion applied to content" : "Comment marked as accepted",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to accept comment",
        variant: "destructive",
      });
    }
  };

  // Reject a comment
  const rejectComment = async (commentId: number) => {
    if (!id) return;

    try {
      const response = await apiClient.updateContentComment(parseInt(id), commentId, {
        status: 'rejected'
      });

      if (response.status === 'success') {
        // Refresh comments
        const commentsResponse = await apiClient.getContentComments(parseInt(id));
        if (commentsResponse.status === 'success') {
          setComments(commentsResponse.data);
        }
        toast({
          title: "Comment Rejected",
          description: "Comment has been dismissed",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to reject comment",
        variant: "destructive",
      });
    }
  };

  // Delete a comment
  const deleteComment = async (commentId: number) => {
    if (!id) return;

    try {
      const response = await apiClient.deleteContentComment(parseInt(id), commentId);

      if (response.status === 'success') {
        setComments(comments.filter(c => c.id !== commentId));
        toast({
          title: "Comment Deleted",
          description: "Your comment has been deleted",
        });
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to delete comment",
        variant: "destructive",
      });
    }
  };

  // Highlight selected text in editor when a comment is active
  useEffect(() => {
    if (!editorRef.current) return;

    // Remove existing highlights
    const existingHighlights = editorRef.current.querySelectorAll('.comment-highlight');
    existingHighlights.forEach((el) => {
      const parent = el.parentNode;
      if (parent) {
        parent.replaceChild(document.createTextNode(el.textContent || ''), el);
        parent.normalize(); // Merge adjacent text nodes
      }
    });

    // If no active comment, we're done
    if (!activeCommentId) return;

    // Find the active comment
    const activeComment = comments.find(c => c.id === activeCommentId);
    if (!activeComment) return;

    // Find and highlight the selected text
    const searchText = activeComment.selected_text;
    const editorHtml = editorRef.current.innerHTML;

    // Escape special regex characters in the search text
    const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // Create a regex that matches the text (case-insensitive for flexibility)
    const regex = new RegExp(`(${escapedText})`, 'gi');

    // Only replace the first match to avoid multiple highlights
    let replaced = false;
    const newHtml = editorHtml.replace(regex, (match) => {
      if (replaced) return match;
      replaced = true;
      return `<span class="comment-highlight">${match}</span>`;
    });

    if (replaced) {
      // Save cursor position
      const selection = window.getSelection();
      const range = selection?.rangeCount ? selection.getRangeAt(0) : null;

      editorRef.current.innerHTML = newHtml;

      // Scroll the highlight into view
      const highlight = editorRef.current.querySelector('.comment-highlight');
      if (highlight) {
        highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [activeCommentId, comments]);

  // Set the HTML content only on initial load
  useEffect(() => {
    if (editorRef.current && content && !loading && isInitialLoad.current) {
      // Use a small delay to ensure the contentEditable div is fully ready
      const timeoutId = setTimeout(() => {
        if (editorRef.current) {
          editorRef.current.innerHTML = content;
          originalContentRef.current = content; // Store original content for keyword highlighting
          lastSavedContentRef.current = content; // Track last saved state for auto-save
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

      // Recalculate internal link opportunities
      if (internalLinks.length > 0) {
        findLinkOpportunities(html, internalLinks);
      }

      // Update original content ref when user edits (only if no keyword is selected)
      if (!selectedKeyword) {
        originalContentRef.current = html;
      }

      // Auto-save: mark dirty and schedule save after 5 seconds of inactivity
      // (Issue 3: content not saving / auto-undoing)
      if (html !== lastSavedContentRef.current && !isUndoRedoAction.current) {
        setIsDirty(true);
        setAutoSaveStatus('unsaved');

        // Clear existing timer
        if (autoSaveTimerRef.current) {
          clearTimeout(autoSaveTimerRef.current);
        }

        // Schedule auto-save after 5 seconds of no edits
        autoSaveTimerRef.current = setTimeout(async () => {
          if (id && editorRef.current) {
            try {
              setAutoSaveStatus('saving');
              await apiClient.updateGeneratedContent(parseInt(id), {
                title,
                content_html: editorRef.current.innerHTML
              });
              lastSavedContentRef.current = editorRef.current.innerHTML;
              setIsDirty(false);
              setAutoSaveStatus('saved');
            } catch (err) {
              console.error("Auto-save failed:", err);
              setAutoSaveStatus('unsaved');
            }
          }
        }, 5000);
      }

      // Reset humanise status when user manually edits content (not programmatic)
      if (!isHumaniseUpdateRef.current && humaniseStatus === 'completed') {
        setHumaniseStatus('idle');
        preHumaniseContentRef.current = null;
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

      // Pass content id to save results to database
      const contentId = id ? parseInt(id) : undefined;
      const response = await apiClient.detectAiContent(currentContent, contentId);

      if (response.status === 'success') {
        setAiDetectionResult({
          ai_score: response.ai_score,
          human_score: response.human_score,
          label: response.label,
          confidence: response.confidence,
          checked_at: response.checked_at || new Date().toISOString()
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

  // ============= HUMANISE HANDLERS =============

  const startChecklistTimer = (startFrom: number = 0) => {
    // Clear any existing timer
    if (humaniseChecklistTimerRef.current) {
      clearInterval(humaniseChecklistTimerRef.current);
    }

    setHumaniseChecklistProgress(startFrom);
    setHumaniseChecklistOpen(true);

    // Cosmetic timer: check off ~1 rule every 4 seconds, stop at totalRules - 1
    // (the last rule gets checked when polling detects completion)
    const totalRules = HUMANISE_RULES.length;
    let current = startFrom;

    humaniseChecklistTimerRef.current = setInterval(() => {
      current += 1;
      if (current >= totalRules - 1) {
        // Stop at second-to-last — final tick happens on completion
        setHumaniseChecklistProgress(totalRules - 1);
        if (humaniseChecklistTimerRef.current) {
          clearInterval(humaniseChecklistTimerRef.current);
          humaniseChecklistTimerRef.current = null;
        }
      } else {
        setHumaniseChecklistProgress(current);
      }
    }, 4000);
  };

  const startHumanisePolling = (contentId: number) => {
    if (humanisePollingRef.current) {
      clearInterval(humanisePollingRef.current);
    }

    humanisePollingRef.current = setInterval(async () => {
      try {
        const response: any = await apiClient.getHumaniseStatus(contentId);

        if (response.status === 'success') {
          const data = response.data;

          if (data.humanise_status === 'completed') {
            if (humanisePollingRef.current) {
              clearInterval(humanisePollingRef.current);
              humanisePollingRef.current = null;
            }

            if (data.content_html && editorRef.current) {
              let htmlContent = data.content_html;
              htmlContent = htmlContent.replace(/<h1[^>]*>.*?<\/h1>/gi, '').trim();
              htmlContent = htmlContent.replace(/line-height:\s*[^;"}]+;?/gi, '');
              htmlContent = htmlContent.replace(/\s*style="\s*"/gi, '');
              htmlContent = convertMarkdownInHtml(htmlContent);

              isHumaniseUpdateRef.current = true;
              editorRef.current.innerHTML = htmlContent;
              setContent(htmlContent);
              handleContentChange();
              // Delay ref reset so async onInput events from innerHTML change
              // are still guarded and don't reset humanise status
              setTimeout(() => { isHumaniseUpdateRef.current = false; }, 300);

              // Save cleaned content to backend so page refresh loads the same
              // content the editor displays (ensures consistent score on reload)
              if (id) {
                apiClient.updateGeneratedContent(parseInt(id), {
                  content_html: htmlContent
                }).catch(err => console.error("Error saving humanised content:", err));
              }
            }

            setHumaniseStatus('completed');

            // Complete the checklist: set progress to max, stop timer
            if (humaniseChecklistTimerRef.current) {
              clearInterval(humaniseChecklistTimerRef.current);
              humaniseChecklistTimerRef.current = null;
            }
            setHumaniseChecklistProgress(HUMANISE_RULES.length);
            // Auto-close checklist dialog after 1.5s so user sees "complete" state
            setTimeout(() => {
              setHumaniseChecklistOpen(false);
            }, 1500);

            toast({
              title: "Humanisation complete",
              description: "Content has been humanised. Click Undo to revert.",
            });

          } else if (data.humanise_status === 'failed') {
            if (humanisePollingRef.current) {
              clearInterval(humanisePollingRef.current);
              humanisePollingRef.current = null;
            }

            setHumaniseStatus('failed');
            setHumaniseError(data.humanise_error || 'Humanisation failed');

            // Close checklist dialog and stop timer on failure
            if (humaniseChecklistTimerRef.current) {
              clearInterval(humaniseChecklistTimerRef.current);
              humaniseChecklistTimerRef.current = null;
            }
            setHumaniseChecklistOpen(false);

            toast({
              title: "Humanisation failed",
              description: data.humanise_error || "An error occurred during humanisation.",
              variant: "destructive"
            });
          }
        }
      } catch (error) {
        console.error("Error polling humanise status:", error);
      }
    }, 3000);
  };

  const handleHumanise = async () => {
    if (!id) return;

    const currentContent = editorRef.current?.innerHTML || content;
    if (!currentContent || currentContent.length < 50) {
      toast({
        title: "Not enough content",
        description: "Please add more content before humanising.",
        variant: "destructive"
      });
      return;
    }

    // Save content to backend first
    try {
      await apiClient.updateGeneratedContent(parseInt(id), {
        title,
        content_html: currentContent
      });
    } catch (error) {
      console.error("Error saving content before humanise:", error);
      toast({
        title: "Error",
        description: "Failed to save content before humanisation",
        variant: "destructive"
      });
      return;
    }

    preHumaniseContentRef.current = currentContent;

    try {
      setHumaniseStatus('processing');
      setHumaniseError(null);

      const response: any = await apiClient.humaniseContent(parseInt(id));

      if (response.status === 'success') {
        startChecklistTimer(0);
        startHumanisePolling(parseInt(id));
      } else {
        setHumaniseStatus('failed');
        setHumaniseError(response.message || 'Failed to start humanisation');
        setHumaniseChecklistOpen(false);
        toast({
          title: "Error",
          description: response.message || "Failed to start humanisation",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      console.error("Humanise error:", error);
      setHumaniseStatus('failed');
      setHumaniseError(error.message || 'Failed to start humanisation');
      setHumaniseChecklistOpen(false);
      if (humaniseChecklistTimerRef.current) {
        clearInterval(humaniseChecklistTimerRef.current);
        humaniseChecklistTimerRef.current = null;
      }
      toast({
        title: "Error",
        description: error.message || "Failed to start humanisation",
        variant: "destructive"
      });
    }
  };

  const handleHumaniseUndo = async () => {
    if (!id) return;

    try {
      const response: any = await apiClient.humaniseUndo(parseInt(id));

      if (response.status === 'success' && response.data?.content_html) {
        let htmlContent = response.data.content_html;
        htmlContent = htmlContent.replace(/<h1[^>]*>.*?<\/h1>/gi, '').trim();
        htmlContent = htmlContent.replace(/line-height:\s*[^;"}]+;?/gi, '');
        htmlContent = htmlContent.replace(/\s*style="\s*"/gi, '');
        htmlContent = convertMarkdownInHtml(htmlContent);

        if (editorRef.current) {
          isHumaniseUpdateRef.current = true;
          editorRef.current.innerHTML = htmlContent;
          setContent(htmlContent);
          handleContentChange();
          // Delay ref reset so async onInput events from innerHTML change
          // are still guarded and don't reset humanise status
          setTimeout(() => { isHumaniseUpdateRef.current = false; }, 300);
        }

        setHumaniseStatus('idle');
        preHumaniseContentRef.current = null;

        toast({
          title: "Reverted",
          description: "Content has been reverted to the pre-humanisation version.",
        });
      } else {
        toast({
          title: "Error",
          description: response.message || "Failed to undo humanisation",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      console.error("Humanise undo error:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to undo humanisation",
        variant: "destructive"
      });
    }
  };

  // Fetch internal links for the domain
  const fetchInternalLinks = async (domainId: number) => {
    try {
      setIsLoadingLinks(true);
      const response: any = await apiClient.getInternalLinkMaps(domainId);
      const links = response.internal_links || [];
      setInternalLinks(links);
      return links;
    } catch (error) {
      console.error("Error fetching internal links:", error);
      return [];
    } finally {
      setIsLoadingLinks(false);
    }
  };

  // Find link opportunities in content
  const findLinkOpportunities = (htmlContent: string, links: typeof internalLinks) => {
    if (!links || links.length === 0) {
      setLinkOpportunities([]);
      setTotalLinkOpportunities(0);
      setAppliedLinksCount(0);
      return;
    }

    // Get plain text from content
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlContent;
    const plainText = tempDiv.textContent?.toLowerCase() || '';

    // Extract all text content from anchor tags to check what's already linked
    const anchorTexts: string[] = [];
    const anchors = tempDiv.querySelectorAll('a');
    anchors.forEach(anchor => {
      const text = anchor.textContent?.toLowerCase() || '';
      if (text) anchorTexts.push(text);
    });

    // Find which keywords appear in the content (excluding already linked text)
    const opportunities: typeof linkOpportunities = [];
    let appliedKeywordsCount = 0;
    let totalKeywordsFound = 0;

    links.forEach(link => {
      // Split keywords by comma and check each one
      const keywordList = link.keywords.split(',').map(k => k.trim().toLowerCase()).filter(k => k.length > 0);

      keywordList.forEach(keyword => {
        if (keyword.length < 2) return; // Skip very short keywords

        // Count occurrences of keyword in plain text
        const regex = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
        const matches = plainText.match(regex);
        const count = matches ? matches.length : 0;

        if (count > 0) {
          totalKeywordsFound++;

          // Check if this keyword is already inside any anchor tag
          const keywordRegex = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
          const alreadyLinked = anchorTexts.some(anchorText => keywordRegex.test(anchorText));

          if (alreadyLinked) {
            appliedKeywordsCount++;
          } else {
            opportunities.push({
              linkId: link.id,
              topic: link.topic,
              keyword: keyword,
              url: link.url,
              count: count
            });
          }
        }
      });
    });

    // Sort by count descending
    opportunities.sort((a, b) => b.count - a.count);
    setLinkOpportunities(opportunities);
    setTotalLinkOpportunities(totalKeywordsFound);
    setAppliedLinksCount(appliedKeywordsCount);
  };

  // Generate unique key for a link opportunity
  const getLinkOpportunityKey = (opportunity: typeof linkOpportunities[0]) => {
    return `${opportunity.linkId}-${opportunity.keyword}`;
  };

  // Apply selected internal links to content
  const handleApplySelectedLinks = () => {
    if (!editorRef.current || selectedLinkOpportunities.size === 0) return;

    setIsApplyingLinks(true);

    try {
      let html = editorRef.current.innerHTML;
      let appliedCount = 0;

      // Apply only selected link opportunities
      linkOpportunities.forEach(opportunity => {
        const key = getLinkOpportunityKey(opportunity);
        if (!selectedLinkOpportunities.has(key)) return;

        // Create a regex that matches the keyword but not if it's already in a link
        const keywordRegex = new RegExp(
          `(?<!<a[^>]*>)\\b(${opportunity.keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b(?![^<]*</a>)`,
          'i'
        );

        // Replace only the first occurrence
        const newHtml = html.replace(keywordRegex, `<a href="${opportunity.url}" target="_blank" rel="noopener noreferrer">$1</a>`);
        if (newHtml !== html) {
          appliedCount++;
          html = newHtml;
        }
      });

      // Update the editor
      editorRef.current.innerHTML = html;
      handleContentChange();

      // Recalculate opportunities
      findLinkOpportunities(html, internalLinks);

      // Close modal and reset selection
      setLinkOpportunitiesModalOpen(false);
      setSelectedLinkOpportunities(new Set());

      toast({
        title: "Links Applied",
        description: `Applied ${appliedCount} internal link(s) to your content.`,
      });
    } catch (error) {
      console.error("Error applying internal links:", error);
      toast({
        title: "Error",
        description: "Failed to apply internal links",
        variant: "destructive"
      });
    } finally {
      setIsApplyingLinks(false);
    }
  };

  // Toggle selection of a link opportunity
  const toggleLinkOpportunitySelection = (opportunity: typeof linkOpportunities[0]) => {
    const key = getLinkOpportunityKey(opportunity);
    setSelectedLinkOpportunities(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) {
        newSet.delete(key);
      } else {
        newSet.add(key);
      }
      return newSet;
    });
  };

  // Toggle all link opportunities selection
  const toggleAllLinkOpportunities = (selectAll: boolean) => {
    if (selectAll) {
      const allKeys = linkOpportunities.map(getLinkOpportunityKey);
      setSelectedLinkOpportunities(new Set(allKeys));
    } else {
      setSelectedLinkOpportunities(new Set());
    }
  };

  // Open the link opportunities modal
  const handleOpenLinkOpportunitiesModal = () => {
    setSelectedLinkOpportunities(new Set());
    setLinkOpportunitiesModalOpen(true);
  };

  // Open link dialog
  const handleOpenLinkDialog = () => {
    const selection = window.getSelection();

    // Check if cursor/selection is inside an existing link
    let existingLink: HTMLAnchorElement | null = null;
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      let node: Node | null = range.startContainer;

      // Walk up the DOM tree to find an anchor element
      while (node && node !== editorRef.current) {
        if (node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName === 'A') {
          existingLink = node as HTMLAnchorElement;
          break;
        }
        node = node.parentNode;
      }

      if (existingLink) {
        // Editing existing link - pre-populate with existing values
        setEditingLinkElement(existingLink);
        setLinkUrl(existingLink.href || "");
        setLinkText(existingLink.textContent || "");
        setLinkTarget(existingLink.target === "_blank" ? "_blank" : "_self");

        // Detect rel attribute
        const rel = existingLink.rel || "";
        if (rel.includes("sponsored")) {
          setLinkRel("sponsored");
        } else if (rel.includes("ugc")) {
          setLinkRel("ugc");
        } else if (rel.includes("nofollow")) {
          setLinkRel("nofollow");
        } else {
          setLinkRel("dofollow");
        }

        // Select the entire link for replacement
        const linkRange = document.createRange();
        linkRange.selectNode(existingLink);
        linkSelectionRef.current = linkRange;
        setLinkDialogOpen(true);
        return;
      }

      // No existing link - use selected text
      const selectedText = selection.toString().trim();
      linkSelectionRef.current = range.cloneRange();
      setEditingLinkElement(null);
      setLinkText(selectedText);
      setLinkUrl("");
      setLinkTarget("_self");
      setLinkRel("dofollow");
      setLinkDialogOpen(true);
    } else {
      // No selection, still allow inserting link
      linkSelectionRef.current = null;
      setEditingLinkElement(null);
      setLinkText("");
      setLinkUrl("");
      setLinkTarget("_self");
      setLinkRel("dofollow");
      setLinkDialogOpen(true);
    }
  };

  // Build rel attribute based on settings
  const buildRelAttribute = () => {
    const relParts: string[] = [];

    // Add noopener noreferrer for new window links
    if (linkTarget === "_blank") {
      relParts.push("noopener", "noreferrer");
    }

    // Add SEO-related rel values
    if (linkRel === "nofollow") {
      relParts.push("nofollow");
    } else if (linkRel === "sponsored") {
      relParts.push("sponsored", "nofollow");
    } else if (linkRel === "ugc") {
      relParts.push("ugc", "nofollow");
    }
    // dofollow = no additional rel needed

    return relParts.length > 0 ? relParts.join(" ") : "";
  };

  // Insert or update link
  const handleInsertLink = () => {
    if (!linkUrl) {
      toast({
        title: "URL Required",
        description: "Please enter a URL for the link.",
        variant: "destructive"
      });
      return;
    }

    editorRef.current?.focus();
    const relValue = buildRelAttribute();

    // If editing an existing link, update it directly
    if (editingLinkElement && editingLinkElement.parentNode) {
      editingLinkElement.href = linkUrl;
      editingLinkElement.textContent = linkText || linkUrl;

      if (linkTarget === "_blank") {
        editingLinkElement.target = "_blank";
      } else {
        editingLinkElement.removeAttribute("target");
      }

      if (relValue) {
        editingLinkElement.rel = relValue;
      } else {
        editingLinkElement.removeAttribute("rel");
      }

      handleContentChange();
    } else if (linkSelectionRef.current) {
      // Restore selection and insert new link
      const selection = window.getSelection();
      if (selection) {
        selection.removeAllRanges();
        selection.addRange(linkSelectionRef.current);

        // Create the link HTML
        const textToLink = linkText || linkUrl;
        const targetAttr = linkTarget === "_blank" ? ' target="_blank"' : '';
        const relAttr = relValue ? ` rel="${relValue}"` : '';
        const linkHtml = `<a href="${linkUrl}"${targetAttr}${relAttr}>${textToLink}</a>`;

        document.execCommand('insertHTML', false, linkHtml);
        handleContentChange();
      }
    } else {
      // No selection, insert link at cursor or end
      const textToLink = linkText || linkUrl;
      const targetAttr = linkTarget === "_blank" ? ' target="_blank"' : '';
      const relAttr = relValue ? ` rel="${relValue}"` : '';
      const linkHtml = `<a href="${linkUrl}"${targetAttr}${relAttr}>${textToLink}</a>`;
      document.execCommand('insertHTML', false, linkHtml);
      handleContentChange();
    }

    setLinkDialogOpen(false);
    setLinkUrl("");
    setLinkText("");
    setLinkRel("dofollow");
    setEditingLinkElement(null);
    linkSelectionRef.current = null;
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
      lastSavedContentRef.current = currentContent;
      setIsDirty(false);
      setAutoSaveStatus('saved');

      // Cancel any pending auto-save
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = null;
      }

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

  // Save meta details (meta_title and meta_description)
  const handleSaveMetaDetails = async () => {
    if (!id) return;

    try {
      setIsSavingMeta(true);

      await apiClient.updateGeneratedContent(parseInt(id), {
        meta_title: editMetaTitle.trim(),
        meta_description: editMetaDescription.trim(),
      });

      // Update local contentData to reflect the changes
      setContentData((prev: any) => ({
        ...prev,
        meta_title: editMetaTitle.trim(),
        meta_description: editMetaDescription.trim(),
      }));

      toast({
        title: "Success",
        description: "Meta details updated successfully",
      });

      setMetaDetailsDialogOpen(false);
    } catch (error) {
      console.error("Error saving meta details:", error);
      toast({
        title: "Error",
        description: "Failed to save meta details",
        variant: "destructive"
      });
    } finally {
      setIsSavingMeta(false);
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
  const handleExportDocx = () => {
    const htmlContent = editorRef.current?.innerHTML || content;
    if (!htmlContent) {
      toast({ title: "Nothing to export", description: "Editor content is empty." });
      return;
    }
    const titleHtml = title ? `<h1 style="font-size:26pt;font-weight:bold;margin-bottom:12pt;">${title}</h1>` : "";
    const fullHtml = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40"><head><meta charset="utf-8"><title>${title || "Content"}</title></head><body>${titleHtml}${htmlContent}</body></html>`;
    const blob = new Blob([fullHtml], { type: "application/msword" });
    const url = URL.createObjectURL(blob);
    const filename = (title || "content").replace(/[^a-zA-Z0-9\s-]/g, "").trim().replace(/\s+/g, "_");
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.doc`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Export as HTML file (Issue 6: download options)
  const handleExportHtml = () => {
    const htmlContent = editorRef.current?.innerHTML || content;
    if (!htmlContent) {
      toast({ title: "Nothing to export", description: "Editor content is empty." });
      return;
    }
    const titleHtml = title ? `<h1>${title}</h1>` : "";
    const fullHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title || "Content"}</title><style>body{font-family:Arial,sans-serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.6}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background-color:#f2f2f2}img{max-width:100%}</style></head><body>${titleHtml}${htmlContent}</body></html>`;
    const blob = new Blob([fullHtml], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const filename = (title || "content").replace(/[^a-zA-Z0-9\s-]/g, "").trim().replace(/\s+/g, "_");
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Export as plain text (Issue 6: no background when pasting)
  const handleExportTxt = () => {
    const htmlContent = editorRef.current?.innerHTML || content;
    if (!htmlContent) {
      toast({ title: "Nothing to export", description: "Editor content is empty." });
      return;
    }
    const titleText = title ? `${title}\n${"=".repeat(title.length)}\n\n` : "";
    const plainText = titleText + htmlContent.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim();
    const blob = new Blob([plainText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const filename = (title || "content").replace(/[^a-zA-Z0-9\s-]/g, "").trim().replace(/\s+/g, "_");
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Copy content without background styling (Issue 6: background pasting)
  const handleCopyClean = async () => {
    const htmlContent = editorRef.current?.innerHTML || content;
    if (!htmlContent) {
      toast({ title: "Nothing to copy", description: "Editor content is empty." });
      return;
    }
    // Strip background-color styles to prevent colored background when pasting
    const cleanHtml = htmlContent.replace(/background-color\s*:\s*[^;}"']+;?/gi, '');
    try {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([cleanHtml], { type: 'text/html' }),
          'text/plain': new Blob([htmlContent.replace(/<[^>]*>/g, '')], { type: 'text/plain' })
        })
      ]);
      toast({ title: "Copied", description: "Content copied without background styling" });
    } catch {
      // Fallback to plain text copy
      await navigator.clipboard.writeText(htmlContent.replace(/<[^>]*>/g, ''));
      toast({ title: "Copied", description: "Content copied as plain text" });
    }
  };

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
            {/* Auto-save status indicator */}
            {autoSaveStatus === 'saving' && (
              <span className="text-xs text-muted-foreground animate-pulse">Auto-saving...</span>
            )}
            {autoSaveStatus === 'saved' && !isDirty && (
              <span className="text-xs text-green-600">Saved</span>
            )}
            {autoSaveStatus === 'unsaved' && isDirty && (
              <span className="text-xs text-orange-500">Unsaved changes</span>
            )}
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
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="default" size="sm">
                  <Share2 className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleExportDocx}>
                  Export as Word (.doc)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportHtml}>
                  Export as HTML
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleExportTxt}>
                  Export as Plain Text
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleCopyClean}>
                  Copy (no background)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
                onClick={handleOpenLinkDialog}
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
                title="Optimize selected text with custom prompt"
                className={`gap-1 ${hasSelection ? 'bg-primary text-primary-foreground' : 'opacity-50'}`}
              >
                <RefreshCw className="h-4 w-4" />
                Optimize with custom prompt
              </Button>
              <Separator orientation="vertical" className="h-6 mx-1" />
              {/* Meta Details */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEditMetaTitle(contentData?.meta_title || "");
                  setEditMetaDescription(contentData?.meta_description || "");
                  setMetaDetailsDialogOpen(true);
                }}
                title="View and edit meta title & description"
                className="gap-1"
              >
                <FileText className="h-4 w-4" />
                Meta Details
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
                .content-editor img {
                  max-width: 100%;
                  height: auto;
                  border-radius: 0.5rem;
                  margin: 1rem 0;
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
                .content-editor .comment-highlight {
                  background-color: hsl(var(--primary) / 0.2) !important;
                  border-bottom: 2px solid hsl(var(--primary)) !important;
                  padding: 2px 0 !important;
                  transition: background-color 0.3s ease;
                  border-radius: 2px;
                }
                @keyframes pulse-highlight {
                  0%, 100% { background-color: hsl(var(--primary) / 0.2); }
                  50% { background-color: hsl(var(--primary) / 0.35); }
                }
                .content-editor .comment-highlight {
                  animation: pulse-highlight 1.5s ease-in-out 2;
                }
              `}</style>
              <div
                ref={editorRef}
                contentEditable
                onInput={handleContentChange}
                onMouseUp={handleTextSelection}
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
          <Tabs defaultValue="content" className="h-full flex flex-col">
            <div className="border-b border-border bg-card p-3">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="content">Content</TabsTrigger>
                <TabsTrigger value="reviews">
                  Comments
                  {comments.filter(c => c.status === 'pending').length > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center h-5 min-w-5 px-1.5 text-xs font-medium rounded-full bg-primary text-primary-foreground">
                      {comments.filter(c => c.status === 'pending').length}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="content" className="flex-1 overflow-y-auto mt-0">
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

            {/* Humanise */}
            <div className="flex items-center gap-2 mt-3">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 h-8 text-xs"
                onClick={handleHumanise}
                disabled={humaniseStatus === 'processing' || humaniseStatus === 'completed'}
              >
                {humaniseStatus === 'processing' ? (
                  <>
                    <Loader2 className="h-3 w-3 mr-1.5 animate-spin" />
                    Humanising...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-3 w-3 mr-1.5" />
                    Humanise
                  </>
                )}
              </Button>

              {humaniseStatus === 'completed' && preHumaniseContentRef.current && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={handleHumaniseUndo}
                  title="Undo humanisation"
                >
                  <Undo2 className="h-4 w-4" />
                </Button>
              )}
            </div>

            {humaniseStatus === 'failed' && humaniseError && (
              <p className="text-xs text-destructive mt-1">
                {humaniseError}
              </p>
            )}

            <Separator />

            {/* AI Detection */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold">AI Detection</h3>
                  <p className="text-xs text-muted-foreground">Powered by <a href="https://huggingface.co/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">Hugging Face</a></p>
                </div>
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

                  {/* Last Checked Time */}
                  {aiDetectionResult.checked_at && (
                    <p className="text-xs text-muted-foreground text-center pt-2 border-t">
                      Last checked: {new Date(aiDetectionResult.checked_at).toLocaleString()}
                    </p>
                  )}
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

            {/* Internal Links */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Internal Links</h3>
                {isLoadingLinks && (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>

              {internalLinks.length === 0 ? (
                <div className="text-center py-4">
                  <Link2 className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">
                    No internal links configured for this domain.
                  </p>
                  <Button
                    variant="link"
                    size="sm"
                    className="text-xs mt-1 h-auto p-0"
                    onClick={() => {
                      const domainId = contentData?.domain_id || contentData?.domain;
                      if (domainId) {
                        window.open(`/organization-settings/domains/${domainId}?tab=internal-links`, '_blank');
                      }
                    }}
                  >
                    Configure in Domain Settings
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Counts */}
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Opportunities:</span>
                      <span className="font-semibold">{linkOpportunities.length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Applied:</span>
                      <span className="font-semibold text-green-600">{appliedLinksCount}/{totalLinkOpportunities}</span>
                    </div>
                  </div>

                  {/* Explore button */}
                  {linkOpportunities.length > 0 ? (
                    <Button
                      size="sm"
                      className="w-full"
                      onClick={handleOpenLinkOpportunitiesModal}
                    >
                      <Link2 className="h-4 w-4 mr-2" />
                      Explore Opportunities
                    </Button>
                  ) : (
                    <div className="flex items-center justify-center gap-2 py-2 text-green-600">
                      <Check className="h-4 w-4" />
                      <span className="text-xs">All links applied</span>
                    </div>
                  )}
                </div>
              )}
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
            </TabsContent>

            <TabsContent value="reviews" className="flex-1 overflow-y-auto mt-0">
              <div className="p-4 space-y-4">
                {/* Add Comment Section */}
                {selectedText && (
                  <Card className="p-3 border-primary">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-primary">Selected Text</span>
                      <Button size="sm" variant="default" onClick={openCommentDialog}>
                        <MessageSquare className="h-3 w-3 mr-1" />
                        Add Comment
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground bg-muted p-2 rounded">
                      "{selectedText.slice(0, 100)}{selectedText.length > 100 ? '...' : ''}"
                    </p>
                  </Card>
                )}

                {/* Instructions */}
                {!selectedText && comments.length === 0 && (
                  <Card className="p-4">
                    <div className="text-center">
                      <MessageSquare className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                      <p className="text-sm font-medium mb-1">Add Comments</p>
                      <p className="text-xs text-muted-foreground">
                        Select text in the editor to add a comment or suggestion
                      </p>
                    </div>
                  </Card>
                )}

                {/* Pending Comments */}
                {comments.filter(c => c.status === 'pending').length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                      <Clock className="h-4 w-4 text-yellow-500" />
                      Pending ({comments.filter(c => c.status === 'pending').length})
                    </h4>
                    {comments.filter(c => c.status === 'pending').map((comment) => (
                      <Card
                        key={comment.id}
                        className={`p-3 cursor-pointer hover:bg-muted/50 transition-colors ${activeCommentId === comment.id ? 'ring-2 ring-primary bg-primary/5' : ''}`}
                        onClick={() => setActiveCommentId(activeCommentId === comment.id ? null : comment.id)}
                      >
                        <div className="flex items-start gap-2 mb-2">
                          <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-medium text-primary">
                              {comment.author_name?.charAt(0) || '?'}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium">{comment.author_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {new Date(comment.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="bg-muted p-2 rounded text-xs mb-2 border border-border">
                          <span className="text-muted-foreground">On: </span>
                          "{comment.selected_text.slice(0, 50)}{comment.selected_text.length > 50 ? '...' : ''}"
                        </div>
                        <p className="text-sm mb-2">{comment.comment}</p>
                        {comment.suggestion && (
                          <div className="bg-primary/10 p-2 rounded text-xs mb-2 border border-primary/20">
                            <span className="font-medium text-primary">Suggestion: </span>
                            {comment.suggestion}
                          </div>
                        )}
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="flex-1 h-7 text-xs hover:bg-primary/10 hover:text-primary hover:border-primary"
                            onClick={(e) => { e.stopPropagation(); acceptComment(comment.id, comment.suggestion); }}
                          >
                            <CheckCircle className="h-3 w-3 mr-1" />
                            {comment.suggestion ? 'Accept' : 'Resolve'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="flex-1 h-7 text-xs hover:bg-destructive/10 hover:text-destructive hover:border-destructive"
                            onClick={(e) => { e.stopPropagation(); rejectComment(comment.id); }}
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            Reject
                          </Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Resolved Comments */}
                {comments.filter(c => c.status !== 'pending').length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      Resolved ({comments.filter(c => c.status !== 'pending').length})
                    </h4>
                    {comments.filter(c => c.status !== 'pending').map((comment) => (
                      <Card
                        key={comment.id}
                        className={`p-3 opacity-60 cursor-pointer hover:opacity-80 transition-opacity ${activeCommentId === comment.id ? 'ring-2 ring-primary opacity-100' : ''}`}
                        onClick={() => {
                          setActiveCommentId(comment.id);
                          setViewingComment({
                            id: comment.id,
                            author_name: comment.author_name,
                            selected_text: comment.selected_text,
                            comment: comment.comment,
                            suggestion: comment.suggestion,
                            status: comment.status as 'accepted' | 'rejected',
                            resolved_by_name: comment.resolved_by_name,
                            resolved_at: comment.resolved_at
                          });
                        }}
                      >
                        <div className="flex items-start gap-2 mb-2">
                          <div className="h-6 w-6 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-medium">
                              {comment.author_name?.charAt(0) || '?'}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium">{comment.author_name}</p>
                            <Badge variant={comment.status === 'accepted' ? 'default' : 'secondary'} className="text-xs mt-1">
                              {comment.status === 'accepted' ? 'Accepted' : 'Rejected'}
                            </Badge>
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{comment.comment}</p>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
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

      {/* Link Insert Dialog */}
      <Dialog open={linkDialogOpen} onOpenChange={(open) => {
        setLinkDialogOpen(open);
        if (!open) {
          setLinkUrl("");
          setLinkText("");
          setLinkRel("dofollow");
          setEditingLinkElement(null);
          linkSelectionRef.current = null;
        }
      }}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link className="h-5 w-5" />
              {editingLinkElement ? "Edit Link" : "Insert Link"}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="linkText">Link Text</Label>
              <Input
                id="linkText"
                placeholder="Text to display"
                value={linkText}
                onChange={(e) => setLinkText(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Leave empty to use the URL as link text
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="linkUrl">URL</Label>
              <Input
                id="linkUrl"
                placeholder="https://example.com"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="linkTarget">Target</Label>
                <Select value={linkTarget} onValueChange={(value: "_self" | "_blank") => setLinkTarget(value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select target" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="_self">Same window</SelectItem>
                    <SelectItem value="_blank">New window</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="linkRel">Link Type</Label>
                <Select value={linkRel} onValueChange={setLinkRel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dofollow">Dofollow</SelectItem>
                    <SelectItem value="nofollow">Nofollow</SelectItem>
                    <SelectItem value="sponsored">Sponsored</SelectItem>
                    <SelectItem value="ugc">UGC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setLinkDialogOpen(false);
              setLinkUrl("");
              setLinkText("");
              setLinkRel("dofollow");
              setEditingLinkElement(null);
              linkSelectionRef.current = null;
            }}>
              Cancel
            </Button>
            <Button onClick={handleInsertLink} disabled={!linkUrl}>
              {editingLinkElement ? "Update Link" : "Insert Link"}
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

      {/* Meta Details Dialog */}
      <Dialog open={metaDetailsDialogOpen} onOpenChange={setMetaDetailsDialogOpen}>
        <DialogContent className="sm:max-w-[550px]" onOpenAutoFocus={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Meta Details
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="metaTitle">Meta Title</Label>
              <Input
                id="metaTitle"
                placeholder="Enter meta title (recommended ~60 characters)"
                value={editMetaTitle}
                onChange={(e) => setEditMetaTitle(e.target.value)}
                maxLength={200}
              />
              <p className={`text-xs ${editMetaTitle.length > 60 ? 'text-amber-600' : 'text-muted-foreground'}`}>
                {editMetaTitle.length}/60 characters (recommended)
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="metaDescription">Meta Description</Label>
              <Textarea
                id="metaDescription"
                placeholder="Enter meta description (recommended ~160 characters)"
                value={editMetaDescription}
                onChange={(e) => setEditMetaDescription(e.target.value)}
                rows={3}
                maxLength={300}
              />
              <p className={`text-xs ${editMetaDescription.length > 160 ? 'text-amber-600' : 'text-muted-foreground'}`}>
                {editMetaDescription.length}/160 characters (recommended)
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setMetaDetailsDialogOpen(false)}
              disabled={isSavingMeta}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveMetaDetails}
              disabled={isSavingMeta}
            >
              {isSavingMeta ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Meta Details
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

      {/* Internal Link Opportunities Modal */}
      <Dialog open={linkOpportunitiesModalOpen} onOpenChange={setLinkOpportunitiesModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Internal Link Opportunities</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            {linkOpportunities.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                No link opportunities found
              </div>
            ) : (
              <div className="border rounded-lg">
                <table className="w-full">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr className="border-b">
                      <th className="p-3 text-left w-12">
                        <Checkbox
                          checked={selectedLinkOpportunities.size === linkOpportunities.length && linkOpportunities.length > 0}
                          onCheckedChange={(checked) => toggleAllLinkOpportunities(!!checked)}
                        />
                      </th>
                      <th className="p-3 text-left text-sm font-medium">Target Text</th>
                      <th className="p-3 text-left text-sm font-medium">Topic</th>
                      <th className="p-3 text-left text-sm font-medium">Target Link</th>
                      <th className="p-3 text-center text-sm font-medium w-20">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {linkOpportunities.map((opportunity) => {
                      const key = getLinkOpportunityKey(opportunity);
                      const isSelected = selectedLinkOpportunities.has(key);
                      return (
                        <tr
                          key={key}
                          className={`border-b last:border-b-0 hover:bg-muted/30 cursor-pointer ${isSelected ? 'bg-primary/5' : ''}`}
                          onClick={() => toggleLinkOpportunitySelection(opportunity)}
                        >
                          <td className="p-3">
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleLinkOpportunitySelection(opportunity)}
                              onClick={(e) => e.stopPropagation()}
                            />
                          </td>
                          <td className="p-3">
                            <span className="font-medium">{opportunity.keyword}</span>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground">
                            {opportunity.topic}
                          </td>
                          <td className="p-3">
                            <a
                              href={opportunity.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-primary hover:underline flex items-center gap-1 max-w-[250px] truncate"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {opportunity.url}
                              <ExternalLink className="h-3 w-3 flex-shrink-0" />
                            </a>
                          </td>
                          <td className="p-3 text-center">
                            <Badge variant="secondary">{opportunity.count}</Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <DialogFooter className="flex items-center justify-between border-t pt-4">
            <div className="text-sm text-muted-foreground">
              {selectedLinkOpportunities.size} of {linkOpportunities.length} selected
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setLinkOpportunitiesModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleApplySelectedLinks}
                disabled={selectedLinkOpportunities.size === 0 || isApplyingLinks}
              >
                {isApplyingLinks ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Applying...
                  </>
                ) : (
                  <>
                    <Link2 className="h-4 w-4 mr-2" />
                    Apply Selected ({selectedLinkOpportunities.size})
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Comment Dialog */}
      <Dialog open={showCommentDialog} onOpenChange={setShowCommentDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add Comment</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="bg-muted p-3 rounded-lg border border-border">
              <p className="text-xs text-muted-foreground mb-1">Selected text:</p>
              <p className="text-sm">"{selectedText.slice(0, 150)}{selectedText.length > 150 ? '...' : ''}"</p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="commentText">Your Comment *</Label>
              <textarea
                id="commentText"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="What feedback do you have about this text?"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="suggestionText">Suggested Replacement (optional)</Label>
              <textarea
                id="suggestionText"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                placeholder="Suggest alternative text to replace the selection..."
                value={suggestionText}
                onChange={(e) => setSuggestionText(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                If provided, the content owner can accept to replace the selected text with your suggestion.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCommentDialog(false)}>
              Cancel
            </Button>
            <Button onClick={saveComment} disabled={isSavingComment || !commentText.trim()}>
              {isSavingComment ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Adding...</>
              ) : (
                <><MessageSquare className="h-4 w-4 mr-2" /> Add Comment</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Resolved Comment Dialog */}
      <Dialog open={viewingComment !== null} onOpenChange={(open) => {
        if (!open) {
          setViewingComment(null);
          setActiveCommentId(null);
        }
      }}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {viewingComment?.status === 'accepted' ? (
                <><CheckCircle className="h-5 w-5 text-primary" /> Accepted Comment</>
              ) : (
                <><XCircle className="h-5 w-5 text-destructive" /> Rejected Comment</>
              )}
            </DialogTitle>
          </DialogHeader>
          {viewingComment && (
            <div className="grid gap-4 py-4">
              {/* Author Info */}
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <User className="h-4 w-4" />
                <span>Comment by <strong className="text-foreground">{viewingComment.author_name}</strong></span>
              </div>

              {/* Selected Text */}
              <div>
                <Label className="text-xs text-muted-foreground mb-2 block">Original Text</Label>
                <div className="bg-muted p-3 rounded-lg border border-border">
                  <p className="text-sm">"{viewingComment.selected_text}"</p>
                </div>
              </div>

              {/* Comment */}
              <div>
                <Label className="text-xs text-muted-foreground mb-2 block">Comment</Label>
                <div className="bg-muted p-3 rounded-lg border border-border">
                  <p className="text-sm">{viewingComment.comment}</p>
                </div>
              </div>

              {/* Suggestion (if any) */}
              {viewingComment.suggestion && (
                <div>
                  <Label className="text-xs text-muted-foreground mb-2 block">
                    Suggested Change {viewingComment.status === 'accepted' && <Badge variant="default" className="ml-2 text-xs">Applied</Badge>}
                  </Label>
                  <div className={`p-3 rounded-lg border ${viewingComment.status === 'accepted' ? 'bg-primary/10 border-primary/20' : 'bg-muted border-border'}`}>
                    <p className="text-sm">{viewingComment.suggestion}</p>
                  </div>
                </div>
              )}

              {/* Resolution Info */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground border-t pt-3">
                <Clock className="h-3 w-3" />
                <span>
                  {viewingComment.status === 'accepted' ? 'Accepted' : 'Rejected'} by {viewingComment.resolved_by_name || 'Unknown'}
                  {viewingComment.resolved_at && ` on ${new Date(viewingComment.resolved_at).toLocaleDateString()}`}
                </span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setViewingComment(null);
              setActiveCommentId(null);
            }}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Humanise Checklist Progress Dialog */}
      <Dialog
        open={humaniseChecklistOpen}
        onOpenChange={(open) => {
          // Only allow closing when humanisation is not actively processing
          if (!open && humaniseStatus !== 'processing') {
            setHumaniseChecklistOpen(false);
          }
        }}
      >
        <DialogContent className="sm:max-w-[480px]" onPointerDownOutside={(e) => {
          // Prevent closing by clicking outside while processing
          if (humaniseStatus === 'processing') e.preventDefault();
        }} onEscapeKeyDown={(e) => {
          // Prevent closing with Escape while processing
          if (humaniseStatus === 'processing') e.preventDefault();
        }}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5" />
              Humanising Content
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5 max-h-[400px] overflow-y-auto py-2">
            {HUMANISE_RULES.map((rule, index) => {
              const isCompleted = index < humaniseChecklistProgress;
              const isActive = index === humaniseChecklistProgress && humaniseStatus === 'processing';
              const isDone = humaniseChecklistProgress >= HUMANISE_RULES.length;

              return (
                <div
                  key={index}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md transition-colors ${
                    isCompleted ? 'bg-green-50 dark:bg-green-950/30' :
                    isActive ? 'bg-blue-50 dark:bg-blue-950/30' :
                    ''
                  }`}
                >
                  {isCompleted || isDone ? (
                    <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 text-blue-500 animate-spin flex-shrink-0" />
                  ) : (
                    <CircleDashed className="h-4 w-4 text-muted-foreground/40 flex-shrink-0" />
                  )}
                  <span className={`text-sm ${
                    isCompleted || isDone ? 'text-green-700 dark:text-green-400' :
                    isActive ? 'text-blue-700 dark:text-blue-400 font-medium' :
                    'text-muted-foreground/60'
                  }`}>
                    {rule}
                  </span>
                </div>
              );
            })}
          </div>
          {humaniseChecklistProgress >= HUMANISE_RULES.length && (
            <div className="flex items-center gap-2 pt-2 border-t">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Humanisation complete!
              </span>
            </div>
          )}
          {humaniseStatus === 'processing' && (
            <div className="flex items-center gap-2 pt-2 border-t">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">
                This may take a minute. Please wait...
              </span>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContentEditor;
