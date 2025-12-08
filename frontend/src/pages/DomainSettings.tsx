import { useState, useEffect } from "react";
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
  X,
  Upload,
  FileText,
  Palette,
  Link2,
  Info,
  Activity,
  CheckCircle2,
  AlertCircle,
  XCircle,
} from "lucide-react";
import { PageLoader } from "@/components/PageLoader";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

export default function DomainSettings() {
  const { domainId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();

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
  const [isSavingBrandIdentity, setIsSavingBrandIdentity] = useState(false);

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

  // Keywords state for Add Keywords dialog
  const [newKeywordsInput, setNewKeywordsInput] = useState("");
  const [newKeywordsList, setNewKeywordsList] = useState<string[]>([]);
  const [isAddingKeywords, setIsAddingKeywords] = useState(false);
  const [showAddKeywords, setShowAddKeywords] = useState(false);

  // Health check state
  const [healthData, setHealthData] = useState<any>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthHistory, setHealthHistory] = useState<any>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const MAX_KEYWORD_LENGTH = 255;

  const initialTab = searchParams.get("tab") || "basic-info";
  const [activeTab, setActiveTab] = useState(initialTab);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [searchParams, activeTab]);

  // Fetch health data when health tab is active (including on initial load with ?tab=health)
  useEffect(() => {
    if (activeTab === 'health' && domainId && !healthHistory) {
      console.log('Health tab is active, fetching health history');
      fetchHealthHistory();
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
      setShortDescription(foundDomain.short_description || "");
      setDomainName(foundDomain.name || "");
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

  const hasBasicInfoChanged = () => {
    if (!domain) return false;
    return (
      domainName !== domain.name ||
      shortDescription !== (domain.short_description || "")
    );
  };

  const handleSaveGuidelines = async () => {
    if (!domain) return;

    try {
      setIsSavingGuidelines(true);
      await apiClient.updateDomain(domain.id, {
        tone_of_voice: toneOfVoice.trim() || null,
        content_style: contentStyle.trim() || null,
        key_messages: keyMessages.trim() || null,
        topics_to_avoid: topicsToAvoid.trim() || null,
      });

      setDomain({
        ...domain,
        tone_of_voice: toneOfVoice.trim() || null,
        content_style: contentStyle.trim() || null,
        key_messages: keyMessages.trim() || null,
        topics_to_avoid: topicsToAvoid.trim() || null,
      });

      toast({
        title: "Guidelines saved",
        description: "Content guidelines have been updated successfully.",
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

  const handleSaveBrandIdentity = async () => {
    if (!domain) return;

    try {
      setIsSavingBrandIdentity(true);
      await apiClient.updateDomain(domain.id, {
        target_audience: targetAudience.trim() || null,
        brand_values: brandValues.trim() || null,
        key_competitors: keyCompetitors.trim() || null,
      });

      setDomain({
        ...domain,
        target_audience: targetAudience.trim() || null,
        brand_values: brandValues.trim() || null,
        key_competitors: keyCompetitors.trim() || null,
      });

      toast({
        title: "Brand identity saved",
        description: "Brand identity has been updated successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Error saving brand identity",
        description: error.message || "Failed to save brand identity.",
        variant: "destructive",
      });
    } finally {
      setIsSavingBrandIdentity(false);
    }
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
      toast({
        title: `${integrationName} Connected`,
        description: `Your ${integrationName} account has been successfully connected.`,
      });
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
        <Button onClick={() => setShowAddKeywords(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Keywords
        </Button>
      </div>

      {/* Add Keywords Modal */}
      <Dialog open={showAddKeywords} onOpenChange={(open) => {
        setShowAddKeywords(open);
        if (!open) {
          setNewKeywordsList([]);
          setNewKeywordsInput("");
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Keywords</DialogTitle>
            <DialogDescription>
              Add additional keywords to track for {domain.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <div
                className="flex flex-wrap gap-2 min-h-[100px] max-h-[300px] overflow-y-auto p-3 border border-input rounded-md bg-background text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
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
                  placeholder={newKeywordsList.length === 0 ? "Enter keywords and press Enter (e.g., seo, digital marketing)" : "Add more keywords..."}
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
              <div className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">
                  Type keywords and press Enter, or upload CSV/XLSX files. Max 100 keywords per upload.
                </p>
                {newKeywordsList.length > 0 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setNewKeywordsList([]);
                      setNewKeywordsInput("");
                    }}
                    className="h-8 text-xs"
                  >
                    Clear all
                  </Button>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddKeywords(false)}>
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
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="bg-muted/50 p-1 border border-border">
          <TabsTrigger value="basic-info" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <Info className="h-4 w-4" />
            Basic Info
          </TabsTrigger>
          <TabsTrigger value="content-guidelines" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <FileText className="h-4 w-4" />
            Content Guidelines
          </TabsTrigger>
          <TabsTrigger value="brand-identity" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <Palette className="h-4 w-4" />
            Brand Identity
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <Link2 className="h-4 w-4" />
            Integrations
          </TabsTrigger>
          <TabsTrigger value="health" className="gap-2 data-[state=active]:gradient-primary data-[state=active]:shadow-md data-[state=active]:shadow-primary/20 data-[state=active]:text-white">
            <Activity className="h-4 w-4" />
            Health
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
                  disabled={isSavingGuidelines || !hasGuidelinesChanged()}
                >
                  {isSavingGuidelines ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Guidelines"
                  )}
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
                Define your brand's identity and market positioning. These values are auto-populated using AI when you create a new brand.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
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
              <div className="flex justify-end">
                <Button
                  onClick={handleSaveBrandIdentity}
                  disabled={isSavingBrandIdentity || !hasBrandIdentityChanged()}
                >
                  {isSavingBrandIdentity ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Save Brand Identity"
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
              <div className={`p-4 border rounded-lg ${isProperlyConnected(getIntegration('google_analytics')) ? 'border-green-500 bg-green-50' : getIntegration('google_analytics')?.status === 'disconnected' ? 'border-red-200 bg-red-50' : ''}`}>
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
              <div className={`p-4 border rounded-lg ${isProperlyConnected(getIntegration('search_console')) ? 'border-green-500 bg-green-50' : getIntegration('search_console')?.status === 'disconnected' ? 'border-red-200 bg-red-50' : ''}`}>
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
        <TabsContent value="health" className="space-y-4 mt-6">
          <Card className="border border-border">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Website Health Check</CardTitle>
                <CardDescription>
                  Technical assessment of your website's AI-friendliness and SEO optimization
                </CardDescription>
              </div>
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

                  {/* Health Checks */}
                  <div className="space-y-4 mt-8">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold">Detailed Health Checks</h3>
                      <span className="text-sm text-muted-foreground">{healthData.checks?.length} total checks</span>
                    </div>
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
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <Badge
                                    variant="outline"
                                    className={`text-xs font-medium ${
                                      check.importance === 'critical' ? 'border-red-500 text-red-700 bg-red-50 dark:bg-red-900/20' :
                                      check.importance === 'high' ? 'border-orange-500 text-orange-700 bg-orange-50 dark:bg-orange-900/20' :
                                      check.importance === 'medium' ? 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-900/20' :
                                      'border-gray-400 text-gray-600 bg-gray-50 dark:bg-gray-900/20'
                                    }`}
                                  >
                                    {check.importance}
                                  </Badge>
                                  <span className={`text-xs font-mono font-semibold px-2 py-1 rounded ${
                                    check.status === 'pass' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                    check.status === 'warning' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  }`}>
                                    {check.score}/{check.max_score}
                                  </span>
                                </div>
                              </div>
                              <p className="text-sm text-muted-foreground leading-relaxed">
                                {check.message}
                              </p>
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
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
      </Tabs>

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
    </div>
  );
}
