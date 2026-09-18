import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import {
  ArrowLeft,
  Plus,
  Loader2,
  Sparkles,
  Download,
  X,
  Upload,
  FileText,
  Link2,
  Info,
  Activity,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Trash2,
  Edit2,
  ExternalLink,
  BookOpen,
  File,
  FileSpreadsheet,
  Presentation,
  MessageSquare,
  Globe,
  RefreshCw,
  Eye,
  ShieldCheck,
  CalendarClock,
} from "lucide-react";
import { DomainClientAccess } from "@/components/DomainClientAccess";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageLoader } from "@/components/PageLoader";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { useDomainStore } from "@/stores/domainStore";
import {
  CADENCE_OPTIONS, cadenceOf, creditsPerSweep, describeNextSweep, type Cadence,
} from "@/lib/sweep-cadence";
import { useAuth } from "@/contexts/AuthContext";

export default function DomainSettings() {
  const { domainId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const { setSelectedDomain, selectedDomain, domains, setDomains, sweep } = useDomainStore();

  // Keep the page on whichever project the sidebar switcher points at.
  //
  // This screen reads :domainId from the URL; switchDomain() in the sidebar
  // only writes to the store. Without this the pill and the page disagree —
  // "Bata" selected, Binance's settings on screen.
  //
  // Only a *change* in selection redirects. Comparing the store to the URL
  // instead would break deep links: opening /organization-settings/domains/<x>
  // while another project is selected would bounce straight back to it.
  const lastSelectedId = useRef<number | null>(selectedDomain?.id ?? null);
  useEffect(() => {
    const selected = selectedDomain?.id ?? null;
    if (selected === lastSelectedId.current) return;
    lastSelectedId.current = selected;
    if (selected !== null && String(selected) !== String(domainId)) {
      navigate(`/organization-settings/domains/${selected}`, { replace: true });
    }
  }, [selectedDomain?.id, domainId, navigate]);
  // Draft state, like every other field in Basic Information: choosing a
  // cadence arms Save, and nothing reaches the server until Save is pressed.
  // It used to write immediately, which made it the one control on the card
  // that behaved differently from its neighbours.
  const [sweepCadence, setSweepCadence] = useState<Cadence>("weekly");
  const { user } = useAuth();
  const isTeamMember = user?.role === 'user';
  // A client opens this page for the health report and nothing else. Brand
  // identity, content guidelines, internal links, integrations, the reference
  // repository and client access are all agency-side configuration.
  const isClient = user?.role === 'client';

  // Domain state
  const [domain, setDomain] = useState<{
    id: number;
    name: string;
    url: string;
    short_description?: string | null;
    country?: string;
    tone_of_voice?: string | null;
    content_style?: string | null;
    key_messages?: string | null;
    topics_to_avoid?: string | null;
    target_audience?: string | null;
    brand_values?: string | null;
    key_competitors?: string | null;
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
    /** Sweep schedule, edited on this page and applied by Save. */
    sweep_cadence?: Cadence;
  } | null>(null);

  // Basic Info edit state
  const [domainName, setDomainName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [isSavingBasicInfo, setIsSavingBasicInfo] = useState(false);

  // Content Guidelines state
  const [toneOfVoice, setToneOfVoice] = useState("");
  const [contentStyle, setContentStyle] = useState("");
  const [keyMessages, setKeyMessages] = useState("");
  const [topicsToAvoid, setTopicsToAvoid] = useState("");
  const [isSavingGuidelines, setIsSavingGuidelines] = useState(false);

  // Brand Identity state
  const [targetAudience, setTargetAudience] = useState("");
  const [brandValues, setBrandValues] = useState("");
  const [keyCompetitors, setKeyCompetitors] = useState("");

  // AI auto-fill for the two guideline tabs. Each button fills only the fields
  // its own tab owns, and only the ones that are still empty — a click must
  // never overwrite something the user has written.
  const [isFillingGuidelines, setIsFillingGuidelines] = useState(false);

  // Integrations state
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [isConnectingGA, setIsConnectingGA] = useState(false);
  const [isConnectingGSC, setIsConnectingGSC] = useState(false);
  
  // Property/Site selection state
  const [showPropertySelection, setShowPropertySelection] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState<any>(null);
  const [properties, setProperties] = useState<any[]>([]);
  const [sites, setSites] = useState<any[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string>("");
  const [selectedSiteId, setSelectedSiteId] = useState<string>("");
  const [isLoadingProperties, setIsLoadingProperties] = useState(false);
  const [isSelectingProperty, setIsSelectingProperty] = useState(false);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);


  // Health check state
  const [healthData, setHealthData] = useState<any>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthHistory, setHealthHistory] = useState<any>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Internal Link Map state
  const [internalLinks, setInternalLinks] = useState<any[]>([]);
  const [isLoadingInternalLinks, setIsLoadingInternalLinks] = useState(false);
  const [showAddLinkDialog, setShowAddLinkDialog] = useState(false);
  const [showEditLinkDialog, setShowEditLinkDialog] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [editingLink, setEditingLink] = useState<any>(null);
  const [newLinkTopic, setNewLinkTopic] = useState("");
  const [newLinkKeywords, setNewLinkKeywords] = useState("");
  const [newLinkUrl, setNewLinkUrl] = useState("");
  const [isSavingLink, setIsSavingLink] = useState(false);
  const [isDeletingLink, setIsDeletingLink] = useState(false);
  const [csvImportText, setCsvImportText] = useState("");
  const [csvFileName, setCsvFileName] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  // Reference Repository state
  const [referenceDocuments, setReferenceDocuments] = useState<any[]>([]);
  const [isLoadingRefDocs, setIsLoadingRefDocs] = useState(false);
  const [isUploadingRefDoc, setIsUploadingRefDoc] = useState(false);
  const [isDeletingRefDoc, setIsDeletingRefDoc] = useState(false);
  const [refDocTotalFiles, setRefDocTotalFiles] = useState(0);
  const [refDocTotalSize, setRefDocTotalSize] = useState(0);
  const [refDocMaxFiles, setRefDocMaxFiles] = useState(20);
  const [showAddTextNoteDialog, setShowAddTextNoteDialog] = useState(false);
  const [textNoteTitle, setTextNoteTitle] = useState("");
  const [textNoteContent, setTextNoteContent] = useState("");
  const [textNoteDescription, setTextNoteDescription] = useState("");
  const [isSavingTextNote, setIsSavingTextNote] = useState(false);

  // Brand Links state
  const [brandLinks, setBrandLinks] = useState<any[]>([]);
  const [isLoadingBrandLinks, setIsLoadingBrandLinks] = useState(false);
  const [showAddBrandLinkDialog, setShowAddBrandLinkDialog] = useState(false);
  const [brandLinkPlatform, setBrandLinkPlatform] = useState("");
  const [brandLinkUrl, setBrandLinkUrl] = useState("");
  const [brandLinkLabel, setBrandLinkLabel] = useState("");
  const [isSavingBrandLink, setIsSavingBrandLink] = useState(false);
  const [isDeletingBrandLink, setIsDeletingBrandLink] = useState(false);
  const [brandLinkTotalLinks, setBrandLinkTotalLinks] = useState(0);
  const [brandLinkMaxLinks, setBrandLinkMaxLinks] = useState(20);

  // Content Viewer state (for both documents and brand links)
  const [showContentViewer, setShowContentViewer] = useState(false);
  const [contentViewerTitle, setContentViewerTitle] = useState("");
  const [contentViewerText, setContentViewerText] = useState("");
  const [isLoadingContent, setIsLoadingContent] = useState(false);

  // Health is the only tab a client is offered, so it is also the only tab a
  // client may land on. Without this, arriving without ?tab would select
  // basic-info - a tab whose trigger is hidden from them - and the page would
  // render an empty panel.
  const initialTab = isClient
    ? "health"
    : isTeamMember
    ? "integrations"
    : (searchParams.get("tab") || "basic-info");
  const [activeTab, setActiveTab] = useState(initialTab);

  useEffect(() => {
    if (isClient) {
      setActiveTab("health");
      return;
    }
    if (isTeamMember) {
      setActiveTab("integrations");
      return;
    }
    const tabParam = searchParams.get("tab");
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [searchParams, activeTab, isTeamMember, isClient]);

  // Fetch health data when health tab is active (including on initial load with ?tab=health)
  useEffect(() => {
    if (activeTab === 'health' && domainId && !healthHistory) {
      console.log('Health tab is active, fetching health history');
      fetchHealthHistory();
    }
  }, [activeTab, domainId]);

  // Fetch internal links when internal-links tab is active
  useEffect(() => {
    if (activeTab === 'internal-links' && domainId && internalLinks.length === 0) {
      fetchInternalLinks();
    }
  }, [activeTab, domainId]);

  // Fetch reference documents and brand links when reference-repository tab is active
  useEffect(() => {
    if (activeTab === 'reference-repository' && domainId && referenceDocuments.length === 0) {
      fetchReferenceDocuments();
    }
    if (activeTab === 'reference-repository' && domainId && brandLinks.length === 0) {
      fetchBrandLinks();
    }
  }, [activeTab, domainId]);

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    const newParams = new URLSearchParams(searchParams);
    newParams.set("tab", value);
    setSearchParams(newParams, { replace: true });

    // Fetch health check data when Health tab is activated
    if (value === 'health' && domainId) {
      console.log('Health tab activated. healthData exists:', !!healthData, 'healthHistory exists:', !!healthHistory);
      if (!healthData && !healthHistory) {
        // First time viewing health tab - fetch latest health check from history first
        console.log('Fetching health history (first time)');
        fetchHealthHistory();
      } else if (!healthHistory) {
        // If we have health data but no history, just fetch history
        console.log('Fetching health history (have data, need history)');
        fetchHealthHistory();
      }
    }

    // Fetch internal links when Internal Links tab is activated
    if (value === 'internal-links' && domainId && internalLinks.length === 0) {
      fetchInternalLinks();
    }
  };

  // Fetch health check data
  const fetchHealthCheck = async () => {
    if (!domainId) return;

    setIsLoadingHealth(true);
    setHealthError(null);

    try {
      const response = await apiClient.getDomainHealthCheck(parseInt(domainId));
      setHealthData(response);

      // Also fetch updated history
      fetchHealthHistory();
    } catch (error: any) {
      console.error('Error fetching health check:', error);
      setHealthError(error.message || 'Failed to fetch health check data');
      toast({
        title: "Error",
        description: error.message || "Failed to fetch health check data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingHealth(false);
    }
  };

  // Fetch health check history
  const fetchHealthHistory = async () => {
    if (!domainId) return;

    setIsLoadingHistory(true);

    try {
      const response = await apiClient.getDomainHealthCheckHistory(parseInt(domainId), 5);
      console.log('Health history response:', response);
      setHealthHistory(response);

      // If we don't have healthData but history has results, use the latest one
      if (!healthData && response.history && response.history.length > 0) {
        const latest = response.history[0];
        console.log('Setting health data from latest history:', latest);
        setHealthData({
          id: latest.id,
          domain: response.domain,
          health_score: latest.health_score,
          max_score: latest.max_score,
          percentage: latest.percentage,
          grade: latest.grade,
          grade_color: latest.grade_color,
          checks: latest.checks,
          categories: latest.categories,
          summary: latest.summary,
          created_at: latest.created_at
        });
      } else {
        console.log('No health data to set. healthData exists:', !!healthData, 'history length:', response.history?.length);
      }
    } catch (error: any) {
      console.error('Error fetching health history:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Fetch internal links
  const fetchInternalLinks = async () => {
    if (!domainId) return;

    setIsLoadingInternalLinks(true);
    try {
      const response: any = await apiClient.getInternalLinkMaps(parseInt(domainId));
      setInternalLinks(response.internal_links || []);
    } catch (error: any) {
      console.error('Error fetching internal links:', error);
      toast({
        title: "Error",
        description: error.message || "Failed to fetch internal links.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingInternalLinks(false);
    }
  };

  // Add internal link
  const handleAddInternalLink = async () => {
    if (!domain || !newLinkTopic.trim() || !newLinkKeywords.trim() || !newLinkUrl.trim()) {
      toast({
        title: "Validation Error",
        description: "Please fill in all fields.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingLink(true);
    try {
      await apiClient.createInternalLinkMap(domain.id, {
        topic: newLinkTopic.trim(),
        keywords: newLinkKeywords.trim(),
        url: newLinkUrl.trim(),
      });

      toast({
        title: "Link Added",
        description: "Internal link has been added successfully.",
      });

      setNewLinkTopic("");
      setNewLinkKeywords("");
      setNewLinkUrl("");
      setShowAddLinkDialog(false);
      fetchInternalLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add internal link.",
        variant: "destructive",
      });
    } finally {
      setIsSavingLink(false);
    }
  };

  // Update internal link
  const handleUpdateInternalLink = async () => {
    if (!domain || !editingLink || !newLinkTopic.trim() || !newLinkKeywords.trim() || !newLinkUrl.trim()) {
      toast({
        title: "Validation Error",
        description: "Please fill in all fields.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingLink(true);
    try {
      await apiClient.updateInternalLinkMap(domain.id, editingLink.id, {
        topic: newLinkTopic.trim(),
        keywords: newLinkKeywords.trim(),
        url: newLinkUrl.trim(),
      });

      toast({
        title: "Link Updated",
        description: "Internal link has been updated successfully.",
      });

      setNewLinkTopic("");
      setNewLinkKeywords("");
      setNewLinkUrl("");
      setEditingLink(null);
      setShowEditLinkDialog(false);
      fetchInternalLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to update internal link.",
        variant: "destructive",
      });
    } finally {
      setIsSavingLink(false);
    }
  };

  // Delete internal link
  const handleDeleteInternalLink = async (linkId: number) => {
    if (!domain) return;

    setIsDeletingLink(true);
    try {
      await apiClient.deleteInternalLinkMap(domain.id, linkId);

      toast({
        title: "Link Deleted",
        description: "Internal link has been deleted successfully.",
      });

      fetchInternalLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to delete internal link.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingLink(false);
    }
  };

  // Open edit dialog
  const handleOpenEditDialog = (link: any) => {
    setEditingLink(link);
    setNewLinkTopic(link.topic);
    setNewLinkKeywords(link.keywords);
    setNewLinkUrl(link.url);
    setShowEditLinkDialog(true);
  };

  // Import CSV
  const handleImportCSV = async () => {
    if (!domain || !csvImportText.trim()) {
      toast({
        title: "Validation Error",
        description: "Please select a CSV file.",
        variant: "destructive",
      });
      return;
    }

    setIsImporting(true);
    try {
      // Parse CSV text
      const lines = csvImportText.trim().split('\n');
      const csvData: Array<{ topic: string; keywords: string; url: string }> = [];

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Skip header row if it contains "topic", "keywords", "url", or "target"
        const lowerLine = line.toLowerCase();
        if (i === 0 && (lowerLine.includes('topic') || lowerLine.includes('keywords') || lowerLine.includes('url') || lowerLine.includes('target'))) {
          continue;
        }

        // Parse CSV line (handle quoted values)
        const values: string[] = [];
        let current = '';
        let inQuotes = false;

        for (let j = 0; j < line.length; j++) {
          const char = line[j];
          if (char === '"') {
            inQuotes = !inQuotes;
          } else if (char === ',' && !inQuotes) {
            values.push(current.trim().replace(/^"|"$/g, ''));
            current = '';
          } else {
            current += char;
          }
        }
        values.push(current.trim().replace(/^"|"$/g, ''));

        if (values.length >= 3) {
          csvData.push({
            topic: values[0],
            keywords: values[1],
            url: values[2],
          });
        }
      }

      if (csvData.length === 0) {
        toast({
          title: "No Data",
          description: "No valid rows found in CSV data.",
          variant: "destructive",
        });
        return;
      }

      const response: any = await apiClient.importInternalLinkMaps(domain.id, csvData);

      toast({
        title: "Import Complete",
        description: response.message || `Imported ${response.created_count} links.`,
      });

      setCsvImportText("");
      setShowImportDialog(false);
      fetchInternalLinks();
    } catch (error: any) {
      toast({
        title: "Import Error",
        description: error.message || "Failed to import CSV data.",
        variant: "destructive",
      });
    } finally {
      setIsImporting(false);
    }
  };

  // Handle CSV file upload
  const handleCSVFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast({
        title: "Invalid File",
        description: "Please upload a CSV file.",
        variant: "destructive",
      });
      return;
    }

    try {
      const text = await file.text();
      setCsvImportText(text);
      setCsvFileName(file.name);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to read file.",
        variant: "destructive",
      });
    }

    event.target.value = '';
  };

  // ===== Reference Repository Functions =====
  const fetchReferenceDocuments = async () => {
    if (!domainId) return;
    setIsLoadingRefDocs(true);
    try {
      const response: any = await apiClient.getReferenceDocuments(parseInt(domainId));
      setReferenceDocuments(response.reference_documents || []);
      setRefDocTotalFiles(response.total_files || 0);
      setRefDocTotalSize(response.total_size_bytes || 0);
      setRefDocMaxFiles(response.max_files || 20);
    } catch (error: any) {
      console.error('Error fetching reference documents:', error);
    } finally {
      setIsLoadingRefDocs(false);
    }
  };

  const handleReferenceFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !domain) return;

    const allowedExtensions = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.csv', '.xls', '.xlsx'];
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      toast({
        title: "Unsupported File Type",
        description: "Allowed formats: PDF, PPT/PPTX, DOC/DOCX, CSV, XLS/XLSX",
        variant: "destructive",
      });
      event.target.value = '';
      return;
    }

    // Check file size (max 25MB)
    if (file.size > 25 * 1024 * 1024) {
      toast({
        title: "File Too Large",
        description: "Maximum file size is 25 MB.",
        variant: "destructive",
      });
      event.target.value = '';
      return;
    }

    setIsUploadingRefDoc(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response: any = await apiClient.uploadReferenceDocument(domain.id, formData);
      toast({
        title: "File Uploaded",
        description: response.message || "Reference document uploaded successfully.",
      });
      fetchReferenceDocuments();
    } catch (error: any) {
      toast({
        title: "Upload Error",
        description: error.message || "Failed to upload file.",
        variant: "destructive",
      });
    } finally {
      setIsUploadingRefDoc(false);
      event.target.value = '';
    }
  };

  const handleAddTextNote = async () => {
    if (!domain || !textNoteContent.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter text content.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingTextNote(true);
    try {
      const response: any = await apiClient.addReferenceTextNote(domain.id, {
        file_type: 'text',
        title: textNoteTitle.trim() || 'Text Note',
        text_content: textNoteContent.trim(),
        description: textNoteDescription.trim(),
      });

      toast({
        title: "Text Note Added",
        description: response.message || "Text note added successfully.",
      });

      setTextNoteTitle("");
      setTextNoteContent("");
      setTextNoteDescription("");
      setShowAddTextNoteDialog(false);
      fetchReferenceDocuments();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add text note.",
        variant: "destructive",
      });
    } finally {
      setIsSavingTextNote(false);
    }
  };

  const handleDeleteReferenceDoc = async (docId: number) => {
    if (!domain) return;
    setIsDeletingRefDoc(true);
    try {
      await apiClient.deleteReferenceDocument(domain.id, docId);
      toast({
        title: "Document Deleted",
        description: "Reference document removed successfully.",
      });
      fetchReferenceDocuments();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to delete document.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingRefDoc(false);
    }
  };

  // ===== Brand Links Functions =====
  const fetchBrandLinks = async () => {
    if (!domainId) return;
    setIsLoadingBrandLinks(true);
    try {
      const response: any = await apiClient.getBrandLinks(parseInt(domainId));
      setBrandLinks(response.brand_links || []);
      setBrandLinkTotalLinks(response.total_links || 0);
      setBrandLinkMaxLinks(response.max_links || 20);
    } catch (error: any) {
      console.error('Error fetching brand links:', error);
    } finally {
      setIsLoadingBrandLinks(false);
    }
  };

  const handleAddBrandLink = async () => {
    if (!domain || !brandLinkUrl.trim() || !brandLinkPlatform) {
      toast({
        title: "Validation Error",
        description: "Please select a platform and enter a URL.",
        variant: "destructive",
      });
      return;
    }

    setIsSavingBrandLink(true);
    try {
      const response: any = await apiClient.addBrandLink(domain.id, {
        platform: brandLinkPlatform,
        url: brandLinkUrl.trim(),
        label: brandLinkLabel.trim(),
      });

      toast({
        title: "Brand Link Added",
        description: response.message || "Brand link added successfully.",
      });

      setBrandLinkPlatform("");
      setBrandLinkUrl("");
      setBrandLinkLabel("");
      setShowAddBrandLinkDialog(false);
      fetchBrandLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add brand link.",
        variant: "destructive",
      });
    } finally {
      setIsSavingBrandLink(false);
    }
  };

  const handleDeleteBrandLink = async (linkId: number) => {
    if (!domain) return;
    setIsDeletingBrandLink(true);
    try {
      await apiClient.deleteBrandLink(domain.id, linkId);
      toast({
        title: "Brand Link Deleted",
        description: "Brand link removed successfully.",
      });
      fetchBrandLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to delete brand link.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingBrandLink(false);
    }
  };

  const handleRecrawlBrandLink = async (linkId: number) => {
    if (!domain) return;
    try {
      const response: any = await apiClient.recrawlBrandLink(domain.id, linkId);
      toast({
        title: "Re-crawling",
        description: response.message || "Re-crawling brand link in the background.",
      });
      fetchBrandLinks();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to re-crawl brand link.",
        variant: "destructive",
      });
    }
  };

  // ===== Content Viewer Functions =====
  const handleViewDocumentContent = async (doc: any) => {
    if (!domain) return;
    setContentViewerTitle(doc.file_name || 'Document Content');
    setShowContentViewer(true);
    setIsLoadingContent(true);
    try {
      const response: any = await apiClient.getReferenceDocumentDetail(domain.id, doc.id);
      setContentViewerText(response.reference_document?.extracted_text || 'No content extracted.');
    } catch (error: any) {
      setContentViewerText('Failed to load content.');
    } finally {
      setIsLoadingContent(false);
    }
  };

  const handleViewBrandLinkContent = async (link: any) => {
    if (!domain) return;
    setContentViewerTitle(`${link.platform_display} — ${link.url}`);
    setShowContentViewer(true);
    setIsLoadingContent(true);
    try {
      const response: any = await apiClient.getBrandLinkDetail(domain.id, link.id);
      const brandLink = response.brand_link;
      if (brandLink?.extraction_status === 'failed') {
        setContentViewerText(`Extraction failed: ${brandLink.extraction_error || 'Unknown error'}\n\nSome platforms (like Twitter/X) block automated crawling. You can try the Re-crawl button or add the content manually using a Text Note in the Reference Documents section below.`);
      } else if (brandLink?.extraction_status === 'processing') {
        setContentViewerText('Content extraction is still in progress. Please check back in a few moments.');
      } else if (brandLink?.extraction_status === 'pending') {
        setContentViewerText('Content extraction has not started yet. It will begin shortly.');
      } else {
        setContentViewerText(brandLink?.extracted_text || 'No content was extracted from this URL.');
      }
    } catch (error: any) {
      setContentViewerText('Failed to load content.');
    } finally {
      setIsLoadingContent(false);
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'facebook': return <Globe className="h-4 w-4 text-blue-600" />;
      case 'instagram': return <Globe className="h-4 w-4 text-pink-500" />;
      case 'twitter': return <Globe className="h-4 w-4 text-sky-500" />;
      case 'youtube': return <Globe className="h-4 w-4 text-red-500" />;
      case 'linkedin': return <Globe className="h-4 w-4 text-blue-700" />;
      case 'microsite': return <Globe className="h-4 w-4 text-emerald-500" />;
      case 'blog': return <Globe className="h-4 w-4 text-orange-500" />;
      default: return <Globe className="h-4 w-4 text-gray-500" />;
    }
  };

  const getExtractionStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="outline" className="text-xs text-green-600 border-green-300"><CheckCircle2 className="h-3 w-3 mr-1" />Extracted</Badge>;
      case 'processing':
        return <Badge variant="outline" className="text-xs text-blue-600 border-blue-300"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Processing</Badge>;
      case 'failed':
        return <Badge variant="outline" className="text-xs text-red-600 border-red-300"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      default:
        return <Badge variant="outline" className="text-xs text-yellow-600 border-yellow-300"><AlertCircle className="h-3 w-3 mr-1" />Pending</Badge>;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileTypeIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf': return <File className="h-4 w-4 text-red-500" />;
      case 'docx': return <FileText className="h-4 w-4 text-blue-500" />;
      case 'pptx': return <Presentation className="h-4 w-4 text-orange-500" />;
      case 'csv': return <FileSpreadsheet className="h-4 w-4 text-green-500" />;
      case 'xlsx': return <FileSpreadsheet className="h-4 w-4 text-green-600" />;
      case 'text': return <MessageSquare className="h-4 w-4 text-purple-500" />;
      default: return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  // Load domain data
  useEffect(() => {
    if (!domainId) return;
    // Every tab below caches its data and refetches only when the cache is
    // empty, so switching projects has to empty them: otherwise Health,
    // Internal Links and Reference would keep showing the previous project's
    // results under the new project's name. Harmless before the switcher moved
    // this page, because you could never change domainId without a remount.
    setHealthData(null);
    setHealthHistory(null);
    setInternalLinks([]);
    setReferenceDocuments([]);
    setBrandLinks([]);
    loadDomainData();
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
      setShortDescription(foundDomain.short_description || "");
      setDomainName(foundDomain.name || "");
      setSweepCadence(cadenceOf(foundDomain));
      setToneOfVoice(foundDomain.tone_of_voice || "");
      setContentStyle(foundDomain.content_style || "");
      setKeyMessages(foundDomain.key_messages || "");
      setTopicsToAvoid(foundDomain.topics_to_avoid || "");
      setTargetAudience(foundDomain.target_audience || "");
      setBrandValues(foundDomain.brand_values || "");
      setKeyCompetitors(foundDomain.key_competitors || "");
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


  const handleSaveBasicInfo = async () => {
    if (!domain || !domainName.trim()) return;

    try {
      setIsSavingBasicInfo(true);
      await apiClient.updateDomain(domain.id, {
        name: domainName.trim(),
        short_description: shortDescription.trim() || null,
      });

      setDomain({
        ...domain,
        name: domainName.trim(),
        short_description: shortDescription.trim() || null,
      });

      toast({
        title: "Basic info saved",
        description: "Domain information has been updated successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Error saving",
        description: error.message || "Failed to save domain information.",
        variant: "destructive",
      });
    } finally {
      setIsSavingBasicInfo(false);
    }
  };

  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  /** Prompt groups - what a sweep actually walks, one row each in the table. */
  const [scheduleGroups, setScheduleGroups] = useState<
    { id: number; group_id: string; prompts_count: number; prompts_in_flight: number }[] | null
  >(null);

  /**
   * Save just the cadence.
   *
   * Its own handler rather than riding on handleSaveBasicInfo: the control used
   * to live on the Basic Information card, and a Save button on one tab that
   * silently commits a field on another is the kind of thing nobody finds until
   * it loses their work.
   */
  const handleSaveSchedule = async () => {
    if (!domain) return;
    try {
      setIsSavingSchedule(true);
      await apiClient.updateDomain(domain.id, { sweep_cadence: sweepCadence });
      setDomain({ ...domain, sweep_cadence: sweepCadence });
      // Organization Settings > Schedules reads the cadence from the domain
      // store, so without this it would show the old value until a reload.
      setDomains(
        useDomainStore.getState().domains.map((x) =>
          x.id === domain.id ? { ...x, sweep_cadence: sweepCadence } : x,
        ),
      );
      toast({
        title: "Schedule saved",
        description: `${domain.name} — ${
          CADENCE_OPTIONS.find((o) => o.value === sweepCadence)?.label
        }.`,
      });
    } catch (error: any) {
      toast({
        title: "Error saving",
        description: error?.message || "Failed to save the schedule.",
        variant: "destructive",
      });
    } finally {
      setIsSavingSchedule(false);
    }
  };

  const hasScheduleChanged = () => !!domain && sweepCadence !== cadenceOf(domain);

  // Loaded only when the Schedule tab is opened: the other eight tabs have no
  // use for it, and this page already makes enough requests on mount.
  useEffect(() => {
    if (activeTab !== "schedule" || !domainId || scheduleGroups) return;
    let cancelled = false;
    apiClient
      .getPromptGroups({ domain_id: domainId, limit: 100 })
      .then((r: any) => {
        if (!cancelled) setScheduleGroups(r?.groups ?? []);
      })
      .catch(() => {
        if (!cancelled) setScheduleGroups([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab, domainId, scheduleGroups]);

  const hasBasicInfoChanged = () => {
    if (!domain) return false;
    return (
      domainName !== domain.name ||
      shortDescription !== (domain.short_description || "")
    );
  };

  /**
   * Ask the LLM for a brand profile and fill ONLY the blank fields of one tab.
   *
   * Never overwrites anything the user has already written — a field with any
   * content is left exactly as it is. The result is put into form state, not
   * saved: the model is instructed to "make reasonable inferences", so the user
   * reviews it and presses Save themselves.
   */
  /** Fills every blank field on the Brand Guidelines tab. Anything the user
   *  has already written is left alone. */
  const autoFillFields = async (): Promise<void> => {
    if (!domain) return;
    setIsFillingGuidelines(true);
    try {
      const res = (await apiClient.fetchBrandInfo(
        domain.name || "",
        domain.url || "",
      )) as { success?: boolean; data?: Record<string, string>; brand_info?: Record<string, string>; message?: string };

      const info = res?.data || res?.brand_info || (res as Record<string, string>) || {};

      // [state value, setter, key on the response, hard cap]
      //
      // tone and content style are capped at 50 characters: `domains` stores
      // them as TEXT, but `generated_contents` copies them into varchar(50)
      // columns, so a longer value saves happily here and then breaks content
      // generation later with a raw DataError.
      const guidelineFields: Array<[string, (v: string) => void, string, number]> = [
        [toneOfVoice, setToneOfVoice, "tone_of_voice", 50],
        [contentStyle, setContentStyle, "content_style", 50],
        [keyMessages, setKeyMessages, "key_messages", 0],
        [topicsToAvoid, setTopicsToAvoid, "topics_to_avoid", 0],
      ];
      const brandFields: Array<[string, (v: string) => void, string, number]> = [
        [targetAudience, setTargetAudience, "target_audience", 0],
        [brandValues, setBrandValues, "brand_values", 0],
        [keyCompetitors, setKeyCompetitors, "key_competitors", 0],
      ];

      const targets = [...guidelineFields, ...brandFields];
      let filled = 0;
      let skipped = 0;

      targets.forEach(([current, setter, key, cap]) => {
        if (current && current.trim()) {
          skipped += 1;   // already written by the user — leave it alone
          return;
        }
        let value = (info?.[key] || "").trim();
        if (!value) return;
        if (cap > 0 && value.length > cap) {
          // Trim on a word boundary so the result still reads as a phrase.
          value = value.slice(0, cap);
          const lastSpace = value.lastIndexOf(" ");
          if (lastSpace > cap * 0.6) value = value.slice(0, lastSpace);
          value = value.replace(/[,;:\-\s]+$/, "");
        }
        setter(value);
        filled += 1;
      });

      if (filled === 0) {
        toast({
          title: skipped > 0 ? "Nothing to fill" : "No suggestions returned",
          description:
            skipped > 0
              ? "Every field already has content. Clear a field to have it filled."
              : "The model did not return anything for these fields. Try again.",
        });
      } else {
        toast({
          title: `Filled ${filled} field${filled === 1 ? "" : "s"}`,
          description:
            (skipped > 0 ? `${skipped} left untouched because they already had content. ` : "") +
            "Review the suggestions, then press Save.",
        });
      }
    } catch (err: unknown) {
      toast({
        title: "Could not generate suggestions",
        description:
          err instanceof Error && err.message
            ? err.message
            : "The request failed. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsFillingGuidelines(false);
    }
  };

  /**
   * Export the health-check result to a .csv on the user's computer.
   *
   * Pure client-side: `healthData` is already in state after a check runs, so
   * there is no request, no cost and nothing to wait for.
   */
  // CRLF is what Excel expects; the BOM makes it read the file as UTF-8 so
  // accented characters and en-dashes survive rather than becoming mojibake.
  const CSV_NEWLINE = String.fromCharCode(13, 10);
  const CSV_BOM = String.fromCharCode(0xfeff);

  const escapeCsv = (value: unknown): string => {
    const text = value === null || value === undefined ? "" : String(value);
    // Check messages are free text — "Found 3 blocks (Schema.org), 2 valid" —
    // so commas, quotes and newlines all appear. Quote everything and double
    // any inner quote, which is what Excel and Sheets expect.
    return `"${text.replace(/"/g, '""')}"`;
  };

  const handleExportHealthCsv = () => {
    if (!healthData) return;

    const rows: string[][] = [];
    rows.push([
      "Category", "Check", "Status", "Score", "Max Score", "Importance", "Message",
    ]);

    // Prefer the grouped shape; fall back to the flat list the API returns for
    // older results, so an export never silently produces a header-only file.
    const categories = healthData.categories as
      | Array<{ name?: string; status?: string; checks?: Array<Record<string, unknown>> }>
      | undefined;

    if (Array.isArray(categories) && categories.length > 0) {
      categories.forEach((category) => {
        const checks = Array.isArray(category?.checks) ? category.checks : [];
        if (checks.length === 0) {
          // Categories awaiting an API key carry no checks. Say so in the file
          // rather than dropping the row, so the reader knows it was not run.
          rows.push([
            category?.name ?? "",
            "(no checks run)",
            category?.status === "coming_soon" ? "not configured" : "no data",
            "", "", "", "",
          ]);
          return;
        }
        checks.forEach((check) => {
          rows.push([
            category?.name ?? "",
            String(check?.name ?? ""),
            String(check?.status ?? ""),
            String(check?.score ?? ""),
            String(check?.max_score ?? ""),
            String(check?.importance ?? ""),
            String(check?.message ?? ""),
          ]);
        });
      });
    } else if (Array.isArray(healthData.checks)) {
      healthData.checks.forEach((check: Record<string, unknown>) => {
        rows.push([
          String(check?.category ?? ""),
          String(check?.name ?? ""),
          String(check?.status ?? ""),
          String(check?.score ?? ""),
          String(check?.max_score ?? ""),
          String(check?.importance ?? ""),
          String(check?.message ?? ""),
        ]);
      });
    }

    // Summary last, so the per-check rows stay a clean rectangular table that
    // sorts and filters properly in a spreadsheet.
    rows.push([]);
    rows.push(["Summary"]);
    rows.push(["Domain", domain?.name ?? ""]);
    rows.push(["URL", domain?.url ?? ""]);
    rows.push(["Grade", String(healthData.grade ?? "")]);
    rows.push(["Score", `${healthData.health_score ?? ""} / ${healthData.max_score ?? ""}`]);
    rows.push(["Percentage", String(healthData.percentage ?? "")]);
    rows.push(["Passed", String(healthData.summary?.passed ?? "")]);
    rows.push(["Warnings", String(healthData.summary?.warnings ?? "")]);
    rows.push(["Failed", String(healthData.summary?.failed ?? "")]);
    rows.push(["Exported", new Date().toISOString()]);

    const csv = rows.map((row) => row.map(escapeCsv).join(",")).join(CSV_NEWLINE);

    // The BOM makes Excel read it as UTF-8; without it accented characters and
    // the en-dashes these messages use come out as mojibake.
    const blob = new Blob([CSV_BOM + csv], { type: "text/csv;charset=utf-8;" });

    const slug = (domain?.name || "domain")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 50);

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `health-check-${slug || "domain"}-${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    toast({
      title: "Health check exported",
      description: `${link.download}`,
    });
  };

  /** Saves all seven fields: identity and voice are one document now. */
  const handleSaveGuidelines = async () => {
    if (!domain) return;

    try {
      setIsSavingGuidelines(true);
      const fields = {
        tone_of_voice: toneOfVoice.trim() || null,
        content_style: contentStyle.trim() || null,
        key_messages: keyMessages.trim() || null,
        topics_to_avoid: topicsToAvoid.trim() || null,
        target_audience: targetAudience.trim() || null,
        brand_values: brandValues.trim() || null,
        key_competitors: keyCompetitors.trim() || null,
      };
      await apiClient.updateDomain(domain.id, fields);

      setDomain({ ...domain, ...fields });

      toast({
        title: "Brand guidelines saved",
        description: "Your brand guidelines have been updated successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Error saving guidelines",
        description: error.message || "Failed to save content guidelines.",
        variant: "destructive",
      });
    } finally {
      setIsSavingGuidelines(false);
    }
  };

  const hasGuidelinesChanged = () => {
    if (!domain) return false;
    return (
      toneOfVoice !== (domain.tone_of_voice || "") ||
      contentStyle !== (domain.content_style || "") ||
      keyMessages !== (domain.key_messages || "") ||
      topicsToAvoid !== (domain.topics_to_avoid || "")
    );
  };

  const hasBrandIdentityChanged = () => {
    if (!domain) return false;
    return (
      targetAudience !== (domain.target_audience || "") ||
      brandValues !== (domain.brand_values || "") ||
      keyCompetitors !== (domain.key_competitors || "")
    );
  };

  // Load integrations for this domain
  const loadIntegrations = async () => {
    if (!domain) return;
    try {
      setIsLoadingIntegrations(true);
      const response = await apiClient.getIntegrationsByDomain(domain.id);
      setIntegrations(response || []);
    } catch (error) {
      console.error('Failed to load integrations:', error);
    } finally {
      setIsLoadingIntegrations(false);
    }
  };

  // Load integrations when domain changes
  useEffect(() => {
    if (domain) {
      loadIntegrations();
    }
  }, [domain?.id]);

  // Auto-open property/site selection dialog after OAuth if needed
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const type = urlParams.get('type');
    
    // If OAuth just completed, check if property/site selection is needed
    if (success === 'google_connected' && integrations.length > 0 && !showPropertySelection) {
      const integration = integrations.find(
        (i: any) => i.type === type && 
        i.status === 'active' && 
        (!i.provider_id || i.provider_id === '' || i.provider_id === 'pending_selection')
      );
      
      if (integration) {
        // Small delay to ensure UI is ready and toast is shown
        setTimeout(() => {
          handleOpenPropertySelection(integration);
        }, 1000);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [integrations]);

  // Check for OAuth success/error in URL params and auto-open property selection if needed
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const success = urlParams.get('success');
    const error = urlParams.get('error');
    const type = urlParams.get('type');
    const tab = urlParams.get('tab');

    if (success === 'google_connected') {
      const integrationName = type === 'search_console' ? 'Google Search Console' : 'Google Analytics';
      const integrationStatus = urlParams.get('status');
      if (integrationStatus === 'disconnected') {
        const noItemsLabel = type === 'search_console' ? 'sites' : 'properties';
        toast({
          title: `No ${integrationName} ${noItemsLabel} found`,
          description: `Your Google account was authenticated, but no ${noItemsLabel} were found. Please ensure ${integrationName} is set up for this account.`,
          variant: "destructive",
        });
      } else {
        toast({
          title: `${integrationName} Connected`,
          description: `Your ${integrationName} account has been successfully connected.`,
        });
      }
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
      loadIntegrations();
    }

    if (error) {
      const errorMessages: Record<string, string> = {
        'google_auth_denied': 'Google authentication was denied.',
        'missing_params': 'Missing required parameters.',
        'invalid_state': 'Invalid authentication state.',
        'domain_not_found': 'Domain not found.',
        'oauth_failed': 'OAuth authentication failed.',
      };
      toast({
        title: "Connection Failed",
        description: errorMessages[error] || 'Failed to connect Google service.',
        variant: "destructive",
      });
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleConnectGoogleAnalytics = async () => {
    if (!domain) return;
    try {
      setIsConnectingGA(true);
      const response: any = await apiClient.getGoogleAuthUrl(domain.id, 'google_analytics');
      if (response.authorization_url) {
        // Redirect to Google OAuth
        window.location.href = response.authorization_url;
      }
    } catch (error: any) {
      toast({
        title: "Connection Error",
        description: error.message || "Failed to initiate Google Analytics connection.",
        variant: "destructive",
      });
      setIsConnectingGA(false);
    }
  };

  const handleConnectGoogleSearchConsole = async () => {
    if (!domain) return;
    try {
      setIsConnectingGSC(true);
      const response: any = await apiClient.getGoogleAuthUrl(domain.id, 'search_console');
      if (response.authorization_url) {
        // Redirect to Google OAuth
        window.location.href = response.authorization_url;
      }
    } catch (error: any) {
      toast({
        title: "Connection Error",
        description: error.message || "Failed to initiate Google Search Console connection.",
        variant: "destructive",
      });
      setIsConnectingGSC(false);
    }
  };

  const handleDisconnectIntegration = async (integrationId: number) => {
    try {
      await apiClient.disconnectIntegration(integrationId);
      toast({
        title: "Disconnected",
        description: "Integration has been disconnected successfully.",
      });
      loadIntegrations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to disconnect integration.",
        variant: "destructive",
      });
    }
  };

  const handleRemoveIntegration = async (integrationId: number) => {
    try {
      await apiClient.deleteIntegration(integrationId);
      toast({
        title: "Removed",
        description: "Integration has been removed successfully.",
      });
      loadIntegrations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to remove integration.",
        variant: "destructive",
      });
    }
  };

  // Get integration by type (includes active and disconnected)
  const getIntegration = (type: string) => {
    return integrations.find(i => i.type === type);
  };

  // Check if integration needs property selection
  const needsPropertySelection = (integration: any) => {
    return integration && 
           integration.status === 'active' && 
           (!integration.provider_id || integration.provider_id === '' || integration.provider_id === 'pending_selection');
  };

  // Check if integration is properly connected (has provider_id)
  const isProperlyConnected = (integration: any) => {
    return integration && 
           integration.status === 'active' && 
           integration.provider_id && 
           integration.provider_id !== '' && 
           integration.provider_id !== 'pending_selection';
  };

  // Open property/site selection dialog
  const handleOpenPropertySelection = async (integration: any) => {
    if (!domain) return;
    
    setSelectedIntegration(integration);
    setShowPropertySelection(true);
    setSelectedPropertyId("");
    setSelectedSiteId("");
    setIsLoadingProperties(true);
    setProperties([]);
    setSites([]);

    try {
      if (integration.type === 'google_analytics') {
        const response: any = await apiClient.getGAProperties({
          integrationId: integration.id,
          domainId: domain.id,
        });
        
        if (response.properties && Array.isArray(response.properties)) {
          setProperties(response.properties);
        } else {
          toast({
            title: "No Properties Found",
            description: "No Google Analytics properties were found for this account.",
            variant: "destructive",
          });
        }
      } else if (integration.type === 'search_console') {
        const response: any = await apiClient.getGSCSites({
          integrationId: integration.id,
          domainId: domain.id,
        });
        
        if (response.sites && Array.isArray(response.sites)) {
          setSites(response.sites);
        } else {
          toast({
            title: "No Sites Found",
            description: "No Google Search Console sites were found for this account.",
            variant: "destructive",
          });
        }
      }
    } catch (error: any) {
      const errorType = integration.type === 'google_analytics' ? 'properties' : 'sites';
      toast({
        title: `Error Loading ${errorType === 'properties' ? 'Properties' : 'Sites'}`,
        description: error.message || `Failed to load ${errorType === 'properties' ? 'Google Analytics properties' : 'Google Search Console sites'}.`,
        variant: "destructive",
      });
    } finally {
      setIsLoadingProperties(false);
    }
  };

  // Handle property/site selection
  const handleSelectProperty = async () => {
    if (!selectedIntegration) {
      toast({
        title: "Selection Required",
        description: "Please select an item to continue.",
        variant: "destructive",
      });
      return;
    }

    if (selectedIntegration.type === 'google_analytics') {
      if (!selectedPropertyId) {
        toast({
          title: "Selection Required",
          description: "Please select a property to continue.",
          variant: "destructive",
        });
        return;
      }

      const selectedProperty = properties.find((p: any) => p.id === selectedPropertyId);
      if (!selectedProperty) {
        toast({
          title: "Invalid Property",
          description: "The selected property is invalid.",
          variant: "destructive",
        });
        return;
      }

      setIsSelectingProperty(true);
      try {
        await apiClient.selectGAProperty(
          selectedIntegration.id,
          selectedProperty.id,
          selectedProperty.display_name || selectedProperty.id
        );
        
        toast({
          title: "Property Selected",
          description: `Successfully connected to ${selectedProperty.display_name || selectedProperty.id}`,
        });
        
        // Reload integrations to get updated provider_id
        await loadIntegrations();
        setShowPropertySelection(false);
        setSelectedIntegration(null);
        setSelectedPropertyId("");
        setProperties([]);
      } catch (error: any) {
        toast({
          title: "Selection Failed",
          description: error.message || "Failed to select property.",
          variant: "destructive",
        });
      } finally {
        setIsSelectingProperty(false);
      }
    } else if (selectedIntegration.type === 'search_console') {
      if (!selectedSiteId) {
        toast({
          title: "Selection Required",
          description: "Please select a site to continue.",
          variant: "destructive",
        });
        return;
      }

      const selectedSite = sites.find((s: any) => s.id === selectedSiteId);
      if (!selectedSite) {
        toast({
          title: "Invalid Site",
          description: "The selected site is invalid.",
          variant: "destructive",
        });
        return;
      }

      setIsSelectingProperty(true);
      try {
        await apiClient.selectGSCSite(
          selectedIntegration.id,
          selectedSite.id,
          selectedSite.display_name || selectedSite.id
        );
        
        toast({
          title: "Site Selected",
          description: `Successfully connected to ${selectedSite.display_name || selectedSite.id}`,
        });
        
        // Reload integrations to get updated provider_id
        await loadIntegrations();
        setShowPropertySelection(false);
        setSelectedIntegration(null);
        setSelectedSiteId("");
        setSites([]);
      } catch (error: any) {
        toast({
          title: "Selection Failed",
          description: error.message || "Failed to select site.",
          variant: "destructive",
        });
      } finally {
        setIsSelectingProperty(false);
      }
    }
  };

  if (isLoading) {
    return <PageLoader />;
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
              src={getFaviconUrl(domain.url, 32)}
              alt={`${domain.name} favicon`}
              className="h-8 w-8 rounded"
              onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
            />
            <div>
              <h1 className="text-3xl font-bold capitalize">{domain.name}</h1>
              <a
                href={domain.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-primary hover:underline transition-colors inline-flex items-center gap-1"
              >
                {domain.url}
                <Link2 className="h-3 w-3" />
              </a>
            </div>
          </div>
        </div>
        {!isTeamMember && (
          <Button onClick={() => {
            if (domain) {
              const storeDomain = domains.find(d => d.id === domain.id);
              if (storeDomain) {
                setSelectedDomain(storeDomain);
              }
            }
            navigate('/seo-rankings/add-keyword');
          }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Keywords
          </Button>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="bg-muted/50 p-1 border border-border">
          {!isTeamMember && !isClient && (
              <TabsTrigger value="basic-info" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <Info className="h-4 w-4" />
              Basic Info
            </TabsTrigger>
          )}
          {!isTeamMember && !isClient && (
              <TabsTrigger value="content-guidelines" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <FileText className="h-4 w-4" />
              Brand Guidelines
            </TabsTrigger>
          )}
          {!isTeamMember && !isClient && (
              <TabsTrigger value="internal-links" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <Link2 className="h-4 w-4" />
              Internal Links
            </TabsTrigger>
          )}
            {!isClient && (
            <TabsTrigger value="integrations" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <Link2 className="h-4 w-4" />
            Integrations
          </TabsTrigger>
            )}
          {!isTeamMember && !isClient && (
            <TabsTrigger value="schedule" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <CalendarClock className="h-4 w-4" />
              Schedule
            </TabsTrigger>
          )}
          {!isTeamMember && (
            <TabsTrigger value="health" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <Activity className="h-4 w-4" />
              Health
            </TabsTrigger>
          )}
          {!isTeamMember && !isClient && (
              <TabsTrigger value="reference-repository" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <BookOpen className="h-4 w-4" />
              Reference
            </TabsTrigger>
          )}
          {!isTeamMember && !isClient && (
              <TabsTrigger value="client-access" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
              <ShieldCheck className="h-4 w-4" />
              Client Access
            </TabsTrigger>
          )}
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
                    value={domainName}
                    onChange={(e) => setDomainName(e.target.value)}
                    placeholder="Enter domain name"
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
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={domain.country || "United States"}
                    disabled
                    className="bg-muted"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="short-description">Brand Description</Label>
                <Textarea
                  id="short-description"
                  value={shortDescription}
                  onChange={(e) => setShortDescription(e.target.value)}
                  placeholder="Enter a brief description of your brand (e.g., Leading provider of cloud-based HR solutions for small businesses)"
                  className="min-h-[80px]"
                  maxLength={500}
                />
                <p className="text-xs text-muted-foreground">
                  {shortDescription.length}/500 characters
                </p>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleSaveBasicInfo}
                  disabled={isSavingBasicInfo || !hasBasicInfoChanged() || !domainName.trim()}
                >
                  {isSavingBasicInfo ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Saving...
                    </>
                  ) : (
                    "Save"
                  )}
                </Button>
              </div>
              <Separator />
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
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1.5">
                  <CardTitle>Brand Guidelines</CardTitle>
                  <CardDescription>
                    Who your brand is and how it should sound. Everything here steers the content
                    the AI writes for you, and is auto-populated when a new brand is created.
                  </CardDescription>
                </div>
                {/* Fills only the blank fields on this tab. Anything already
                    written is left untouched. */}
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2 shrink-0"
                  onClick={autoFillFields}
                  disabled={isFillingGuidelines || isSavingGuidelines || !domain}
                >
                  {isFillingGuidelines ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  {isFillingGuidelines ? "Generating..." : "Auto-fill with AI"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1 pb-1">
                <h3 className="text-sm font-semibold">Brand Identity</h3>
                <p className="text-xs text-muted-foreground">
                  Who you are, who you sell to, and who you are measured against.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="target-audience">Target Audience</Label>
                <Textarea
                  id="target-audience"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="Describe your target audience demographics and preferences..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="brand-values">Brand Values</Label>
                <Textarea
                  id="brand-values"
                  value={brandValues}
                  onChange={(e) => setBrandValues(e.target.value)}
                  placeholder="List your brand's core values..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="competitors-brand">Key Competitors</Label>
                <Textarea
                  id="competitors-brand"
                  value={keyCompetitors}
                  onChange={(e) => setKeyCompetitors(e.target.value)}
                  placeholder="List your main competitors..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-1 pt-4 pb-1 border-t border-border">
                <h3 className="text-sm font-semibold pt-3">Content Guidelines</h3>
                <p className="text-xs text-muted-foreground">
                  How the AI should write for you — and what it should stay away from.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="tone-of-voice">Tone of Voice</Label>
                <Textarea
                  id="tone-of-voice"
                  value={toneOfVoice}
                  onChange={(e) => setToneOfVoice(e.target.value)}
                  placeholder="Describe your brand's tone of voice (e.g., professional, friendly, authoritative...)"
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="content-style">Content Style</Label>
                <Textarea
                  id="content-style"
                  value={contentStyle}
                  onChange={(e) => setContentStyle(e.target.value)}
                  placeholder="Describe your preferred content style (e.g., concise, detailed, technical...)"
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="key-messages">Key Messages</Label>
                <Textarea
                  id="key-messages"
                  value={keyMessages}
                  onChange={(e) => setKeyMessages(e.target.value)}
                  placeholder="List key messages or themes to emphasize in content..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="avoid-topics">Topics to Avoid</Label>
                <Textarea
                  id="avoid-topics"
                  value={topicsToAvoid}
                  onChange={(e) => setTopicsToAvoid(e.target.value)}
                  placeholder="List topics or themes to avoid in content..."
                  className="min-h-[100px]"
                />
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleSaveGuidelines}
                  disabled={isSavingGuidelines || !(hasGuidelinesChanged() || hasBrandIdentityChanged())}
                >
                  {isSavingGuidelines ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Brand Guidelines"
                  )}
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
                Connect external services to track traffic from AI platforms and analyze website performance
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Google Analytics */}
              <div className={`p-4 border rounded-lg ${isProperlyConnected(getIntegration('google_analytics')) ? 'border-green-500 bg-green-50' : getIntegration('google_analytics')?.status === 'disconnected' && !getIntegration('google_analytics')?.has_credentials ? 'border-red-200 bg-red-50' : getIntegration('google_analytics')?.status === 'disconnected' && getIntegration('google_analytics')?.has_credentials ? 'border-amber-300 bg-amber-50' : ''}`}>
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
                      <p className="text-sm text-muted-foreground">
                        {getIntegration('google_analytics') ? (
                          isProperlyConnected(getIntegration('google_analytics')) ? (
                            <>
                              Connected - Track AI referral traffic
                              {(getIntegration('google_analytics')?.credentials?.selected_property_name || getIntegration('google_analytics')?.provider_id) && (
                                <span className="block mt-1 text-xs font-medium text-gray-700">
                                  Property: {getIntegration('google_analytics')?.credentials?.selected_property_name ||
                                    getIntegration('google_analytics')?.provider_id?.replace('properties/', '') ||
                                    getIntegration('google_analytics')?.provider_id}
                                </span>
                              )}
                            </>
                          ) : getIntegration('google_analytics')?.status === 'disconnected' && getIntegration('google_analytics')?.has_credentials ? (
                            'Authenticated - No GA4 properties found. Try reconnecting or check your Google Analytics setup.'
                          ) : getIntegration('google_analytics')?.status === 'disconnected' ? (
                            'Not connected - No properties found'
                          ) : (
                            'Please select a property to complete the connection'
                          )
                        ) : (
                          'Track website traffic and AI platform referrals'
                        )}
                      </p>
                    </div>
                  </div>
                  {getIntegration('google_analytics') ? (
                    isProperlyConnected(getIntegration('google_analytics')) ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-green-600 font-medium">Connected</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDisconnectIntegration(getIntegration('google_analytics')!.id)}
                        >
                          Disconnect
                        </Button>
                      </div>
                    ) : getIntegration('google_analytics')?.status === 'disconnected' && getIntegration('google_analytics')?.has_credentials ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-amber-600 font-medium">Authenticated</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            await handleRemoveIntegration(getIntegration('google_analytics')!.id);
                            handleConnectGoogleAnalytics();
                          }}
                        >
                          Reconnect
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveIntegration(getIntegration('google_analytics')!.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ) : getIntegration('google_analytics')?.status === 'disconnected' ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-red-600 font-medium">Not Connected</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveIntegration(getIntegration('google_analytics')!.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ) : needsPropertySelection(getIntegration('google_analytics')) ? (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleOpenPropertySelection(getIntegration('google_analytics')!)}
                      >
                        Select Property
                      </Button>
                    ) : null
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleConnectGoogleAnalytics}
                      disabled={isConnectingGA}
                    >
                      {isConnectingGA ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        'Connect'
                      )}
                    </Button>
                  )}
                </div>
              </div>

              {/* Google Search Console */}
              <div className={`p-4 border rounded-lg ${isProperlyConnected(getIntegration('search_console')) ? 'border-green-500 bg-green-50' : getIntegration('search_console')?.status === 'disconnected' && !getIntegration('search_console')?.has_credentials ? 'border-red-200 bg-red-50' : getIntegration('search_console')?.status === 'disconnected' && getIntegration('search_console')?.has_credentials ? 'border-amber-300 bg-amber-50' : ''}`}>
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
                      <p className="text-sm text-muted-foreground">
                        {getIntegration('search_console') ? (
                          isProperlyConnected(getIntegration('search_console')) ? (
                            <>
                              Connected - Monitor search performance
                              {(getIntegration('search_console')?.credentials?.selected_site_name || getIntegration('search_console')?.provider_id) && (
                                <span className="block mt-1 text-xs font-medium text-gray-700">
                                  Site: {getIntegration('search_console')?.credentials?.selected_site_name ||
                                    getIntegration('search_console')?.provider_id?.replace('sc-domain:', '')?.replace('https://', '')?.replace('http://', '')?.replace(/\/$/, '') ||
                                    getIntegration('search_console')?.provider_id}
                                </span>
                              )}
                            </>
                          ) : getIntegration('search_console')?.status === 'disconnected' && getIntegration('search_console')?.has_credentials ? (
                            'Authenticated - No Search Console sites found. Try reconnecting or verify your site in Google Search Console.'
                          ) : getIntegration('search_console')?.status === 'disconnected' ? (
                            'Not connected - No sites found'
                          ) : (
                            'Please select a site to complete the connection'
                          )
                        ) : (
                          'Monitor search performance and queries'
                        )}
                      </p>
                    </div>
                  </div>
                  {getIntegration('search_console') ? (
                    isProperlyConnected(getIntegration('search_console')) ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-green-600 font-medium">Connected</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDisconnectIntegration(getIntegration('search_console')!.id)}
                        >
                          Disconnect
                        </Button>
                      </div>
                    ) : getIntegration('search_console')?.status === 'disconnected' && getIntegration('search_console')?.has_credentials ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-amber-600 font-medium">Authenticated</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            await handleRemoveIntegration(getIntegration('search_console')!.id);
                            handleConnectGoogleSearchConsole();
                          }}
                        >
                          Reconnect
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveIntegration(getIntegration('search_console')!.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ) : getIntegration('search_console')?.status === 'disconnected' ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-red-600 font-medium">Not Connected</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRemoveIntegration(getIntegration('search_console')!.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    ) : needsPropertySelection(getIntegration('search_console')) ? (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleOpenPropertySelection(getIntegration('search_console')!)}
                      >
                        Select Site
                      </Button>
                    ) : null
                  ) : (
                    <Button
                      variant="outline"
                      onClick={handleConnectGoogleSearchConsole}
                      disabled={isConnectingGSC}
                    >
                      {isConnectingGSC ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        'Connect'
                      )}
                    </Button>
                  )}
                </div>
              </div>

              <div className="text-sm text-muted-foreground text-center py-4">
                More integrations coming soon (Slack, Webhooks, etc.)
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Health Tab */}
        {/* Sweep schedule — its own tab rather than a field on Basic
            Information, so the one control that costs money per change is not
            buried among brand copy. */}
        <TabsContent value="schedule" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <CardTitle>Sweep schedule</CardTitle>
              <CardDescription>
                The full sweep re-runs every prompt of this project on every AI
                platform. Choose how often that happens.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {(() => {
                // The store's copy is the full Domain the API returned; this
                // page keeps a trimmed shape with no prompt_count on it.
                const stored = domains.find((x) => x.id === domain.id);
                const draft = stored && { ...stored, sweep_cadence: sweepCadence };
                return (
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-lg border p-3">
                      <div className="text-2xl font-bold tabular-nums">
                        {(stored?.prompt_count ?? 0).toLocaleString()}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">prompts</div>
                    </div>
                    <div className="rounded-lg border p-3">
                      <div className="text-2xl font-bold tabular-nums">
                        {stored && sweep?.platforms?.length
                          ? `$\u2009${creditsPerSweep(stored, sweep.platforms).toFixed(2)}`
                          : "—"}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        cost per sweep
                      </div>
                    </div>
                    <div className="rounded-lg border p-3">
                      <div className="text-2xl font-bold">
                        {draft
                          ? describeNextSweep(draft, sweep?.enabled !== false).label
                          : "—"}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">next sweep</div>
                    </div>
                  </div>
                );
              })()}

              <div className="space-y-2 max-w-sm">
                <Label htmlFor="sweep-cadence">How often</Label>
                <Select
                  value={sweepCadence}
                  onValueChange={(v) => setSweepCadence(v as Cadence)}
                >
                  <SelectTrigger id="sweep-cadence">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CADENCE_OPTIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {o.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  A change applies from the next sweep — it does not start or cancel a
                  run already under way.
                </p>
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={handleSaveSchedule}
                  disabled={isSavingSchedule || !hasScheduleChanged()}
                >
                  {isSavingSchedule ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* What the sweep actually walks. One row per prompt group, the same
              way the Prompts page is organised, so the two read alike. Every
              figure comes from this project's real counts and the cadence
              selected above - change the dropdown and the table moves with it,
              before anything is saved. */}
          <Card className="border border-border">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[34%]">Target</TableHead>
                    <TableHead>Cadence</TableHead>
                    <TableHead className="text-right">LLMs</TableHead>
                    <TableHead className="text-right">Runs</TableHead>
                    <TableHead className="text-right">Cost / run</TableHead>
                    <TableHead>Next run</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scheduleGroups === null ? (
                    <TableRow>
                      <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                        Loading prompt groups...
                      </TableCell>
                    </TableRow>
                  ) : scheduleGroups.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
                        This project has no prompt groups yet, so a sweep would have
                        nothing to run.
                      </TableCell>
                    </TableRow>
                  ) : (
                    scheduleGroups.map((g) => {
                      const platforms = sweep?.platforms?.length ?? 0;
                      const paused = sweepCadence === "off";
                      const stored = domains.find((x) => x.id === domain.id);
                      const perPrompt =
                        stored && platforms && (stored.prompt_count ?? 0) > 0
                          ? creditsPerSweep(stored, sweep!.platforms) / (stored.prompt_count ?? 1)
                          : 0;
                      return (
                        <TableRow key={g.id}>
                          <TableCell>
                            <div className="font-medium">{g.group_id}</div>
                            <div className="text-xs text-muted-foreground mt-0.5">
                              Group &middot; {g.prompts_count} prompt
                              {g.prompts_count === 1 ? "" : "s"}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm">
                            {CADENCE_OPTIONS.find((o) => o.value === sweepCadence)?.label}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {platforms || "\u2014"}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {g.prompts_count}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {perPrompt ? `$\u2009${(g.prompts_count * perPrompt).toFixed(2)}` : "\u2014"}
                          </TableCell>
                          <TableCell className="text-sm">
                            <span className="inline-flex items-center gap-2">
                              {stored
                                ? describeNextSweep(
                                    { ...stored, sweep_cadence: sweepCadence },
                                    sweep?.enabled !== false,
                                  ).label
                                : "\u2014"}
                              {g.prompts_in_flight > 0 && (
                                <span
                                  className="h-1.5 w-1.5 rounded-full bg-amber-500"
                                  title={`${g.prompts_in_flight} prompt(s) running now`}
                                />
                              )}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant={paused ? "secondary" : "outline"}>
                              {paused ? "Paused" : "Active"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="health" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Website Health Check</CardTitle>
                <div className="flex items-center gap-2">
                {/* Export is client-side only — healthData is already in state,
                    so there is no request to make. Appears only once a check has
                    run: with no result there is nothing to export. */}
                {healthData && (
                  <Button
                    onClick={handleExportHealthCsv}
                    size="sm"
                    variant="outline"
                    className="gap-2"
                    disabled={isLoadingHealth}
                    title="Download the results as a .csv"
                  >
                    <Download className="h-4 w-4" />
                    Export CSV
                  </Button>
                )}
                {/* Hide button when domain is processing */}
                {domain?.processing_status !== 'PROC' && domain?.processing_status !== 'SCHD' && (
                  <Button
                    onClick={fetchHealthCheck}
                    disabled={isLoadingHealth}
                    size="sm"
                    variant="outline"
                  >
                    {isLoadingHealth ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Checking...
                      </>
                    ) : (
                      <>
                        <Activity className="h-4 w-4 mr-2" />
                        Run Health Check
                      </>
                    )}
                  </Button>
                )}
                </div>
              </div>
              <CardDescription>
                Technical assessment of your website's AI-friendliness and SEO optimization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {domain?.processing_status === 'PROC' || domain?.processing_status === 'SCHD' ? (
                <div className="flex items-center justify-center p-12">
                  <div className="text-center space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                    <p className="text-sm text-muted-foreground">Domain is currently being processed...</p>
                    <p className="text-xs text-muted-foreground">Health check will be available once processing is complete</p>
                  </div>
                </div>
              ) : isLoadingHealth ? (
                <div className="flex items-center justify-center p-12">
                  <div className="text-center space-y-3">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                    <p className="text-sm text-muted-foreground">Analyzing your website...</p>
                  </div>
                </div>
              ) : healthError ? (
                <div className="p-6 bg-destructive/10 rounded-lg border border-destructive/20 text-center">
                  <XCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
                  <p className="text-sm text-destructive font-medium">{healthError}</p>
                  <Button
                    onClick={fetchHealthCheck}
                    variant="outline"
                    size="sm"
                    className="mt-4"
                  >
                    Try Again
                  </Button>
                </div>
              ) : healthData ? (
                <>
                  {/* Overall Score & Summary Stats - 50/50 Layout */}
                  <div className="grid grid-cols-2 gap-6">
                    {/* Left side - Overall Score (50% width) */}
                    <Card className="p-8 bg-gradient-to-br from-primary/5 via-primary/3 to-background border-primary/20 shadow-lg shadow-primary/5 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-8xl font-bold bg-gradient-to-br from-primary to-primary/60 bg-clip-text text-transparent mb-3">
                          {healthData.percentage}
                        </div>
                        <div className="text-base text-muted-foreground mb-2">
                          out of 100
                        </div>
                        <div className="text-sm text-muted-foreground/80 mb-5">
                          ({healthData.health_score}/{healthData.max_score} points)
                        </div>
                        <Badge
                          variant="outline"
                          className={`text-base px-4 py-1.5 ${
                            healthData.grade_color === 'green' ? 'border-green-500 text-green-600 bg-green-50 dark:bg-green-900/20' :
                            healthData.grade_color === 'blue' ? 'border-blue-500 text-blue-600 bg-blue-50 dark:bg-blue-900/20' :
                            healthData.grade_color === 'yellow' ? 'border-yellow-500 text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20' :
                            'border-red-500 text-red-600 bg-red-50 dark:bg-red-900/20'
                          }`}
                        >
                          {healthData.grade}
                        </Badge>
                      </div>
                    </Card>

                    {/* Right side - Summary Stats in 2x2 Grid (50% width) */}
                    <div className="grid grid-cols-2 gap-4">
                      <Card className="p-6 border-green-200 bg-gradient-to-br from-green-50 to-background dark:from-green-900/10 dark:to-background hover:shadow-md transition-shadow">
                        <div className="flex flex-col h-full">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                              <CheckCircle2 className="h-5 w-5 text-green-600" />
                            </div>
                            <span className="text-sm font-medium text-green-900 dark:text-green-100">Passed</span>
                          </div>
                          <div className="flex-1 flex flex-col justify-center">
                            <div className="text-5xl font-bold text-green-600">{healthData.summary.passed}</div>
                            <div className="text-xs text-muted-foreground mt-2">checks successful</div>
                          </div>
                        </div>
                      </Card>
                      <Card className="p-6 border-yellow-200 bg-gradient-to-br from-yellow-50 to-background dark:from-yellow-900/10 dark:to-background hover:shadow-md transition-shadow">
                        <div className="flex flex-col h-full">
                          <div className="flex items-center gap-2 mb-3">
                            <div className="p-2 rounded-lg bg-yellow-100 dark:bg-yellow-900/30">
                              <AlertCircle className="h-5 w-5 text-yellow-600" />
                            </div>
                            <span className="text-sm font-medium text-yellow-900 dark:text-yellow-100">Warnings</span>
                          </div>
                          <div className="flex-1 flex flex-col justify-center">
                            <div className="text-5xl font-bold text-yellow-600">{healthData.summary.warnings}</div>
                            <div className="text-xs text-muted-foreground mt-2">needs attention</div>
                          </div>
                        </div>
                      </Card>
                      <Card className="p-6 border-red-200 bg-gradient-to-br from-red-50 to-background dark:from-red-900/10 dark:to-background hover:shadow-md transition-shadow col-span-2">
                        <div className="flex items-center gap-4">
                          <div className="p-3 rounded-lg bg-red-100 dark:bg-red-900/30">
                            <XCircle className="h-6 w-6 text-red-600" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-red-900 dark:text-red-100">Failed</span>
                              <div className="text-5xl font-bold text-red-600">{healthData.summary.failed}</div>
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">requires fixing</div>
                          </div>
                        </div>
                      </Card>
                    </div>
                  </div>

                  {/* Health Checks by Category */}
                  <div className="space-y-6 mt-8">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold">Detailed Health Checks</h3>
                      <span className="text-sm text-muted-foreground">
                        {healthData.summary?.total_checks || healthData.checks?.length} total checks
                      </span>
                    </div>

                    {healthData.categories ? (
                      healthData.categories.map((category: any) => (
                        <Card key={category.key} className="border border-border overflow-hidden">
                          {/* Category Header */}
                          <div className={`px-6 py-4 flex items-center justify-between border-b ${
                            category.status === 'coming_soon'
                              ? 'bg-muted/50'
                              : 'bg-gradient-to-r from-primary/5 to-background'
                          }`}>
                            <div className="flex items-center gap-3">
                              <h4 className="font-semibold text-base">{category.name}</h4>
                              {category.status === 'coming_soon' && (
                                <Badge variant="outline" className="text-xs border-muted-foreground/30 text-muted-foreground">
                                  Coming Soon
                                </Badge>
                              )}
                            </div>
                            {category.status !== 'coming_soon' && (
                              <div className="flex items-center gap-4 text-xs">
                                <span className="flex items-center gap-1">
                                  <div className="w-2 h-2 rounded-full bg-green-500" />
                                  {category.summary.passed} passed
                                </span>
                                <span className="flex items-center gap-1">
                                  <div className="w-2 h-2 rounded-full bg-yellow-500" />
                                  {category.summary.warnings} warnings
                                </span>
                                <span className="flex items-center gap-1">
                                  <div className="w-2 h-2 rounded-full bg-red-500" />
                                  {category.summary.failed} failed
                                </span>
                                <span className="font-mono font-semibold text-sm ml-2">
                                  {category.score}/{category.max_score}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Category Content */}
                          {category.status === 'coming_soon' ? (
                            <div className="p-6 text-center">
                              <p className="text-sm text-muted-foreground mb-4">
                                {category.placeholder_message || 'These checks will be enabled once the required API is configured.'}
                              </p>
                              <div className="flex flex-wrap gap-2 justify-center">
                                {category.checks.map((check: any, idx: number) => (
                                  <Badge key={idx} variant="outline" className="text-xs text-muted-foreground">
                                    {check.name}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="w-12">Status</TableHead>
                                  <TableHead>Check</TableHead>
                                  <TableHead className="hidden md:table-cell">Details</TableHead>
                                  <TableHead className="w-24 text-right">Score</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {category.checks.map((check: any, index: number) => (
                                  <TableRow
                                    key={index}
                                    className={
                                      check.status === 'pass' ? 'bg-green-50/30 dark:bg-green-900/5' :
                                      check.status === 'warning' ? 'bg-yellow-50/30 dark:bg-yellow-900/5' :
                                      'bg-red-50/30 dark:bg-red-900/5'
                                    }
                                  >
                                    <TableCell>
                                      {check.status === 'pass' ? (
                                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                                      ) : check.status === 'warning' ? (
                                        <AlertCircle className="h-5 w-5 text-yellow-600" />
                                      ) : (
                                        <XCircle className="h-5 w-5 text-red-600" />
                                      )}
                                    </TableCell>
                                    <TableCell className="font-medium text-sm">{check.name}</TableCell>
                                    <TableCell className="hidden md:table-cell text-sm text-muted-foreground max-w-md truncate">
                                      {check.message}
                                    </TableCell>
                                    <TableCell className="text-right">
                                      <span className={`text-xs font-mono font-semibold px-2 py-1 rounded ${
                                        check.status === 'pass' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                        check.status === 'warning' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                      }`}>
                                        {check.score}/{check.max_score}
                                      </span>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          )}
                        </Card>
                      ))
                    ) : (
                      /* Fallback: render flat list for old data without categories */
                      <div className="space-y-2">
                        {healthData.checks && healthData.checks.map((check: any, index: number) => (
                          <Card
                            key={index}
                            className={`p-4 transition-all hover:shadow-md ${
                              check.status === 'pass' ? 'border-green-200/60 bg-gradient-to-r from-green-50/50 to-background dark:from-green-900/5 dark:to-background' :
                              check.status === 'warning' ? 'border-yellow-200/60 bg-gradient-to-r from-yellow-50/50 to-background dark:from-yellow-900/5 dark:to-background' :
                              'border-red-200/60 bg-gradient-to-r from-red-50/50 to-background dark:from-red-900/5 dark:to-background'
                            }`}
                          >
                            <div className="flex items-start gap-4">
                              <div className={`flex-shrink-0 p-2 rounded-lg ${
                                check.status === 'pass' ? 'bg-green-100 dark:bg-green-900/30' :
                                check.status === 'warning' ? 'bg-yellow-100 dark:bg-yellow-900/30' :
                                'bg-red-100 dark:bg-red-900/30'
                              }`}>
                                {check.status === 'pass' ? (
                                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                                ) : check.status === 'warning' ? (
                                  <AlertCircle className="h-5 w-5 text-yellow-600" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-red-600" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-3 mb-2">
                                  <h4 className="font-semibold text-sm leading-tight">{check.name}</h4>
                                  <span className={`text-xs font-mono font-semibold px-2 py-1 rounded ${
                                    check.status === 'pass' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                    check.status === 'warning' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  }`}>
                                    {check.score}/{check.max_score}
                                  </span>
                                </div>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                  {check.message}
                                </p>
                              </div>
                            </div>
                          </Card>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Health Check History */}
                  {healthHistory && healthHistory.history && healthHistory.history.length > 0 && (
                    <div className="mt-10 pt-8 border-t border-border/50">
                      <div className="flex items-center justify-between mb-6">
                        <div>
                          <h3 className="text-lg font-semibold">Health Check History</h3>
                          <p className="text-sm text-muted-foreground mt-1">Track improvements over time</p>
                        </div>
                        {healthHistory.trend && (
                          <Card className={`px-4 py-2 ${
                            healthHistory.trend.direction === 'up' ? 'border-green-200 bg-green-50/50 dark:bg-green-900/10' :
                            healthHistory.trend.direction === 'down' ? 'border-red-200 bg-red-50/50 dark:bg-red-900/10' :
                            'border-gray-200 bg-gray-50/50 dark:bg-gray-900/10'
                          }`}>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-muted-foreground">Trend:</span>
                              <Badge
                                variant="outline"
                                className={`text-sm font-semibold ${
                                  healthHistory.trend.direction === 'up' ? 'border-green-500 text-green-700 bg-green-100 dark:bg-green-900/30' :
                                  healthHistory.trend.direction === 'down' ? 'border-red-500 text-red-700 bg-red-100 dark:bg-red-900/30' :
                                  'border-gray-500 text-gray-700 bg-gray-100 dark:bg-gray-900/30'
                                }`}
                              >
                                {healthHistory.trend.direction === 'up' ? '↑' : healthHistory.trend.direction === 'down' ? '↓' : '→'}
                                {' '}
                                {healthHistory.trend.change > 0 ? '+' : ''}{healthHistory.trend.change}%
                              </Badge>
                            </div>
                          </Card>
                        )}
                      </div>
                      <div className="space-y-3">
                        {healthHistory.history.map((check: any, index: number) => (
                          <Card
                            key={check.id}
                            className={`p-5 transition-all hover:shadow-md ${
                              index === 0 ? 'border-primary/40 bg-gradient-to-r from-primary/5 to-background shadow-sm' : 'border-border/60 bg-card'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-4">
                                <div className={`text-center px-4 py-2 rounded-lg ${
                                  check.grade_color === 'green' ? 'bg-green-100 dark:bg-green-900/30' :
                                  check.grade_color === 'blue' ? 'bg-blue-100 dark:bg-blue-900/30' :
                                  check.grade_color === 'yellow' ? 'bg-yellow-100 dark:bg-yellow-900/30' :
                                  'bg-red-100 dark:bg-red-900/30'
                                }`}>
                                  <div className={`text-3xl font-bold ${
                                    check.grade_color === 'green' ? 'text-green-600' :
                                    check.grade_color === 'blue' ? 'text-blue-600' :
                                    check.grade_color === 'yellow' ? 'text-yellow-600' :
                                    'text-red-600'
                                  }`}>
                                    {check.percentage}
                                  </div>
                                  <div className="text-xs text-muted-foreground font-medium">score</div>
                                </div>
                                <div>
                                  <div className="flex items-center gap-2 mb-1">
                                    <div className="text-sm font-semibold">
                                      {new Date(check.created_at).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        year: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                      })}
                                    </div>
                                    {index === 0 && (
                                      <Badge className="text-xs bg-primary/10 text-primary border-primary/30">
                                        Latest
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                      <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                      {check.summary.passed} passed
                                    </span>
                                    <span className="flex items-center gap-1">
                                      <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                                      {check.summary.warnings} warnings
                                    </span>
                                    <span className="flex items-center gap-1">
                                      <div className="w-2 h-2 rounded-full bg-red-500"></div>
                                      {check.summary.failed} failed
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <Badge
                                variant="outline"
                                className={`text-sm px-3 py-1 font-semibold ${
                                  check.grade_color === 'green' ? 'border-green-500 text-green-700 bg-green-50 dark:bg-green-900/20' :
                                  check.grade_color === 'blue' ? 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-900/20' :
                                  check.grade_color === 'yellow' ? 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-900/20' :
                                  'border-red-500 text-red-700 bg-red-50 dark:bg-red-900/20'
                                }`}
                              >
                                {check.grade}
                              </Badge>
                            </div>
                          </Card>
                        ))}
                      </div>
                      {healthHistory.total_checks > 5 && (
                        <div className="text-center mt-3">
                          <p className="text-xs text-muted-foreground">
                            Showing 5 of {healthHistory.total_checks} total health checks
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center p-12">
                  <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Run Your First Health Check</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Click the "Run Health Check" button above to analyze your website's AI-friendliness
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Internal Links Tab */}
        <TabsContent value="internal-links" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Internal Link Map</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowImportDialog(true)}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Import CSV
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      setNewLinkTopic("");
                      setNewLinkKeywords("");
                      setNewLinkUrl("");
                      setShowAddLinkDialog(true);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Link
                  </Button>
                </div>
              </div>
              <CardDescription>
                Manage internal links that can be automatically inserted into content during generation
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingInternalLinks ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : internalLinks.length === 0 ? (
                <div className="text-center py-12">
                  <Link2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Internal Links Yet</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Add internal links to automatically include them in generated content
                  </p>
                  <Button
                    onClick={() => {
                      setNewLinkTopic("");
                      setNewLinkKeywords("");
                      setNewLinkUrl("");
                      setShowAddLinkDialog(true);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add First Link
                  </Button>
                </div>
              ) : (
                <div className="border rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[200px]">Topic</TableHead>
                        <TableHead className="w-[300px]">Keywords</TableHead>
                        <TableHead>Associated URL</TableHead>
                        <TableHead className="w-[100px] text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {internalLinks.map((link) => (
                        <TableRow key={link.id}>
                          <TableCell className="font-medium">{link.topic}</TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {(link.keywords || '').split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0).slice(0, 3).map((kw: string, idx: number) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {kw}
                                </Badge>
                              ))}
                              {(link.keywords || '').split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0).length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                  +{(link.keywords || '').split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0).length - 3} more
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <a
                              href={link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline flex items-center gap-1 max-w-[300px] truncate"
                            >
                              {link.url}
                              <ExternalLink className="h-3 w-3 flex-shrink-0" />
                            </a>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleOpenEditDialog(link)}
                              >
                                <Edit2 className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeleteInternalLink(link.id)}
                                disabled={isDeletingLink}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reference Repository Tab */}
        <TabsContent value="reference-repository" className="space-y-4 mt-6">
          {/* Brand Links Section */}
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Brand Digital Assets</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs whitespace-nowrap">
                    {brandLinkTotalLinks}/{brandLinkMaxLinks} links
                  </Badge>
                  <Button
                    size="sm"
                    onClick={() => setShowAddBrandLinkDialog(true)}
                    disabled={brandLinkTotalLinks >= brandLinkMaxLinks}
                    className="gap-1"
                  >
                    <Plus className="h-4 w-4" />
                    Add Link
                  </Button>
                </div>
              </div>
              <CardDescription>
                Add your brand's social media profiles, microsites, blogs, and other digital assets. These URLs are crawled and their content is used during AI content generation — just like uploaded documents.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoadingBrandLinks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mr-2" />
                  <span>Loading brand links...</span>
                </div>
              ) : brandLinks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Globe className="h-10 w-10 mx-auto mb-3 opacity-30" />
                  <p className="text-base font-medium">No brand links yet</p>
                  <p className="text-sm mt-1">Add your social media profiles, microsites, or blog URLs for better brand context.</p>
                </div>
              ) : (
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Platform</TableHead>
                        <TableHead>URL</TableHead>
                        <TableHead className="hidden md:table-cell">Label</TableHead>
                        <TableHead className="w-28">Status</TableHead>
                        <TableHead className="w-36 hidden sm:table-cell">Added</TableHead>
                        <TableHead className="w-28 text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {brandLinks.map((link: any) => (
                        <TableRow key={link.id}>
                          <TableCell>
                            <div className="flex items-center justify-center">
                              {getPlatformIcon(link.platform)}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="font-medium text-sm truncate max-w-[250px]">
                              <a href={link.url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                                {link.url}
                                <ExternalLink className="h-3 w-3 flex-shrink-0" />
                              </a>
                            </div>
                            <div className="text-xs text-muted-foreground">{link.platform_display}</div>
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            <span className="text-sm text-muted-foreground">{link.label || '—'}</span>
                          </TableCell>
                          <TableCell>
                            {getExtractionStatusBadge(link.extraction_status)}
                          </TableCell>
                          <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                            {new Date(link.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleViewBrandLinkContent(link)}
                                className="h-8 w-8"
                                title="View extracted content"
                              >
                                <Eye className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleRecrawlBrandLink(link.id)}
                                className="h-8 w-8"
                                title="Re-crawl URL"
                              >
                                <RefreshCw className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeleteBrandLink(link.id)}
                                disabled={isDeletingBrandLink}
                                className="h-8 w-8"
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Reference Documents Section */}
          <Card className="border border-border">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Reference Documents</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs whitespace-nowrap">
                    {refDocTotalFiles}/{refDocMaxFiles} files
                  </Badge>
                  <Badge variant="outline" className="text-xs whitespace-nowrap">
                    {formatFileSize(refDocTotalSize)} used
                  </Badge>
                </div>
              </div>
              <CardDescription>
                Upload brand documents (PDF, PPT, Word, CSV, Excel) and text notes to enhance AI content generation with brand-specific context.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Upload Section */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <input
                    type="file"
                    accept=".pdf,.ppt,.pptx,.doc,.docx,.csv,.xls,.xlsx"
                    onChange={handleReferenceFileUpload}
                    className="hidden"
                    id="ref-file-upload"
                    disabled={isUploadingRefDoc || refDocTotalFiles >= refDocMaxFiles}
                  />
                  <label
                    htmlFor="ref-file-upload"
                    className={`flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-border rounded-lg cursor-pointer hover:border-primary/50 hover:bg-muted/30 transition-colors ${
                      isUploadingRefDoc || refDocTotalFiles >= refDocMaxFiles ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {isUploadingRefDoc ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        <span className="text-sm">Uploading & extracting text...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="h-5 w-5 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          Upload File (PDF, PPT, Word, CSV, Excel — max 25 MB)
                        </span>
                      </>
                    )}
                  </label>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowAddTextNoteDialog(true)}
                  disabled={refDocTotalFiles >= refDocMaxFiles}
                  className="gap-2"
                >
                  <MessageSquare className="h-4 w-4" />
                  Add Text Note
                </Button>
              </div>

              {/* Info Banner */}
              <div className="bg-muted/30 border border-border rounded-lg p-3 text-sm text-muted-foreground">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <span>
                    Both uploaded documents and brand links are automatically analyzed during content generation. When your article topic matches content in these references, the AI will use brand-specific terminology, facts, and context to produce more accurate content.
                  </span>
                </div>
              </div>

              {/* Documents List */}
              {isLoadingRefDocs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mr-2" />
                  <span>Loading reference documents...</span>
                </div>
              ) : referenceDocuments.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
                  <p className="text-lg font-medium">No reference documents yet</p>
                  <p className="text-sm mt-1">Upload brand guides, previous content, or templates to enhance AI-generated content.</p>
                </div>
              ) : (
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Type</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead className="hidden md:table-cell">Description</TableHead>
                        <TableHead className="w-24 text-right">Size</TableHead>
                        <TableHead className="w-36 hidden sm:table-cell">Uploaded</TableHead>
                        <TableHead className="w-28 text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {referenceDocuments.map((doc: any) => (
                        <TableRow key={doc.id}>
                          <TableCell>
                            <div className="flex items-center justify-center">
                              {getFileTypeIcon(doc.file_type)}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="font-medium text-sm">{doc.file_name}</div>
                            <div className="text-xs text-muted-foreground uppercase">{doc.file_type}</div>
                          </TableCell>
                          <TableCell className="hidden md:table-cell">
                            <span className="text-sm text-muted-foreground line-clamp-1">
                              {doc.description || (doc.file_type === 'text' ? doc.extracted_text?.substring(0, 80) + '...' : '—')}
                            </span>
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {doc.file_size > 0 ? formatFileSize(doc.file_size) : '—'}
                          </TableCell>
                          <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                            {new Date(doc.created_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleViewDocumentContent(doc)}
                                className="h-8 w-8"
                                title="View extracted content"
                              >
                                <Eye className="h-4 w-4 text-muted-foreground" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => handleDeleteReferenceDoc(doc.id)}
                                disabled={isDeletingRefDoc}
                                className="h-8 w-8"
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {!isTeamMember && (
          <TabsContent value="client-access" className="space-y-4 mt-6">
            {domainId && <DomainClientAccess domainId={parseInt(domainId)} />}
          </TabsContent>
        )}
      </Tabs>

      {/* Add Text Note Dialog */}
      <Dialog open={showAddTextNoteDialog} onOpenChange={setShowAddTextNoteDialog}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle>Add Text Note</DialogTitle>
            <DialogDescription>
              Add prompts, templates, or brand notes that will be used as context during content generation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="text-note-title">Title</Label>
              <Input
                id="text-note-title"
                value={textNoteTitle}
                onChange={(e) => setTextNoteTitle(e.target.value)}
                placeholder="e.g., Brand Voice Guidelines, ChatGPT Prompt Template..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="text-note-content">Content *</Label>
              <Textarea
                id="text-note-content"
                value={textNoteContent}
                onChange={(e) => setTextNoteContent(e.target.value)}
                placeholder="Paste your prompts, templates, brand notes, or any text content here..."
                className="min-h-[200px]"
              />
              <p className="text-xs text-muted-foreground">{textNoteContent.length}/50,000 characters</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="text-note-desc">Description (optional)</Label>
              <Input
                id="text-note-desc"
                value={textNoteDescription}
                onChange={(e) => setTextNoteDescription(e.target.value)}
                placeholder="Brief description of what this note contains..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddTextNoteDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddTextNote} disabled={isSavingTextNote || !textNoteContent.trim()}>
              {isSavingTextNote ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Note
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Internal Link Dialog */}
      <Dialog open={showAddLinkDialog} onOpenChange={setShowAddLinkDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Internal Link</DialogTitle>
            <DialogDescription>
              Add a new internal link mapping for content generation
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="link-topic">Topic</Label>
              <Input
                id="link-topic"
                value={newLinkTopic}
                onChange={(e) => setNewLinkTopic(e.target.value)}
                placeholder="e.g., SEO Best Practices"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="link-keywords">Keywords</Label>
              <Textarea
                id="link-keywords"
                value={newLinkKeywords}
                onChange={(e) => setNewLinkKeywords(e.target.value)}
                placeholder="e.g., seo, search engine optimization, ranking"
                className="min-h-[80px]"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated keywords that should trigger this link
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="link-url">Associated URL</Label>
              <Input
                id="link-url"
                value={newLinkUrl}
                onChange={(e) => setNewLinkUrl(e.target.value)}
                placeholder="https://example.com/seo-guide"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddLinkDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddInternalLink} disabled={isSavingLink}>
              {isSavingLink ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                "Add Link"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Internal Link Dialog */}
      <Dialog open={showEditLinkDialog} onOpenChange={(open) => {
        setShowEditLinkDialog(open);
        if (!open) {
          setEditingLink(null);
          setNewLinkTopic("");
          setNewLinkKeywords("");
          setNewLinkUrl("");
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Internal Link</DialogTitle>
            <DialogDescription>
              Update the internal link mapping
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-link-topic">Topic</Label>
              <Input
                id="edit-link-topic"
                value={newLinkTopic}
                onChange={(e) => setNewLinkTopic(e.target.value)}
                placeholder="e.g., SEO Best Practices"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-link-keywords">Keywords</Label>
              <Textarea
                id="edit-link-keywords"
                value={newLinkKeywords}
                onChange={(e) => setNewLinkKeywords(e.target.value)}
                placeholder="e.g., seo, search engine optimization, ranking"
                className="min-h-[80px]"
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated keywords that should trigger this link
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-link-url">Associated URL</Label>
              <Input
                id="edit-link-url"
                value={newLinkUrl}
                onChange={(e) => setNewLinkUrl(e.target.value)}
                placeholder="https://example.com/seo-guide"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditLinkDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateInternalLink} disabled={isSavingLink}>
              {isSavingLink ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update Link"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import CSV Dialog */}
      <Dialog open={showImportDialog} onOpenChange={(open) => {
        setShowImportDialog(open);
        if (!open) {
          setCsvImportText("");
          setCsvFileName("");
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Internal Links from CSV</DialogTitle>
            <DialogDescription>
              Upload a CSV file with your internal link mappings
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="bg-muted/50 rounded-lg p-4 border">
              <p className="text-sm font-medium mb-2">Expected CSV columns:</p>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                  <span className="text-sm">Topic</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                  <span className="text-sm">Keywords</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                  <span className="text-sm">Target</span>
                </div>
              </div>
            </div>
            <div className="flex flex-col items-center gap-3 py-4">
              <input
                type="file"
                accept=".csv"
                onChange={handleCSVFileUpload}
                className="hidden"
                id="csv-file-upload"
              />
              {csvFileName ? (
                <div className="w-full p-3 border rounded-lg bg-muted/30 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" />
                    <span className="text-sm font-medium">{csvFileName}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => document.getElementById('csv-file-upload')?.click()}
                  >
                    Change
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => document.getElementById('csv-file-upload')?.click()}
                  className="w-full"
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Choose CSV File
                </Button>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImportDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleImportCSV} disabled={isImporting || !csvImportText.trim()}>
              {isImporting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                "Import"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Property/Site Selection Dialog */}
      <Dialog open={showPropertySelection} onOpenChange={setShowPropertySelection}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedIntegration?.type === 'google_analytics' 
                ? 'Select Google Analytics Property' 
                : 'Select Google Search Console Site'}
            </DialogTitle>
            <DialogDescription>
              {selectedIntegration?.type === 'google_analytics'
                ? `Choose which Google Analytics property to connect for ${domain?.name}`
                : `Choose which Google Search Console site to connect for ${domain?.name}`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {isLoadingProperties ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">
                  Loading {selectedIntegration?.type === 'google_analytics' ? 'properties' : 'sites'}...
                </span>
              </div>
            ) : (selectedIntegration?.type === 'google_analytics' ? properties.length === 0 : sites.length === 0) ? (
              <div className="text-center py-8">
                <p className="text-sm text-muted-foreground">
                  No {selectedIntegration?.type === 'google_analytics' ? 'properties' : 'sites'} found.
                </p>
              </div>
            ) : selectedIntegration?.type === 'google_analytics' ? (
              <div className="space-y-2">
                <Label htmlFor="property-select">Property</Label>
                <Select value={selectedPropertyId} onValueChange={setSelectedPropertyId}>
                  <SelectTrigger id="property-select">
                    <SelectValue placeholder="Select a property..." />
                  </SelectTrigger>
                  <SelectContent>
                    {properties.map((property: any) => (
                      <SelectItem key={property.id} value={property.id}>
                        <span className="font-medium">{property.display_name || property.id}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedPropertyId && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Selected: {properties.find((p: any) => p.id === selectedPropertyId)?.display_name || selectedPropertyId}
                  </p>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="site-select">Site</Label>
                <Select value={selectedSiteId} onValueChange={setSelectedSiteId}>
                  <SelectTrigger id="site-select">
                    <SelectValue placeholder="Select a site..." />
                  </SelectTrigger>
                  <SelectContent>
                    {sites.map((site: any) => (
                      <SelectItem key={site.id} value={site.id}>
                        <span className="font-medium">{site.display_name || site.id}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedSiteId && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Selected: {sites.find((s: any) => s.id === selectedSiteId)?.display_name || selectedSiteId}
                  </p>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowPropertySelection(false);
                setSelectedPropertyId("");
                setSelectedSiteId("");
                setProperties([]);
                setSites([]);
                setSelectedIntegration(null);
              }}
              disabled={isSelectingProperty}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSelectProperty}
              disabled={
                (selectedIntegration?.type === 'google_analytics' ? !selectedPropertyId : !selectedSiteId) || 
                isSelectingProperty || 
                isLoadingProperties
              }
            >
              {isSelectingProperty ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                `Connect ${selectedIntegration?.type === 'google_analytics' ? 'Property' : 'Site'}`
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Brand Link Dialog */}
      <Dialog open={showAddBrandLinkDialog} onOpenChange={setShowAddBrandLinkDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add Brand Link</DialogTitle>
            <DialogDescription>
              Add a social media profile, microsite, blog, or other digital asset URL. The content will be crawled and used for AI content generation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="brand-link-platform">Platform *</Label>
              <Select value={brandLinkPlatform} onValueChange={setBrandLinkPlatform}>
                <SelectTrigger>
                  <SelectValue placeholder="Select platform..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="facebook">Facebook</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                  <SelectItem value="twitter">Twitter / X</SelectItem>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="linkedin">LinkedIn</SelectItem>
                  <SelectItem value="microsite">Microsite</SelectItem>
                  <SelectItem value="blog">Blog</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="brand-link-url">URL *</Label>
              <Input
                id="brand-link-url"
                value={brandLinkUrl}
                onChange={(e) => setBrandLinkUrl(e.target.value)}
                placeholder="https://www.facebook.com/yourbrand"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="brand-link-label">Label (optional)</Label>
              <Input
                id="brand-link-label"
                value={brandLinkLabel}
                onChange={(e) => setBrandLinkLabel(e.target.value)}
                placeholder="e.g., Main Facebook Page, Product Blog..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddBrandLinkDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddBrandLink} disabled={isSavingBrandLink || !brandLinkUrl.trim() || !brandLinkPlatform}>
              {isSavingBrandLink ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Link
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Content Viewer Dialog */}
      <Dialog open={showContentViewer} onOpenChange={setShowContentViewer}>
        <DialogContent className="w-[95vw] sm:max-w-[700px] max-h-[85vh] overflow-hidden flex flex-col">
          <DialogHeader className="min-w-0">
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5 flex-shrink-0" />
              Extracted Content
            </DialogTitle>
            <DialogDescription className="truncate min-w-0">
              {contentViewerTitle}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2 min-w-0 flex-1 overflow-hidden">
            {isLoadingContent ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                <span>Loading content...</span>
              </div>
            ) : (
              <div className="border rounded-lg bg-muted/20 p-4 max-h-[55vh] overflow-y-auto overflow-x-hidden">
                <pre className="whitespace-pre-wrap break-words text-sm font-mono leading-relaxed max-w-full">
                  {contentViewerText || 'No content available.'}
                </pre>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowContentViewer(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
