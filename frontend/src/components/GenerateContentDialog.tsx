import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useDomainStore } from "@/stores/domainStore";
import apiClient from "@/services/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { RichTextArea } from "@/components/ui/rich-text-area";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  FileText,
  Book,
  GitCompare,
  List,
  Wrench,
  Sparkles,
  Calendar,
  Target,
  CheckCircle2,
  ArrowRight,
  Rocket,
  Briefcase,
  Package,
  LayoutGrid,
  BookOpen,
  Link2,
  Video,
  Image,
  Plus,
  X,
  Globe,
  GripVertical,
  Trash2,
  Edit3,
  ChevronDown,
  ChevronUp,
  ListOrdered,
  Download,
  Upload,
  Loader2,
  // Social Media icons
  Twitter,
  Linkedin,
  Facebook,
  Instagram,
  Share2,
  // Community icons
  MessageCircle,
  HelpCircle,
  MessagesSquare,
  Mail,
  Users,
  Paperclip,
  Search,
} from "lucide-react";
import mammoth from "mammoth";
import { GSCKeywordsModal } from "./GSCKeywordsModal";

interface GenerateContentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existingContent?: any;
}

export const GenerateContentDialog = ({
  open,
  onOpenChange,
  existingContent
}: GenerateContentDialogProps) => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const { selectedDomain } = useDomainStore();
  const [step, setStep] = useState(1);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [generatedContent, setGeneratedContent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  // GSC keywords state
  const [isLoadingGSCKeywords, setIsLoadingGSCKeywords] = useState(false);
  const [showGSCModal, setShowGSCModal] = useState(false);
  const [gscKeywords, setGscKeywords] = useState<Array<{
    keyword: string;
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
  }>>([]);

  // AI keyword suggestions state (Issue 8B)
  const [isLoadingKeywordSuggestions, setIsLoadingKeywordSuggestions] = useState(false);
  const [isLoadingAnchorSuggestions, setIsLoadingAnchorSuggestions] = useState(false);
  const [keywordSuggestions, setKeywordSuggestions] = useState<Array<{ keyword: string; intent: string; relevance: string }>>([]);
  const [showKeywordSuggestions, setShowKeywordSuggestions] = useState(false);

  // URL fetching state (Issue 8A)
  const [fetchingUrlIndex, setFetchingUrlIndex] = useState<number | null>(null);

  // File upload ref for references (Issue 12)
  const referenceFileInputRef = useRef<HTMLInputElement>(null);
  const [isExtractingFile, setIsExtractingFile] = useState(false);

  // Outline state
  const [outline, setOutline] = useState<Array<{
    id: string;
    type: 'h2' | 'h3';
    title: string;
    key_points: string[];
    estimated_words: number;
  }>>([]);
  const [isGeneratingOutline, setIsGeneratingOutline] = useState(false);
  const [outlineGenerated, setOutlineGenerated] = useState(false);
  // Word count of the outline as first generated/imported. If the user edits
  // the outline in Review Outline (removes/adds/changes sections) the live
  // total will differ from this, which is how we detect an "edited" outline
  // and tell the backend to target the edited count instead of the label.
  const [originalOutlineWords, setOriginalOutlineWords] = useState<number | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formInitializedRef = useRef(false);
  
  const [formData, setFormData] = useState({
    articleType: existingContent?.type || "blog",
    title: existingContent?.title || "",
    keywords: existingContent?.targetKeywords?.join(", ") || "",
    targetCountry: "united_states",
    targetLanguage: "us_english",
    references: [] as Array<{ type: 'article' | 'video' | 'image' | 'text' | 'file'; url: string; description: string }>,
    additionalInstructions: "",
    tone: "",
    style: "",
    keyMessages: "",
    topicsToAvoid: "",
    audience: "general",
    depth: "comprehensive",
    wordCount: existingContent?.wordCount || 1500,
    scheduledDate: existingContent?.scheduledDate || new Date(),
  });

  // Target anchor text -> link pairs. Each exact phrase is worked into the copy
  // and turned into a real <a href> link during generation. Optional.
  const [anchorLinks, setAnchorLinks] = useState<Array<{ anchor_text: string; url: string }>>([]);

  const countries = [
    { id: "united_states", name: "United States" },
    { id: "united_kingdom", name: "United Kingdom" },
    { id: "canada", name: "Canada" },
    { id: "australia", name: "Australia" },
    { id: "germany", name: "Germany" },
    { id: "france", name: "France" },
    { id: "spain", name: "Spain" },
    { id: "italy", name: "Italy" },
    { id: "netherlands", name: "Netherlands" },
    { id: "sweden", name: "Sweden" },
    { id: "norway", name: "Norway" },
    { id: "denmark", name: "Denmark" },
    { id: "finland", name: "Finland" },
    { id: "switzerland", name: "Switzerland" },
    { id: "austria", name: "Austria" },
    { id: "belgium", name: "Belgium" },
    { id: "ireland", name: "Ireland" },
    { id: "portugal", name: "Portugal" },
    { id: "poland", name: "Poland" },
    { id: "india", name: "India" },
    { id: "singapore", name: "Singapore" },
    { id: "japan", name: "Japan" },
    { id: "south_korea", name: "South Korea" },
    { id: "china", name: "China" },
    { id: "brazil", name: "Brazil" },
    { id: "mexico", name: "Mexico" },
    { id: "argentina", name: "Argentina" },
    { id: "south_africa", name: "South Africa" },
    { id: "uae", name: "United Arab Emirates" },
    { id: "saudi_arabia", name: "Saudi Arabia" },
    { id: "global", name: "Global (No specific country)" },
  ];

  const languages = [
    { id: "us_english", name: "US English" },
    { id: "uk_english", name: "UK English" },
    { id: "australian_english", name: "Australian English" },
    { id: "canadian_english", name: "Canadian English" },
    { id: "indian_english", name: "Indian English" },
    { id: "irish_english", name: "Irish English" },
    { id: "south_african_english", name: "South African English" },
    { id: "new_zealand_english", name: "New Zealand English" },
    { id: "singapore_english", name: "Singapore English" },
  ];

  // Helper function to map free-text domain values to dropdown options
  const mapDomainValueToOption = (
    value: string | null | undefined,
    options: string[],
    defaultValue: string
  ): string => {
    if (!value) return defaultValue;
    const lowerValue = value.toLowerCase();

    // Try to find a matching option
    for (const option of options) {
      if (lowerValue.includes(option.toLowerCase())) {
        return option;
      }
    }
    return defaultValue;
  };

  // Get content guidelines from selected domain
  const domainGuidelines = selectedDomain ? {
    toneOfVoice: selectedDomain.tone_of_voice || null,
    contentStyle: selectedDomain.content_style || null,
    targetAudience: selectedDomain.target_audience || null,
    keyMessages: selectedDomain.key_messages || null,
    topicsToAvoid: selectedDomain.topics_to_avoid || null,
    brandValues: selectedDomain.brand_values || null,
    keyCompetitors: selectedDomain.key_competitors || null,
  } : null;

  // Check if domain has any content guidelines set
  const hasContentGuidelines = domainGuidelines && (
    domainGuidelines.toneOfVoice ||
    domainGuidelines.contentStyle ||
    domainGuidelines.targetAudience ||
    domainGuidelines.keyMessages ||
    domainGuidelines.topicsToAvoid
  );

  // Reset state when dialog closes, initialize when it opens
  useEffect(() => {
    if (!open) {
      // Dialog closed - reset everything for next time
      setStep(1);
      setProgress(0);
      setIsGenerating(false);
      setError(null);
      setShowSuccess(false);
      setGeneratedContent(null);
      // Reset outline state
      setOutline([]);
      setOutlineGenerated(false);
      setOriginalOutlineWords(null);
      setIsGeneratingOutline(false);
      setEditingSection(null);
      // Anchor links are per-article. Without this they survive the close and
      // get injected into the NEXT article generated from this dialog.
      setAnchorLinks([]);
      // Allow form re-initialization on next open
      formInitializedRef.current = false;
    }
  }, [open]);

  // Initialize form data once when dialog opens
  // Uses a ref flag to prevent re-initialization when selectedDomain
  // object reference changes (e.g., from background store updates)
  useEffect(() => {
    if (open && !showSuccess && !formInitializedRef.current) {
      formInitializedRef.current = true;

      // Map domain guidelines to form fields (editable text)
      const audienceOptions = ["general", "beginners", "professionals", "experts"];
      const mappedAudience = mapDomainValueToOption(
        domainGuidelines?.targetAudience,
        audienceOptions,
        "general"
      );

      setFormData({
        articleType: existingContent?.type || "blog",
        title: existingContent?.title || "",
        keywords: Array.isArray(existingContent?.targetKeywords)
          ? existingContent.targetKeywords.join(", ")
          : (existingContent?.targetKeywords || ""),
        targetCountry: "united_states",
        targetLanguage: "us_english",
        references: [],
        additionalInstructions: "",
        tone: domainGuidelines?.toneOfVoice || "",
        style: domainGuidelines?.contentStyle || "",
        keyMessages: domainGuidelines?.keyMessages || "",
        topicsToAvoid: domainGuidelines?.topicsToAvoid || "",
        audience: mappedAudience,
        depth: "comprehensive",
        wordCount: existingContent?.wordCount || 1500,
        scheduledDate: existingContent?.scheduledDate || new Date(),
      });
    }
  }, [existingContent, open, showSuccess, selectedDomain]);

  const articleTypes = [
    {
      id: "blog",
      icon: FileText,
      title: "Blog Post",
      description: "General informational content for your blog",
      examples: ["Industry insights", "Company updates", "Educational content"]
    },
    {
      id: "guide",
      icon: Book,
      title: "How-to Guide",
      description: "Step-by-step instructional content",
      examples: ["Tutorials", "DIY guides", "Process explanations"]
    },
    {
      id: "comparison",
      icon: GitCompare,
      title: "Comparison Article",
      description: "Side-by-side analysis of multiple options",
      examples: ["A vs B articles", "Best alternatives", "Feature comparisons"]
    },
    {
      id: "listicle",
      icon: List,
      title: "Listicle",
      description: "List-based content with numbered or bulleted items",
      examples: ["Top 10 lists", "Best practices", "Resource roundups"]
    },
    {
      id: "technical",
      icon: Wrench,
      title: "Technical Article",
      description: "In-depth technical documentation or analysis",
      examples: ["API documentation", "Technical deep-dives", "Implementation guides"]
    }
  ];

  const webPageTypes = [
    {
      id: "landing_page",
      icon: Rocket,
      title: "Landing Page",
      description: "Conversion-focused pages for campaigns/products",
      examples: ["Product launch", "Campaign page", "Lead capture"]
    },
    {
      id: "services_page",
      icon: Briefcase,
      title: "Services Page",
      description: "Description of services offered",
      examples: ["Service overview", "What we offer", "Solutions"]
    },
    {
      id: "product_page",
      icon: Package,
      title: "Product Page",
      description: "Product descriptions, features, specifications",
      examples: ["Product details", "Features & specs", "Pricing info"]
    },
    {
      id: "features_page",
      icon: LayoutGrid,
      title: "Features Page",
      description: "Detailed feature breakdowns",
      examples: ["Feature list", "Capabilities", "What's included"]
    },
    {
      id: "resource_page",
      icon: BookOpen,
      title: "Resource/Guide Page",
      description: "Downloadable content landing pages",
      examples: ["Ebook landing", "Whitepaper", "Free guide"]
    }
  ];

  const socialMediaTypes = [
    {
      id: "twitter_post",
      icon: Twitter,
      title: "Twitter/X Post",
      description: "Short, punchy posts with hashtags (280 chars)",
      examples: ["Announcements", "Tips & insights", "Engagement posts"]
    },
    {
      id: "linkedin_post",
      icon: Linkedin,
      title: "LinkedIn Post",
      description: "Professional thought leadership content",
      examples: ["Industry insights", "Career advice", "Company updates"]
    },
    {
      id: "facebook_post",
      icon: Facebook,
      title: "Facebook Post",
      description: "Engaging community-focused content",
      examples: ["Community updates", "Event promotions", "Story sharing"]
    },
    {
      id: "instagram_caption",
      icon: Instagram,
      title: "Instagram Caption",
      description: "Visual-focused captions with CTAs",
      examples: ["Product showcases", "Behind-the-scenes", "User stories"]
    },
    {
      id: "social_thread",
      icon: ListOrdered,
      title: "Thread/Carousel",
      description: "Multi-part content series for storytelling",
      examples: ["Educational threads", "Story breakdowns", "Tips series"]
    }
  ];

  const communityPostTypes = [
    {
      id: "reddit_post",
      icon: MessageCircle,
      title: "Reddit Post",
      description: "Discussion-style content for subreddits",
      examples: ["AMAs", "Discussion starters", "Resource sharing"]
    },
    {
      id: "quora_answer",
      icon: HelpCircle,
      title: "Quora Answer",
      description: "Detailed expert answers to questions",
      examples: ["How-to answers", "Expert opinions", "Comparisons"]
    },
    {
      id: "forum_post",
      icon: MessagesSquare,
      title: "Forum Post",
      description: "Community discussion & help content",
      examples: ["Tutorials", "Q&A responses", "Community guides"]
    },
    {
      id: "product_hunt",
      icon: Rocket,
      title: "Product Hunt Launch",
      description: "Launch day content & descriptions",
      examples: ["Product taglines", "Feature highlights", "Maker stories"]
    },
    {
      id: "newsletter_snippet",
      icon: Mail,
      title: "Newsletter Snippet",
      description: "Email newsletter sections & updates",
      examples: ["Weekly roundups", "Feature announcements", "Tips & tricks"]
    }
  ];

  // Update word count default when content type changes
  useEffect(() => {
    const isSocialMedia = socialMediaTypes.some(t => t.id === formData.articleType);
    const isCommunity = communityPostTypes.some(t => t.id === formData.articleType);

    // Allowed dropdown values for each content-type bucket. Must match the
    // <SelectItem value="..."> entries rendered below.
    const mainArticleOptions = [300, 800, 1500, 2500, 3500];
    const socialMediaOptions = [50, 150, 300, 500];
    const communityOptions = [150, 400, 800, 1500];

    if (isSocialMedia && !socialMediaOptions.includes(formData.wordCount)) {
      setFormData(prev => ({ ...prev, wordCount: 150 }));
    } else if (isCommunity && !communityOptions.includes(formData.wordCount)) {
      setFormData(prev => ({ ...prev, wordCount: 400 }));
    } else if (!isSocialMedia && !isCommunity && !mainArticleOptions.includes(formData.wordCount)) {
      setFormData(prev => ({ ...prev, wordCount: 1500 }));
    }
  }, [formData.articleType]);

  // Advance the wizard, but enforce required fields on the Content Details step
  // (step 2) so the "keywords required" error surfaces HERE, next to the field,
  // instead of later on the outline/generation step.
  const handleNextStep = () => {
    if (step === 2) {
      if (!formData.title.trim()) {
        toast({
          title: "Title required",
          description: "Please enter a title before continuing.",
          variant: "destructive",
        });
        return;
      }
      if (!formData.keywords.trim()) {
        toast({
          title: "Keywords required",
          description: "Please add at least one keyword before continuing.",
          variant: "destructive",
        });
        return;
      }
    }
    setStep(step + 1);
  };

  const handleGenerate = async () => {
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "Please select a domain first",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);
    setProgress(0);
    setError(null);
    setGeneratedContent(null);

    // Simulate progress for UX
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 5;
      });
    }, 1000);

    try {
      // Use enriched source reference if already built, otherwise use default
      const sourceReference = existingContent?.sourceReference || formData.title;

      // Prepare generation request
      const generationData = {
        domain_id: selectedDomain.id,
        title: formData.title,
        keywords: formData.keywords,
        article_type: formData.articleType,
        target_country: formData.targetCountry,
        target_language: formData.targetLanguage,
        references: formData.references.filter(ref => ref.type === 'text' ? ref.description.trim() !== '' : ref.url.trim() !== ''),
        tone: formData.tone,
        style: formData.style,
        goal: 'educate', // Default goal
        audience: formData.audience,
        depth: formData.depth,
        word_count: formData.wordCount,
        anchor_links: anchorLinks.filter(l => l.anchor_text.trim() && l.url.trim()),
        source_type: existingContent?.sourceType || 'manual',
        source_id: existingContent?.sourceId,
        source_reference: sourceReference,
        priority: existingContent?.priority || 'medium',
        scheduled_date: formData.scheduledDate instanceof Date
          ? formData.scheduledDate.toISOString().split('T')[0]  // Convert to YYYY-MM-DD format
          : formData.scheduledDate,
        // Content guidelines from form (editable)
        key_messages: formData.keyMessages,
        topics_to_avoid: formData.topicsToAvoid,
        additional_instructions: formData.additionalInstructions,
        brand_values: domainGuidelines?.brandValues || '',
      };

      // Log the data being sent for debugging
      console.log('Content generation request:', generationData);

      // Call the API to generate content
      const response = await apiClient.generateContent(generationData);

      clearInterval(progressInterval);
      setProgress(100);

      if (response.status === 'success') {
        setGeneratedContent(response.data);
        setIsGenerating(false);
        setShowSuccess(true);

        toast({
          title: "Content Generated Successfully!",
          description: `Generated ${response.data.actual_word_count} words in ${response.data.generation_time_seconds}s`,
        });
      } else {
        throw new Error(response.message || 'Generation failed');
      }

    } catch (err: any) {
      clearInterval(progressInterval);
      setIsGenerating(false);
      setProgress(0);

      console.error('Content generation error:', err);
      const errorMessage = err.message || 'Failed to generate content. Please try again.';
      setError(errorMessage);

      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  // Create manual outline handler
  const handleCreateManualOutline = () => {
    const initialOutline = [{
      id: `manual-${Date.now()}`,
      type: 'h2' as const,
      title: 'New Section',
      key_points: ['Key point 1'],
      estimated_words: 150,
    }];
    setOutline(initialOutline);
    setOutlineGenerated(true);
    // Snapshot the baseline like the generated/imported paths do. Without it
    // the edited-outline check compares against whatever a PREVIOUS article
    // left behind, so the same actions could send target_word_count or not.
    setOriginalOutlineWords(
      initialOutline.reduce((sum, s) => sum + (s.estimated_words || 0), 0)
    );
  };

  // Generate outline handler
  const handleGenerateOutline = async () => {
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "Please select a domain first",
        variant: "destructive",
      });
      return;
    }

    setIsGeneratingOutline(true);
    setError(null);

    try {
      const outlineData = {
        domain_id: selectedDomain.id,
        title: formData.title,
        keywords: formData.keywords,
        article_type: formData.articleType,
        target_country: formData.targetCountry,
        target_language: formData.targetLanguage,
        // Send the same filtered references the content step uses so the
        // outline is planned around the actual URL content, not blind.
        references: formData.references.filter(ref => ref.type === 'text' ? ref.description.trim() !== '' : ref.url.trim() !== ''),
        tone: formData.tone,
        style: formData.style,
        audience: formData.audience,
        word_count: formData.wordCount,
        anchor_links: anchorLinks.filter(l => l.anchor_text.trim() && l.url.trim()),
        key_messages: formData.keyMessages,
        topics_to_avoid: formData.topicsToAvoid,
        additional_instructions: formData.additionalInstructions,
      };

      console.log('Outline generation request:', outlineData);

      const response = await apiClient.generateOutline(outlineData);

      if (response.status === 'success') {
        setOutline(response.data.outline);
        setOutlineGenerated(true);
        // Snapshot the freshly generated outline's word count as the baseline.
        setOriginalOutlineWords(
          response.data.outline.reduce((sum: number, s: any) => sum + (s.estimated_words || 0), 0)
        );

        toast({
          title: "Outline Generated!",
          description: `Created ${response.data.outline.length} sections in ${response.data.generation_time_seconds}s`,
        });
      } else {
        throw new Error(response.message || 'Outline generation failed');
      }

    } catch (err: any) {
      console.error('Outline generation error:', err);
      const errorMessage = err.message || 'Failed to generate outline. Please try again.';
      setError(errorMessage);

      toast({
        title: "Outline Generation Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsGeneratingOutline(false);
    }
  };

  // Generate content from outline handler
  const handleGenerateFromOutline = async () => {
    if (!selectedDomain || outline.length === 0) {
      toast({
        title: "Error",
        description: "Please generate an outline first",
        variant: "destructive",
      });
      return;
    }

    setIsGenerating(true);
    setProgress(0);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 3;
      });
    }, 1000);

    try {
      const sourceReference = existingContent?.sourceReference || formData.title;

      const generationData = {
        domain_id: selectedDomain.id,
        title: formData.title,
        keywords: formData.keywords,
        article_type: formData.articleType,
        target_country: formData.targetCountry,
        target_language: formData.targetLanguage,
        references: formData.references.filter(ref => ref.type === 'text' ? ref.description.trim() !== '' : ref.url.trim() !== ''),
        tone: formData.tone,
        style: formData.style,
        goal: 'educate',
        audience: formData.audience,
        depth: formData.depth,
        word_count: formData.wordCount,
        anchor_links: anchorLinks.filter(l => l.anchor_text.trim() && l.url.trim()),
        source_type: existingContent?.sourceType || 'manual',
        source_id: existingContent?.sourceId,
        source_reference: sourceReference,
        priority: existingContent?.priority || 'medium',
        scheduled_date: formData.scheduledDate instanceof Date
          ? formData.scheduledDate.toISOString().split('T')[0]
          : formData.scheduledDate,
        key_messages: formData.keyMessages,
        topics_to_avoid: formData.topicsToAvoid,
        additional_instructions: formData.additionalInstructions,
        brand_values: domainGuidelines?.brandValues || '',
        outline: outline,
      };

      // If the user edited the outline in Review Outline, its live word total
      // now differs from the baseline captured at generation. In that case
      // target the edited count; otherwise leave length to the label.
      const currentOutlineWords = outline.reduce((sum, s) => sum + (s.estimated_words || 0), 0);
      if (originalOutlineWords !== null && currentOutlineWords !== originalOutlineWords && currentOutlineWords > 0) {
        (generationData as any).target_word_count = currentOutlineWords;
      }

      console.log('Content from outline request:', generationData);

      const response = await apiClient.generateContentFromOutline(generationData);

      clearInterval(progressInterval);
      setProgress(100);

      if (response.status === 'success') {
        setGeneratedContent(response.data);
        setIsGenerating(false);
        setShowSuccess(true);

        toast({
          title: "Content Generated Successfully!",
          description: `Generated ${response.data.actual_word_count} words in ${response.data.generation_time_seconds}s`,
        });
      } else {
        throw new Error(response.message || 'Generation failed');
      }

    } catch (err: any) {
      clearInterval(progressInterval);
      setIsGenerating(false);
      setProgress(0);

      console.error('Content generation error:', err);
      const errorMessage = err.message || 'Failed to generate content. Please try again.';
      setError(errorMessage);

      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  // Outline editing functions
  const updateSectionTitle = (id: string, newTitle: string) => {
    setOutline(prev => prev.map(section =>
      section.id === id ? { ...section, title: newTitle } : section
    ));
  };

  const updateKeyPoint = (sectionId: string, pointIndex: number, newValue: string) => {
    setOutline(prev => prev.map(section =>
      section.id === sectionId
        ? {
            ...section,
            key_points: section.key_points.map((point, i) =>
              i === pointIndex ? newValue : point
            )
          }
        : section
    ));
  };

  const addKeyPoint = (sectionId: string) => {
    setOutline(prev => prev.map(section =>
      section.id === sectionId
        ? { ...section, key_points: [...section.key_points, 'New point'] }
        : section
    ));
  };

  const removeKeyPoint = (sectionId: string, pointIndex: number) => {
    setOutline(prev => prev.map(section =>
      section.id === sectionId
        ? {
            ...section,
            key_points: section.key_points.filter((_, i) => i !== pointIndex)
          }
        : section
    ));
  };

  const removeSection = (id: string) => {
    setOutline(prev => prev.filter(section => section.id !== id));
  };

  const moveSection = (id: string, direction: 'up' | 'down') => {
    setOutline(prev => {
      const index = prev.findIndex(s => s.id === id);
      if (index === -1) return prev;
      if (direction === 'up' && index === 0) return prev;
      if (direction === 'down' && index === prev.length - 1) return prev;

      const newOutline = [...prev];
      const targetIndex = direction === 'up' ? index - 1 : index + 1;
      [newOutline[index], newOutline[targetIndex]] = [newOutline[targetIndex], newOutline[index]];
      return newOutline;
    });
  };

  const addSection = (type: 'h2' | 'h3') => {
    const newId = `new-${Date.now()}`;
    setOutline(prev => [...prev, {
      id: newId,
      type,
      title: type === 'h2' ? 'New Section' : 'New Subsection',
      key_points: ['Key point 1'],
      estimated_words: 150
    }]);
  };

  // Handle Word document upload → parse into outline sections
  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const maxSize = 10 * 1024 * 1024; // 10MB limit

    if (file.size > maxSize) {
      toast({
        title: "File Too Large",
        description: `${file.name} exceeds the 10MB limit`,
        variant: "destructive",
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    try {
      // Read file as ArrayBuffer for mammoth
      const arrayBuffer = await file.arrayBuffer();
      const result = await mammoth.convertToHtml({ arrayBuffer });
      const html = result.value;

      // Parse the HTML to extract headings and content into outline sections
      // Supports both:
      //   1. Actual Word heading styles (h1/h2/h3 tags from mammoth)
      //   2. Text prefixes like "H1: Title", "H2: Title", "H3: Title" in plain paragraphs
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const elements = Array.from(doc.body.children);

      // Regex to detect text-based heading prefixes: "H1: Title", "H2: Title", "H3: Title"
      const h2PrefixRegex = /^H[12]:\s*(.+)$/i;
      const h3PrefixRegex = /^H[34]:\s*(.+)$/i;
      // Regex to detect bullet points: "• text" or "- text" or "* text"
      const bulletRegex = /^[•\-\*]\s*(.+)$/;

      const parsedOutline: Array<{
        id: string;
        type: 'h2' | 'h3';
        title: string;
        key_points: string[];
        estimated_words: number;
      }> = [];

      let currentSection: typeof parsedOutline[0] | null = null;

      const startNewSection = (type: 'h2' | 'h3', title: string) => {
        if (currentSection) parsedOutline.push(currentSection);
        currentSection = {
          id: `doc-${Date.now()}-${parsedOutline.length}`,
          type,
          title,
          key_points: [],
          estimated_words: 0,
        };
      };

      const addKeyPoint = (text: string) => {
        if (!currentSection) {
          // Content before any heading → create a default Introduction section
          startNewSection('h2', 'Introduction');
        }
        currentSection!.key_points.push(text);
        currentSection!.estimated_words += text.split(/\s+/).length;
      };

      for (const el of elements) {
        const tag = el.tagName.toLowerCase();
        const text = el.textContent?.trim() || '';

        // 1. Check actual HTML heading tags (from Word heading styles)
        if (tag === 'h1' || tag === 'h2') {
          startNewSection('h2', text || 'Untitled Section');
          continue;
        }
        if (tag === 'h3' || tag === 'h4') {
          startNewSection('h3', text || 'Untitled Subsection');
          continue;
        }

        // 2. Check for text-based heading prefixes in paragraphs (e.g., "H2: What is SEO?")
        if (tag === 'p' && text) {
          const h2Match = text.match(h2PrefixRegex);
          if (h2Match) {
            startNewSection('h2', h2Match[1].trim());
            continue;
          }
          const h3Match = text.match(h3PrefixRegex);
          if (h3Match) {
            startNewSection('h3', h3Match[1].trim());
            continue;
          }

          // 3. Check for bullet points in paragraph text (• item or - item)
          const bulletMatch = text.match(bulletRegex);
          if (bulletMatch) {
            addKeyPoint(bulletMatch[1].trim());
            continue;
          }

          // 4. Regular paragraph → key point
          addKeyPoint(text);
          continue;
        }

        // 5. Handle list elements
        if (tag === 'ul' || tag === 'ol') {
          const items = Array.from(el.querySelectorAll('li'));
          items.forEach(li => {
            const liText = li.textContent?.trim();
            if (liText) addKeyPoint(liText);
          });
          continue;
        }

        // 6. Any other element with text
        if (text) addKeyPoint(text);
      }

      // Push the last section
      if (currentSection) parsedOutline.push(currentSection);

      if (parsedOutline.length === 0) {
        toast({
          title: "No Structure Found",
          description: "The document doesn't contain any headings. Please use a document with H1/H2/H3 headings.",
          variant: "destructive",
        });
      } else {
        setOutline(parsedOutline);
        setOutlineGenerated(true);
        setOriginalOutlineWords(
          parsedOutline.reduce((sum: number, s: any) => sum + (s.estimated_words || 0), 0)
        );

        toast({
          title: "Document Parsed",
          description: `Extracted ${parsedOutline.length} sections from ${file.name}`,
        });
      }
    } catch {
      toast({
        title: "Upload Failed",
        description: "Could not parse the Word document. Please ensure it's a valid .docx file.",
        variant: "destructive",
      });
    }

    // Reset input so the same file can be re-uploaded
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Pull keywords from GSC
  const handlePullFromGSC = async () => {
    console.log("selectedDomain: ", selectedDomain)
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "Please select a domain first",
        variant: "destructive",
      });
      return;
    }

    setIsLoadingGSCKeywords(true);
    setShowGSCModal(true);

    try {
      const response = await apiClient.getGSCKeywords(selectedDomain.id, formData.title || undefined);

      if (!response.connected) {
        setShowGSCModal(false);
        toast({
          title: "GSC Not Connected",
          description: response.message || "Google Search Console is not connected for this domain. Please connect it in Settings.",
          variant: "destructive",
        });
        return;
      }

      if (!response.keywords || response.keywords.length === 0) {
        setShowGSCModal(false);
        toast({
          title: "No Keywords Found",
          description: response.message || "No GSC data available yet. Please sync your GSC integration first.",
          variant: "destructive",
        });
        return;
      }

      setGscKeywords(response.keywords);

    } catch (err: any) {
      console.error('Error fetching GSC keywords:', err);
      setShowGSCModal(false);
      toast({
        title: "Error",
        description: err.message || "Failed to fetch keywords from GSC",
        variant: "destructive",
      });
    } finally {
      setIsLoadingGSCKeywords(false);
    }
  };

  // Handle adding selected keywords from GSC modal
  const handleAddGSCKeywords = (selectedKeywords: string[]) => {
    if (selectedKeywords.length === 0) return;

    const updatedKeywords = formData.keywords
      ? `${formData.keywords}, ${selectedKeywords.join(', ')}`
      : selectedKeywords.join(', ');

    setFormData({ ...formData, keywords: updatedKeywords });

    toast({
      title: "Keywords Added",
      description: `Added ${selectedKeywords.length} keyword${selectedKeywords.length !== 1 ? 's' : ''} from GSC`,
    });
  };

  // Get existing keywords as array for the modal
  const existingKeywordsArray = formData.keywords
    .split(',')
    .map(k => k.trim())
    .filter(k => k);

  // Issue 8B: AI Keyword Suggestions handler
  const handleSuggestKeywords = async () => {
    if (!formData.title.trim()) {
      toast({
        title: "Title Required",
        description: "Please enter a title first to get keyword suggestions",
        variant: "destructive",
      });
      return;
    }

    setIsLoadingKeywordSuggestions(true);
    try {
      const response = await apiClient.suggestKeywords({
        title: formData.title,
        article_type: formData.articleType,
        domain_url: selectedDomain?.url || '',
        existing_keywords: formData.keywords,
      });

      if (response.status === 'success' && response.data?.suggestions?.length > 0) {
        setKeywordSuggestions(response.data.suggestions);
        setShowKeywordSuggestions(true);
      } else {
        toast({
          title: "No Suggestions",
          description: "Could not generate keyword suggestions. Try adjusting your title.",
        });
      }
    } catch (err: any) {
      console.error('Error suggesting keywords:', err);
      toast({
        title: "Error",
        description: "Failed to generate keyword suggestions",
        variant: "destructive",
      });
    } finally {
      setIsLoadingKeywordSuggestions(false);
    }
  };

  // AI-generate anchor-text -> link pairs and add them to the editable list so
  // the user can review/edit each URL before generating (nothing is inserted
  // into content unreviewed).
  const handleSuggestAnchorLinks = async () => {
    if (!formData.title.trim()) {
      toast({
        title: "Title Required",
        description: "Please enter a title first to get anchor link suggestions",
        variant: "destructive",
      });
      return;
    }

    setIsLoadingAnchorSuggestions(true);
    try {
      const response = await apiClient.suggestAnchorLinks({
        title: formData.title,
        keywords: formData.keywords,
        article_type: formData.articleType,
        domain_id: selectedDomain?.id,
      });

      const suggestions = response.status === 'success' ? (response.data?.suggestions || []) : [];
      if (suggestions.length > 0) {
        setAnchorLinks(prev => {
          const existing = new Set(prev.map(l => `${l.anchor_text}|${l.url}`.toLowerCase()));
          const additions = suggestions
            .filter((s: any) => s.anchor_text && s.url && !existing.has(`${s.anchor_text}|${s.url}`.toLowerCase()))
            .map((s: any) => ({ anchor_text: String(s.anchor_text), url: String(s.url) }));
          return [...prev, ...additions];
        });
        toast({
          title: "Anchor links suggested",
          description: `Added ${suggestions.length} suggestion(s). Review and edit the URLs before generating.`,
        });
      } else {
        toast({
          title: "No Suggestions",
          description: "Could not generate anchor link suggestions. Try adjusting your title or keywords.",
        });
      }
    } catch (err: any) {
      console.error('Error suggesting anchor links:', err);
      toast({
        title: "Error",
        description: "Failed to generate anchor link suggestions",
        variant: "destructive",
      });
    } finally {
      setIsLoadingAnchorSuggestions(false);
    }
  };

  const handleAddSuggestedKeyword = (keyword: string) => {
    const current = formData.keywords.split(',').map(k => k.trim()).filter(k => k);
    if (current.includes(keyword)) return;
    const updated = formData.keywords ? `${formData.keywords}, ${keyword}` : keyword;
    setFormData({ ...formData, keywords: updated });
  };

  // Issue 8A: URL Reading handler
  const handleFetchUrl = async (index: number) => {
    const ref = formData.references[index];
    if (!ref?.url?.trim()) {
      toast({ title: "Error", description: "Please enter a URL first", variant: "destructive" });
      return;
    }

    setFetchingUrlIndex(index);
    try {
      const response = await apiClient.readUrl(ref.url);
      if (response.status === 'success' && response.data) {
        const updated = [...formData.references];
        const pageTitle = response.data.title || '';
        const metaDesc = response.data.description || '';
        const textContent = response.data.text_content || '';

        // Build a clean, structured description
        let description = '';
        if (pageTitle) description += `Title: ${pageTitle}\n`;
        if (metaDesc) description += `Summary: ${metaDesc}\n`;
        if (description) description += '\n';
        description += textContent.substring(0, 2500);

        updated[index] = { ...updated[index], description: description.trim() };
        setFormData({ ...formData, references: updated });
        toast({ title: "URL Content Fetched", description: `Extracted ${response.data.word_count} words from URL` });
      }
    } catch (err: any) {
      console.error('Error fetching URL:', err);
      toast({ title: "Error", description: "Failed to fetch URL content", variant: "destructive" });
    } finally {
      setFetchingUrlIndex(null);
    }
  };

  // Issue 12: File upload handler for references
  const handleReferenceFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input
    if (referenceFileInputRef.current) referenceFileInputRef.current.value = '';

    if (file.size > 10 * 1024 * 1024) {
      toast({ title: "Error", description: "File size must be under 10MB", variant: "destructive" });
      return;
    }

    setIsExtractingFile(true);
    try {
      const response = await apiClient.extractFileText(file);
      if (response.status === 'success' && response.data) {
        setFormData({
          ...formData,
          references: [
            ...formData.references,
            {
              type: 'file' as const,
              url: file.name,
              description: response.data.extracted_text.substring(0, 3000),
            }
          ]
        });
        toast({
          title: "File Processed",
          description: `Extracted ${response.data.word_count} words from ${file.name}`,
        });
      }
    } catch (err: any) {
      console.error('Error extracting file:', err);
      toast({ title: "Error", description: "Failed to extract text from file", variant: "destructive" });
    } finally {
      setIsExtractingFile(false);
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        const currentTab = articleTypes.some(t => t.id === formData.articleType) ? 'articles'
          : webPageTypes.some(t => t.id === formData.articleType) ? 'webpages'
          : socialMediaTypes.some(t => t.id === formData.articleType) ? 'social'
          : communityPostTypes.some(t => t.id === formData.articleType) ? 'community'
          : 'articles';

        return (
          <div className="space-y-4">
            <Tabs defaultValue={currentTab} className="w-full">
              <TabsList className="grid w-full grid-cols-4 mb-4">
                <TabsTrigger value="articles" className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Articles
                </TabsTrigger>
                <TabsTrigger value="webpages" className="flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4" />
                  Web Pages
                </TabsTrigger>
                <TabsTrigger value="social" className="flex items-center gap-2">
                  <Share2 className="h-4 w-4" />
                  Social Media
                </TabsTrigger>
                <TabsTrigger value="community" className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Community
                </TabsTrigger>
              </TabsList>

              <TabsContent value="articles" className="mt-0">
                <p className="text-sm text-muted-foreground mb-4">
                  Blog posts, guides, and informational content
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {articleTypes.map((type) => {
                    const Icon = type.icon;
                    const isSelected = formData.articleType === type.id;

                    return (
                      <Card
                        key={type.id}
                        className={`p-3 cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setFormData({ ...formData, articleType: type.id })}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-sm mb-0.5">{type.title}</h4>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {type.description}
                            </p>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </TabsContent>

              <TabsContent value="webpages" className="mt-0">
                <p className="text-sm text-muted-foreground mb-4">
                  Marketing pages, product pages, and website content
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {webPageTypes.map((type) => {
                    const Icon = type.icon;
                    const isSelected = formData.articleType === type.id;

                    return (
                      <Card
                        key={type.id}
                        className={`p-3 cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setFormData({ ...formData, articleType: type.id })}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0">
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-sm mb-0.5">{type.title}</h4>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {type.description}
                            </p>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </TabsContent>

              <TabsContent value="social" className="mt-0">
                <p className="text-sm text-muted-foreground mb-4">
                  Social media posts, threads, and platform-specific content
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {socialMediaTypes.map((type) => {
                    const Icon = type.icon;
                    const isSelected = formData.articleType === type.id;

                    return (
                      <Card
                        key={type.id}
                        className={`p-3 cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setFormData({ ...formData, articleType: type.id })}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center flex-shrink-0">
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-sm mb-0.5">{type.title}</h4>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {type.description}
                            </p>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </TabsContent>

              <TabsContent value="community" className="mt-0">
                <p className="text-sm text-muted-foreground mb-4">
                  Community forums, Q&A platforms, and discussion content
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {communityPostTypes.map((type) => {
                    const Icon = type.icon;
                    const isSelected = formData.articleType === type.id;

                    return (
                      <Card
                        key={type.id}
                        className={`p-3 cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setFormData({ ...formData, articleType: type.id })}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center flex-shrink-0">
                            <Icon className="h-5 w-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-sm mb-0.5">{type.title}</h4>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {type.description}
                            </p>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        );

      case 2:
        const isWebPage = webPageTypes.some(t => t.id === formData.articleType);
        const isSocialMedia = socialMediaTypes.some(t => t.id === formData.articleType);
        const isCommunity = communityPostTypes.some(t => t.id === formData.articleType);
        const selectedType = [...articleTypes, ...webPageTypes, ...socialMediaTypes, ...communityPostTypes].find(t => t.id === formData.articleType);

        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">Content Details</h3>
              <p className="text-sm text-muted-foreground">
                Provide title and target keywords for your {selectedType?.title || 'content'}
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <Label>
                  {isWebPage ? 'Page Title' : isSocialMedia ? 'Post Topic/Hook' : isCommunity ? 'Post/Answer Title' : 'Article Title'}
                </Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder={
                    isWebPage ? "Transform Your Business with Our Solutions"
                    : isSocialMedia ? "5 game-changing tips for startup founders..."
                    : isCommunity ? "How to optimize React performance in large apps"
                    : "Best Plant-Based Protein Powders for Athletes"
                  }
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>{isSocialMedia ? 'Hashtags/Keywords' : isCommunity ? 'Topics/Tags' : 'Target Keywords'} (comma-separated)</Label>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleSuggestKeywords}
                      disabled={isLoadingKeywordSuggestions}
                      className="h-7 text-xs"
                    >
                      {isLoadingKeywordSuggestions ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Suggesting...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3 w-3 mr-1" />
                          AI Suggest
                        </>
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handlePullFromGSC}
                      disabled={isLoadingGSCKeywords}
                      className="h-7 text-xs"
                    >
                      {isLoadingGSCKeywords ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        <>
                          <Download className="h-3 w-3 mr-1" />
                          Pull from GSC
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                <Textarea
                  value={formData.keywords}
                  onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                  placeholder={
                    isWebPage ? "business solutions, enterprise software, digital transformation"
                    : isSocialMedia ? "#startups, #entrepreneurship, #growthhacking, founder tips"
                    : isCommunity ? "react, performance, optimization, web development"
                    : "plant protein, vegan protein powder, athlete supplements"
                  }
                  rows={3}
                />
                {/* AI Keyword Suggestions Panel */}
                {showKeywordSuggestions && keywordSuggestions.length > 0 && (
                  <div className="mt-2 p-3 bg-muted/50 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-medium">AI Suggested Keywords</p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-5 w-5 p-0"
                        onClick={() => setShowKeywordSuggestions(false)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {keywordSuggestions.map((suggestion, idx) => {
                        const isAdded = existingKeywordsArray.some(
                          k => k.toLowerCase() === suggestion.keyword.toLowerCase()
                        );
                        return (
                          <Badge
                            key={idx}
                            variant={isAdded ? "default" : "outline"}
                            className={`cursor-pointer text-xs ${
                              isAdded ? 'opacity-60' : 'hover:bg-primary/10'
                            } ${
                              suggestion.relevance === 'high' ? 'border-green-500/50' :
                              suggestion.relevance === 'medium' ? 'border-amber-500/50' : ''
                            }`}
                            onClick={() => !isAdded && handleAddSuggestedKeyword(suggestion.keyword)}
                            title={`Intent: ${suggestion.intent} | Relevance: ${suggestion.relevance}${isAdded ? ' (already added)' : ''}`}
                          >
                            {isAdded ? '✓ ' : '+ '}{suggestion.keyword}
                          </Badge>
                        );
                      })}
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-2">Click to add keywords. Green border = high relevance.</p>
                  </div>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {isSocialMedia ? 'Hashtags and keywords to include in your post'
                   : isCommunity ? 'Topics and tags relevant to the community'
                   : 'These keywords will be naturally integrated into your content'}
                </p>
              </div>

              {/* Target Anchor Text -> Link mapping */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>Target Anchor Text &rarr; Link (optional)</Label>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setAnchorLinks([...anchorLinks, { anchor_text: '', url: '' }])}
                    >
                      + Add Link
                    </Button>
                  </div>
                </div>
                {anchorLinks.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Add exact phrases to turn into links in the content, e.g. "payment gateway guide" &rarr; https://yoursite.com/guide
                  </p>
                ) : (
                  <div className="space-y-2">
                    {anchorLinks.map((link, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <Input
                          className="flex-1 h-8 text-sm"
                          placeholder="Anchor text (e.g. payment gateway guide)"
                          value={link.anchor_text}
                          onChange={(e) => {
                            const next = [...anchorLinks];
                            next[idx] = { ...next[idx], anchor_text: e.target.value };
                            setAnchorLinks(next);
                          }}
                        />
                        <Input
                          className="flex-1 h-8 text-sm"
                          placeholder="https://link.com"
                          value={link.url}
                          onChange={(e) => {
                            const next = [...anchorLinks];
                            next[idx] = { ...next[idx], url: e.target.value };
                            setAnchorLinks(next);
                          }}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => setAnchorLinks(anchorLinks.filter((_, i) => i !== idx))}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <p className="text-[10px] text-muted-foreground">
                      Each exact phrase will appear once in the content as a link to its URL.
                    </p>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Target Country</Label>
                  <Select
                    value={formData.targetCountry}
                    onValueChange={(v) => setFormData({ ...formData, targetCountry: v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select country" />
                    </SelectTrigger>
                    <SelectContent>
                      {countries.map((country) => (
                        <SelectItem key={country.id} value={country.id}>
                          {country.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    Content will be localized for this market
                  </p>
                </div>

                <div>
                  <Label>Target Language</Label>
                  <Select
                    value={formData.targetLanguage}
                    onValueChange={(v) => setFormData({ ...formData, targetLanguage: v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select language" />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((language) => (
                        <SelectItem key={language.id} value={language.id}>
                          {language.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    Content will be written in this language
                  </p>
                </div>
              </div>
            </div>
          </div>
        );

      case 3:
        const addReference = (type: 'article' | 'video' | 'image' | 'text' | 'file') => {
          setFormData({
            ...formData,
            references: [...formData.references, { type, url: '', description: '' }]
          });
        };

        const removeReference = (index: number) => {
          setFormData({
            ...formData,
            references: formData.references.filter((_, i) => i !== index)
          });
        };

        const updateReference = (index: number, field: 'url' | 'description', value: string) => {
          const updated = [...formData.references];
          updated[index] = { ...updated[index], [field]: value };
          setFormData({ ...formData, references: updated });
        };

        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">References</h3>
              <p className="text-sm text-muted-foreground">
                Add articles, videos, images, or text as reference material for content generation (optional)
              </p>
            </div>

            {/* Add Reference Buttons */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addReference('article')}
                className="flex items-center gap-2"
              >
                <Globe className="h-4 w-4" />
                Add Article URL
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addReference('video')}
                className="flex items-center gap-2"
              >
                <Video className="h-4 w-4" />
                Add Video URL
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addReference('image')}
                className="flex items-center gap-2"
              >
                <Image className="h-4 w-4" />
                Add Image URL
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addReference('text')}
                className="flex items-center gap-2"
              >
                <FileText className="h-4 w-4" />
                Add Text
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => referenceFileInputRef.current?.click()}
                disabled={isExtractingFile}
                className="flex items-center gap-2"
              >
                {isExtractingFile ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <Paperclip className="h-4 w-4" />
                    Upload File
                  </>
                )}
              </Button>
              <input
                ref={referenceFileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.pptx,.ppt,.csv,.xlsx,.xls,.txt"
                className="hidden"
                onChange={handleReferenceFileUpload}
              />
            </div>

            {/* References List */}
            <div className={`space-y-3 ${formData.references.length > 0 ? 'max-h-[300px] overflow-y-auto pr-2' : ''}`}>
              {formData.references.length === 0 ? (
                <div className="text-center py-8 border border-dashed rounded-lg">
                  <Link2 className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    No references added yet. Add URLs to articles, videos, images, or paste text that should inform your content.
                  </p>
                </div>
              ) : (
                formData.references.map((ref, index) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        ref.type === 'article' ? 'bg-blue-500/10' :
                        ref.type === 'video' ? 'bg-red-500/10' :
                        ref.type === 'text' ? 'bg-purple-500/10' :
                        ref.type === 'file' ? 'bg-orange-500/10' : 'bg-green-500/10'
                      }`}>
                        {ref.type === 'article' && <Globe className="h-5 w-5 text-blue-500" />}
                        {ref.type === 'video' && <Video className="h-5 w-5 text-red-500" />}
                        {ref.type === 'image' && <Image className="h-5 w-5 text-green-500" />}
                        {ref.type === 'text' && <FileText className="h-5 w-5 text-purple-500" />}
                        {ref.type === 'file' && <Paperclip className="h-5 w-5 text-orange-500" />}
                      </div>
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge variant="secondary" className="capitalize">{ref.type === 'file' ? `File: ${ref.url}` : ref.type}</Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeReference(index)}
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                        {ref.type === 'text' || ref.type === 'file' ? (
                          <Textarea
                            placeholder={ref.type === 'file' ? "Extracted text from file..." : "Paste or type your reference text here..."}
                            value={ref.description}
                            onChange={(e) => updateReference(index, 'description', e.target.value)}
                            rows={4}
                          />
                        ) : (
                          <>
                            <div className="flex gap-2">
                              <Input
                                className="flex-1"
                                placeholder={`Enter ${ref.type} URL...`}
                                value={ref.url}
                                onChange={(e) => updateReference(index, 'url', e.target.value)}
                              />
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => handleFetchUrl(index)}
                                disabled={fetchingUrlIndex === index || !ref.url.trim()}
                                className="h-9 px-3 flex-shrink-0"
                                title="Fetch and extract content from this URL"
                              >
                                {fetchingUrlIndex === index ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Search className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                            <Textarea
                              placeholder={ref.description ? "" : "Brief description (optional) — or click the fetch button to auto-extract"}
                              value={ref.description}
                              onChange={(e) => updateReference(index, 'description', e.target.value)}
                              rows={ref.description ? 3 : 1}
                            />
                          </>
                        )}
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>

            {formData.references.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {formData.references.length} reference{formData.references.length !== 1 ? 's' : ''} added.
                The AI will analyze these materials to create more relevant and informed content.
              </p>
            )}
          </div>
        );

      case 4:
        const isSocialMediaStep4 = socialMediaTypes.some(t => t.id === formData.articleType);
        const isCommunityStep4 = communityPostTypes.some(t => t.id === formData.articleType);

        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">Content Settings</h3>
              <p className="text-sm text-muted-foreground">
                Configure your article generation preferences
              </p>
            </div>

            {/* Simple one-line notice about loaded guidelines */}
            {hasContentGuidelines && (
              <p className="text-sm text-muted-foreground italic">
                Pre-filled from your domain's content guidelines. You can edit these for this content.
              </p>
            )}

            {/* Additional Instructions - separated from other settings */}
            <div className="pb-5 mb-5 border-b border-border">
              <Label>Additional Instructions for Content Generation</Label>
              {/* Rich text brief: user formats visually (bold, headings,
                  lists); only clean plain text is stored + sent to the AI. The
                  key remounts a fresh editor whenever the dialog opens. */}
              <RichTextArea
                key={open ? "instr-open" : "instr-closed"}
                placeholder="Any specific instructions for the AI to follow when generating content..."
                minHeight={90}
                onChange={(text) => setFormData((prev) => ({ ...prev, additionalInstructions: text }))}
              />
            </div>

            <div className="space-y-4">
              {/* Tone of Voice */}
              <div>
                <Label>Tone of Voice</Label>
                <Input
                  value={formData.tone}
                  onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
                  placeholder="e.g., Professional, friendly, authoritative..."
                />
              </div>

              {/* Content Style */}
              <div>
                <Label>Content Style</Label>
                <Input
                  value={formData.style}
                  onChange={(e) => setFormData({ ...formData, style: e.target.value })}
                  placeholder="e.g., Informative, persuasive, storytelling..."
                />
              </div>

              {/* Key Messages */}
              <div>
                <Label>Key Messages</Label>
                <Textarea
                  value={formData.keyMessages}
                  onChange={(e) => setFormData({ ...formData, keyMessages: e.target.value })}
                  placeholder="Key messages to incorporate in the content..."
                  rows={2}
                />
              </div>

              {/* Topics to Avoid */}
              <div>
                <Label>Topics to Avoid</Label>
                <Textarea
                  value={formData.topicsToAvoid}
                  onChange={(e) => setFormData({ ...formData, topicsToAvoid: e.target.value })}
                  placeholder="Topics or themes to avoid in the content..."
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Target Audience</Label>
                  <Select value={formData.audience} onValueChange={(v) => setFormData({ ...formData, audience: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="general">General</SelectItem>
                      <SelectItem value="beginners">Beginners</SelectItem>
                      <SelectItem value="professionals">Professionals</SelectItem>
                      <SelectItem value="experts">Experts</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>{isSocialMediaStep4 ? 'Character/Word Count' : 'Word Count'}</Label>
                  <Select
                    value={formData.wordCount.toString()}
                    onValueChange={(v) => setFormData({ ...formData, wordCount: parseInt(v) })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {isSocialMediaStep4 ? (
                        <>
                          <SelectItem value="50">Short (50-100 words)</SelectItem>
                          <SelectItem value="150">Medium (150-250 words)</SelectItem>
                          <SelectItem value="300">Long (300-500 words)</SelectItem>
                          <SelectItem value="500">Thread (500+ words)</SelectItem>
                        </>
                      ) : isCommunityStep4 ? (
                        <>
                          <SelectItem value="150">Brief (150-300 words)</SelectItem>
                          <SelectItem value="400">Standard (400-600 words)</SelectItem>
                          <SelectItem value="800">Detailed (800-1,200 words)</SelectItem>
                          <SelectItem value="1500">Comprehensive (1,500+ words)</SelectItem>
                        </>
                      ) : (
                        <>
                          <SelectItem value="700">Below 800 words</SelectItem>
                          <SelectItem value="800">800-1,000 words</SelectItem>
                          <SelectItem value="1500">1,000-2,000 words</SelectItem>
                          <SelectItem value="2500">2,000-3,000 words</SelectItem>
                          <SelectItem value="3500">3,000+ words</SelectItem>
                        </>
                      )}
                    </SelectContent>
                </Select>
                </div>
              </div>
            </div>
          </div>
        );

      case 5:
        // Calculate total estimated words from outline
        const totalEstimatedWords = outline.reduce((sum, s) => sum + (s.estimated_words || 0), 0);

        return (
          <div className="space-y-6">
            <div className="pb-4 border-b border-border">
              <h3 className="text-lg font-semibold mb-1">
                {showSuccess ? "Content Generated!" : outlineGenerated ? "Review Outline" : "Generate Outline"}
              </h3>
              <p className="text-sm text-muted-foreground">
                {showSuccess
                  ? "Your content has been successfully generated"
                  : outlineGenerated
                    ? "Review and edit the outline, then generate content"
                    : "First, generate an outline to review the structure"}
              </p>
            </div>

            {/* Success State */}
            {showSuccess ? (
              <div className="py-8 space-y-6">
                <div className="flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full bg-green-500/10 flex items-center justify-center">
                    <CheckCircle2 className="h-10 w-10 text-green-500" />
                  </div>
                </div>

                <div className="text-center space-y-3">
                  <h4 className="text-xl font-semibold">Content Successfully Generated!</h4>
                  <p className="text-muted-foreground max-w-md mx-auto">
                    Your content has been created and saved to your content library which can be found in{' '}
                    <strong>
                      {existingContent?.sourceType === 'content_gap' ? 'Content Gaps' :
                       existingContent?.sourceType === 'answer_gap' ? 'Competitor Analysis' :
                       existingContent?.sourceType === 'topic' ? 'Topics' :
                       'Content Calendar'}
                    </strong>
                  </p>
                </div>

                <div className="flex justify-center gap-3 pt-4">
                  <Button
                    onClick={() => {
                      onOpenChange(false);
                      if (generatedContent?.id) {
                        navigate(`/content-editor/${generatedContent.id}`);
                      } else {
                        const sourceType = existingContent?.sourceType;
                        if (sourceType === 'content_gap') {
                          navigate('/content-gaps');
                        } else if (sourceType === 'answer_gap') {
                          navigate('/competitors');
                        } else if (sourceType === 'topic') {
                          navigate('/topics');
                        } else {
                          navigate('/content-calendar');
                        }
                      }
                    }}
                    className="gradient-primary"
                  >
                    <ArrowRight className="h-4 w-4 mr-2" />
                    View Content
                  </Button>
                  <Button onClick={() => onOpenChange(false)} variant="outline">
                    Close
                  </Button>
                </div>
              </div>

            /* Generating Content State */
            ) : isGenerating ? (
              <div className="py-12 space-y-6">
                <div className="flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full gradient-primary flex items-center justify-center animate-pulse">
                    <Sparkles className="h-10 w-10 text-white" />
                  </div>
                </div>
                <div className="space-y-3">
                  <p className="text-center font-medium">Generating your content from outline...</p>
                  <Progress value={progress} className="h-2" />
                  <p className="text-center text-sm text-muted-foreground">{progress}% complete</p>
                </div>
              </div>

            /* Outline Generated - Show Editable Outline */
            ) : outlineGenerated ? (
              <div className="space-y-4">
                {/* Summary Card */}
                <Card className="p-4 border border-border bg-muted/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ListOrdered className="h-5 w-5 text-primary" />
                      <span className="font-medium">{formData.title || "Untitled"}</span>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant="secondary">{outline.length} sections</Badge>
                      <Badge variant="outline">~{totalEstimatedWords} words</Badge>
                    </div>
                  </div>
                </Card>

                {/* Outline Sections - Scrollable */}
                <div className="max-h-[400px] overflow-y-auto pr-2 space-y-3">
                  {outline.map((section, index) => (
                    <Card key={section.id} className={`p-4 ${section.type === 'h3' ? 'ml-6' : ''}`}>
                      <div className="space-y-3">
                        {/* Section Header */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 flex-1">
                            <Badge variant={section.type === 'h2' ? 'default' : 'secondary'} className="text-xs">
                              {section.type.toUpperCase()}
                            </Badge>
                            {editingSection === section.id ? (
                              <Input
                                value={section.title}
                                onChange={(e) => updateSectionTitle(section.id, e.target.value)}
                                onBlur={() => setEditingSection(null)}
                                onKeyDown={(e) => e.key === 'Enter' && setEditingSection(null)}
                                autoFocus
                                className="h-8"
                              />
                            ) : (
                              <span
                                className="font-medium cursor-pointer hover:text-primary"
                                onClick={() => setEditingSection(section.id)}
                              >
                                {section.title}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0"
                              onClick={() => moveSection(section.id, 'up')}
                              disabled={index === 0}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0"
                              onClick={() => moveSection(section.id, 'down')}
                              disabled={index === outline.length - 1}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                              onClick={() => removeSection(section.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>

                        {/* Key Points */}
                        <div className="space-y-2">
                          <p className="text-xs text-muted-foreground font-medium">Key Points:</p>
                          {section.key_points.map((point, pointIndex) => (
                            <div key={pointIndex} className="flex items-center gap-2">
                              <span className="text-muted-foreground">•</span>
                              <Input
                                value={point}
                                onChange={(e) => updateKeyPoint(section.id, pointIndex, e.target.value)}
                                className="h-7 text-sm"
                              />
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                                onClick={() => removeKeyPoint(section.id, pointIndex)}
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          ))}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => addKeyPoint(section.id)}
                          >
                            <Plus className="h-3 w-3 mr-1" />
                            Add Point
                          </Button>
                        </div>

                        {/* Estimated Words */}
                        <p className="text-xs text-muted-foreground">
                          ~{section.estimated_words} words
                        </p>
                      </div>
                    </Card>
                  ))}
                </div>

                {/* Add Section Buttons */}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => addSection('h2')}>
                    <Plus className="h-4 w-4 mr-1" />
                    Add Section (H2)
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => addSection('h3')}>
                    <Plus className="h-4 w-4 mr-1" />
                    Add Subsection (H3)
                  </Button>
                </div>

                {/* Upload Document to replace outline */}
                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">
                      Upload a Word document to replace the outline
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Document
                    </Button>
                  </div>
                </div>
              </div>

            /* Initial State - Generate Outline */
            ) : (
              <div className="space-y-4">
                {/* Summary Card */}
                <Card className="p-5 border border-border bg-muted/30">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-primary" />
                      <h4 className="font-semibold">{formData.title || "Untitled Article"}</h4>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Badge variant="secondary">{formData.articleType}</Badge>
                      <Badge variant="outline">{formData.wordCount} words</Badge>
                      {formData.tone && <Badge variant="outline">{formData.tone}</Badge>}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm pt-3 border-t border-border">
                      {formData.style && (
                        <div>
                          <p className="text-muted-foreground mb-1">Style</p>
                          <p className="font-medium">{formData.style}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-muted-foreground mb-1">Target Audience</p>
                        <p className="font-medium capitalize">{formData.audience}</p>
                      </div>
                      {formData.keywords && (
                        <div className="col-span-2">
                          <p className="text-muted-foreground mb-1">Keywords</p>
                          <p className="font-medium">{formData.keywords}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>

                {/* Info Card */}
                <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <ListOrdered className="h-5 w-5 text-primary mt-0.5" />
                    <div className="text-sm">
                      <p className="font-medium mb-1">Two-Step Generation</p>
                      <p className="text-muted-foreground">
                        First, we'll generate an outline so you can review and customize the structure.
                        Then you can generate the full content from the approved outline.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Generating Outline State */}
                {isGeneratingOutline && (
                  <div className="py-6 space-y-4">
                    <div className="flex items-center justify-center">
                      <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
                        <ListOrdered className="h-8 w-8 text-primary" />
                      </div>
                    </div>
                    <p className="text-center text-sm text-muted-foreground">
                      Generating outline structure...
                    </p>
                  </div>
                )}

                {/* Error Display */}
                {error && (
                  <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive text-sm">
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="text-2xl">Content Generation Wizard</DialogTitle>
        </DialogHeader>

        {/* Wizard Step Indicator - Only show when not in success state */}
        {!showSuccess && (
          <div className="mb-6">
            <div className="flex items-center justify-center gap-2">
              {[1, 2, 3, 4, 5].map((stepNumber) => (
                <div key={stepNumber} className="flex items-center">
                  <div className={`flex items-center justify-center w-9 h-9 rounded-full transition-all ${
                    stepNumber === step
                      ? 'bg-primary text-white shadow-md shadow-primary/30'
                      : stepNumber < step
                        ? 'bg-primary/20 text-primary'
                        : 'bg-muted text-muted-foreground'
                  }`}>
                    <span className="text-sm font-semibold">{stepNumber}</span>
                  </div>
                  {stepNumber < 5 && (
                    <div className={`w-10 h-0.5 mx-1 transition-all ${
                      stepNumber < step ? 'bg-primary' : 'bg-muted'
                    }`} />
                  )}
                </div>
              ))}
            </div>
            <div className="text-center mt-3">
              <p className="text-sm font-medium">
                {step === 1 && "Choose Content Type"}
                {step === 2 && "Content Details"}
                {step === 3 && "References"}
                {step === 4 && "Content Settings"}
                {step === 5 && (outlineGenerated ? "Review Outline" : "Generate Outline")}
              </p>
            </div>
          </div>
        )}

        {renderStepContent()}

        {/* Navigation - Hide when showing success */}
        {!showSuccess && (
          <div className="flex items-center justify-between pt-6 border-t border-border">
            <Button
              variant="outline"
              onClick={() => {
                if (step === 5 && outlineGenerated) {
                  // Go back to outline not generated state
                  setOutline([]);
                  setOutlineGenerated(false);
                  setOriginalOutlineWords(null);
                } else if (step > 1) {
                  setStep(step - 1);
                } else {
                  onOpenChange(false);
                }
              }}
              disabled={isGenerating || isGeneratingOutline}
            >
              {step === 1 ? "Cancel" : step === 5 && outlineGenerated ? "Back to Settings" : "Previous"}
            </Button>

            {step < 5 ? (
              <Button onClick={handleNextStep} disabled={!formData.title && step === 2}>
                Next Step
              </Button>
            ) : outlineGenerated ? (
              <Button
                onClick={handleGenerateFromOutline}
                disabled={isGenerating || outline.length === 0}
                className="gradient-primary"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? "Generating..." : "Generate Content"}
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  onClick={handleCreateManualOutline}
                  disabled={isGeneratingOutline}
                  variant="outline"
                >
                  <Edit3 className="h-4 w-4 mr-2" />
                  Manual Outline
                </Button>
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isGeneratingOutline}
                  variant="outline"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Document
                </Button>
                <Button
                  onClick={handleGenerateOutline}
                  disabled={isGeneratingOutline}
                  className="gradient-primary"
                >
                  <ListOrdered className="h-4 w-4 mr-2" />
                  {isGeneratingOutline ? "Generating..." : "Generate Outline"}
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>

      {/* Hidden file input for Word document upload */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".doc,.docx"
        onChange={handleDocumentUpload}
      />

      {/* GSC Keywords Selection Modal */}
      <GSCKeywordsModal
        open={showGSCModal}
        onOpenChange={setShowGSCModal}
        keywords={gscKeywords}
        isLoading={isLoadingGSCKeywords}
        onAddKeywords={handleAddGSCKeywords}
        existingKeywords={existingKeywordsArray}
      />
    </Dialog>
  );
};
