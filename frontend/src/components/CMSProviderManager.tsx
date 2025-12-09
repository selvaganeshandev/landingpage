import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
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
import { useDomainStore } from "@/stores/domainStore";
import { Plus, Edit, Trash2, TestTube, Globe } from "lucide-react";

interface CMSProvider {
  id: number;
  domain: number;
  domain_name: string;
  provider_type: string;
  name: string;
  settings: {
    api_url?: string;
    username?: string;
    app_password?: string;
    site_url?: string;
    content_type?: string;
    token?: string;
    collection?: string;
    endpoint?: string;
    catid?: number | string;
    state?: number | string;
    password?: string;
    body_format?: string;
    status?: number | string;
    management_token?: string;
    space_id?: string;
    environment_id?: string;
    content_type_id?: string;
  };
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  modified_at: string;
}

const CMSProviderManager = () => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();
  const [providers, setProviders] = useState<CMSProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<CMSProvider | null>(null);
  const [testingProviderId, setTestingProviderId] = useState<number | null>(null);

  const [formData, setFormData] = useState({
    provider_type: "wordpress",
    name: "",
    api_url: "",
    username: "",
    app_password: "",
    site_url: "",
    content_type: "pages", // wordpress
    token: "", // strapi/joomla
    collection: "/api/articles", // strapi
    endpoint: "/api/index.php/v1/content/articles", // joomla
    catid: "",
    state: "1",
    password: "", // drupal
    body_format: "basic_html", // drupal
    status: "1", // drupal
    management_token: "", // contentful
    space_id: "",
    environment_id: "master",
    content_type_id: "",
    is_active: true,
    is_default: false,
  });

  useEffect(() => {
    if (selectedDomain) {
      loadProviders();
    }
  }, [selectedDomain]);

  const loadProviders = async () => {
    if (!selectedDomain) return;

    try {
      setLoading(true);
      const response: any = await apiClient.getCMSProviders({ domain_id: selectedDomain.id });
      if (response.status === "success") {
        setProviders(response.results || []);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to load CMS providers",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (provider?: CMSProvider) => {
    if (provider) {
      setEditingProvider(provider);
      setFormData({
        provider_type: provider.provider_type,
        name: provider.name,
        api_url: provider.settings.api_url || "",
        username: provider.settings.username || "",
        app_password: provider.settings.app_password || "",
        site_url: provider.settings.site_url || "",
        content_type: provider.settings.content_type || "pages",
        token: provider.settings.token || "",
        collection: provider.settings.collection || "/api/articles",
        endpoint: provider.settings.endpoint || "/api/index.php/v1/content/articles",
        catid: provider.settings.catid ? String(provider.settings.catid) : "",
        state: provider.settings.state ? String(provider.settings.state) : "1",
        password: provider.settings.password || "",
        body_format: provider.settings.body_format || "basic_html",
        status: provider.settings.status ? String(provider.settings.status) : "1",
        management_token: provider.settings.management_token || "",
        space_id: provider.settings.space_id || "",
        environment_id: provider.settings.environment_id || "master",
        content_type_id: provider.settings.content_type_id || "",
        is_active: provider.is_active,
        is_default: provider.is_default,
      });
    } else {
      setEditingProvider(null);
      setFormData({
        provider_type: "wordpress",
        name: "",
        api_url: "",
        username: "",
        app_password: "",
        site_url: "",
        content_type: "pages",
        token: "",
        collection: "/api/articles",
        endpoint: "/api/index.php/v1/content/articles",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
        is_active: true,
        is_default: false,
      });
    }
    setDialogOpen(true);
  };

  // When changing provider type, reset provider-specific fields to sensible defaults
  const handleProviderTypeChange = (value: string) => {
    if (value === "wordpress") {
      setFormData((prev) => ({
        ...prev,
        provider_type: "wordpress",
        api_url: "",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "pages",
        token: "",
        collection: "/api/articles",
        endpoint: "/api/index.php/v1/content/articles",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    } else if (value === "strapi") {
      setFormData((prev) => ({
        ...prev,
        provider_type: "strapi",
        api_url: "",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "pages",
        token: "",
        collection: "/api/articles",
        endpoint: "/api/index.php/v1/content/articles",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    } else if (value === "joomla") {
      setFormData((prev) => ({
        ...prev,
        provider_type: "joomla",
        api_url: "",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "pages",
        token: "",
        collection: "/api/articles",
        endpoint: "/api/index.php/v1/content/articles",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    } else if (value === "drupal") {
      setFormData((prev) => ({
        ...prev,
        provider_type: "drupal",
        api_url: "",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "page",
        token: "",
        collection: "/api/articles",
        endpoint: "/entity/node?_format=json",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    } else if (value === "contentful") {
      setFormData((prev) => ({
        ...prev,
        provider_type: "contentful",
        api_url: "https://api.contentful.com",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "page",
        token: "",
        collection: "/api/articles",
        endpoint: "/entity/node?_format=json",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    } else {
      // Generic providers
      setFormData((prev) => ({
        ...prev,
        provider_type: value,
        api_url: "",
        site_url: "",
        username: "",
        app_password: "",
        content_type: "pages",
        token: "",
        collection: "/api/articles",
        endpoint: "/api/index.php/v1/content/articles",
        catid: "",
        state: "1",
        password: "",
        body_format: "basic_html",
        status: "1",
        management_token: "",
        space_id: "",
        environment_id: "master",
        content_type_id: "",
      }));
    }
  };

  const handleSave = async () => {
    if (!selectedDomain) {
      toast({
        title: "Error",
        description: "Please select a domain first",
        variant: "destructive",
      });
      return;
    }

    try {
      // Simple client-side validation
      if (!formData.name.trim()) {
        toast({
          title: "Missing Name",
          description: "Please provide a provider name.",
          variant: "destructive",
        });
        return;
      }
      if (!formData.api_url.trim() || !formData.api_url.startsWith("http")) {
        toast({
          title: "Invalid API URL",
          description: "Please provide a valid API URL (must start with http/https).",
          variant: "destructive",
        });
        return;
      }
      if (formData.provider_type === "wordpress") {
        if (!formData.username.trim() || !formData.app_password.trim()) {
          toast({
            title: "Missing Credentials",
            description: "Username and application password are required for WordPress.",
            variant: "destructive",
          });
          return;
        }
      }
      if (formData.provider_type === "strapi") {
        if (!formData.token.trim()) {
          toast({
            title: "Missing Token",
            description: "Bearer token is required for Strapi.",
            variant: "destructive",
          });
          return;
        }
      }
      if (formData.provider_type === "joomla") {
        if (!formData.token.trim() || !formData.catid.trim()) {
          toast({
            title: "Missing Joomla settings",
            description: "Token and Category ID are required for Joomla.",
            variant: "destructive",
          });
          return;
        }
      }
      if (formData.provider_type === "drupal") {
        if (!formData.username.trim() || !formData.password.trim() || !formData.content_type.trim()) {
          toast({
            title: "Missing Drupal settings",
            description: "Username, password, and content type are required for Drupal.",
            variant: "destructive",
          });
          return;
        }
      }
      if (formData.provider_type === "contentful") {
        if (
          !formData.management_token.trim() ||
          !formData.space_id.trim() ||
          !formData.environment_id.trim() ||
          !formData.content_type_id.trim()
        ) {
          toast({
            title: "Missing Contentful settings",
            description: "Management token, Space ID, Environment ID, and Content Type ID are required for Contentful.",
            variant: "destructive",
          });
          return;
        }
      }
      if (!["wordpress", "strapi"].includes(formData.provider_type)) {
        // Generic providers: API URL required; token optional
      }

      const settings =
        formData.provider_type === "wordpress"
          ? {
              api_url: formData.api_url,
              username: formData.username,
              app_password: formData.app_password,
              site_url: formData.site_url,
              content_type: formData.content_type,
            }
          : formData.provider_type === "strapi"
          ? {
              api_url: formData.api_url,
              token: formData.token,
              collection: formData.collection || "/api/articles",
            }
          : formData.provider_type === "joomla"
          ? {
              api_url: formData.api_url,
              token: formData.token,
              endpoint: formData.endpoint || "/api/index.php/v1/content/articles",
              catid: Number(formData.catid),
              state: Number(formData.state || "1"),
            }
          : formData.provider_type === "drupal"
          ? {
              api_url: formData.api_url,
              username: formData.username,
              password: formData.password,
              endpoint: formData.endpoint || "/entity/node?_format=json",
              content_type: formData.content_type || "page",
              body_format: formData.body_format || "basic_html",
              status: Number(formData.status || "1"),
            }
          : formData.provider_type === "contentful"
          ? {
              api_url: formData.api_url || "https://api.contentful.com",
              management_token: formData.management_token,
              space_id: formData.space_id,
              environment_id: formData.environment_id || "master",
              content_type_id: formData.content_type_id,
            }
          : {
              api_url: formData.api_url,
              token: formData.token,
            };

      if (editingProvider) {
        await apiClient.updateCMSProvider(editingProvider.id, {
          name: formData.name,
          settings,
          is_active: formData.is_active,
          is_default: formData.is_default,
        });
        toast({
          title: "Success",
          description: "CMS provider updated successfully",
        });
      } else {
        await apiClient.createCMSProvider({
          domain: selectedDomain.id,
          provider_type: formData.provider_type,
          name: formData.name,
          settings,
          is_active: formData.is_active,
          is_default: formData.is_default,
        });
        toast({
          title: "Success",
          description: "CMS provider created successfully",
        });
      }

      setDialogOpen(false);
      loadProviders();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to save CMS provider",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (providerId: number) => {
    if (!confirm("Are you sure you want to delete this CMS provider?")) return;

    try {
      await apiClient.deleteCMSProvider(providerId);
      toast({
        title: "Success",
        description: "CMS provider deleted successfully",
      });
      loadProviders();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to delete CMS provider",
        variant: "destructive",
      });
    }
  };

  const handleTestConnection = async (providerId: number) => {
    try {
      setTestingProviderId(providerId);
      const response: any = await apiClient.testCMSProviderConnection(providerId);
      if (response.status === "success") {
        toast({
          title: "Connection Successful",
          description: `Connected to ${response.data?.username || "WordPress"}`,
        });
      }
    } catch (error: any) {
      toast({
        title: "Connection Failed",
        description: error.message || "Failed to connect to CMS provider",
        variant: "destructive",
      });
    } finally {
      setTestingProviderId(null);
    }
  };

  if (!selectedDomain) {
    return (
      <Card className="p-6 border border-border">
        <div className="text-center text-muted-foreground">
          <Globe className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Please select a domain to manage CMS providers</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">CMS Providers</h3>
          <p className="text-sm text-muted-foreground">
            Manage CMS provider configurations for {selectedDomain.name}
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()} className="gradient-primary">
          <Plus className="h-4 w-4 mr-2" />
          Add Provider
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">Loading providers...</div>
      ) : providers.length === 0 ? (
        <Card className="p-8 border border-dashed border-border">
          <div className="text-center text-muted-foreground">
            <Globe className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="mb-4">No CMS providers configured</p>
            <Button onClick={() => handleOpenDialog()} variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Add Your First Provider
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          {providers.map((provider) => (
            <Card key={provider.id} className="p-4 border border-border">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-semibold">{provider.name}</h4>
                    {provider.is_default && (
                      <Badge variant="default" className="text-xs">Default</Badge>
                    )}
                    {!provider.is_active && (
                      <Badge variant="secondary" className="text-xs">Inactive</Badge>
                    )}
                    <Badge variant="outline" className="text-xs capitalize">
                      {provider.provider_type}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Site: {provider.settings.site_url || provider.settings.api_url}</p>
                    <p>Username: {provider.settings.username}</p>
                    <p>Content Type: {provider.settings.content_type || "pages"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleTestConnection(provider.id)}
                    disabled={testingProviderId === provider.id}
                  >
                    {testingProviderId === provider.id ? (
                      <TestTube className="h-4 w-4 animate-spin" />
                    ) : (
                      <TestTube className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenDialog(provider)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(provider.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProvider ? "Edit CMS Provider" : "Add CMS Provider"}
            </DialogTitle>
            <DialogDescription>
              Configure your WordPress site credentials
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <Label>Provider Name *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Main WordPress Site"
              />
            </div>

            <div>
              <Label>Provider Type</Label>
              <Select
                value={formData.provider_type}
                onValueChange={handleProviderTypeChange}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="wordpress">WordPress</SelectItem>
                  <SelectItem value="strapi">Strapi</SelectItem>
                  <SelectItem value="joomla">Joomla</SelectItem>
              <SelectItem value="drupal">Drupal</SelectItem>
                  <SelectItem value="contentful">Contentful</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {formData.provider_type === "wordpress" && (
              <>
                <div>
                  <Label>WordPress Site URL *</Label>
                  <Input
                    value={formData.site_url}
                    onChange={(e) => setFormData({ ...formData, site_url: e.target.value })}
                    placeholder="https://example.com"
                  />
                </div>

                <div>
                  <Label>WordPress API URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://example.com/wp-json/wp/v2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Usually: your-site-url/wp-json/wp/v2
                  </p>
                </div>

                <div>
                  <Label>Username *</Label>
                  <Input
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder="WordPress username"
                  />
                </div>

                <div>
                  <Label>Application Password *</Label>
                  <Input
                    type="password"
                    value={formData.app_password}
                    onChange={(e) => setFormData({ ...formData, app_password: e.target.value })}
                    placeholder="xxxx xxxx xxxx xxxx"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Generate from WordPress: Users → Profile → Application Passwords
                  </p>
                </div>

                <div>
                  <Label>Content Type</Label>
                  <Select
                    value={formData.content_type}
                    onValueChange={(value) => setFormData({ ...formData, content_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pages">Pages</SelectItem>
                      <SelectItem value="posts">Posts</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            {formData.provider_type === "strapi" && (
              <>
                <div>
                  <Label>Strapi API URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://strapi.example.com"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Base URL (no trailing slash), e.g. https://strapi.example.com
                  </p>
                </div>

                <div>
                  <Label>Collection Endpoint</Label>
                  <Input
                    value={formData.collection}
                    onChange={(e) => setFormData({ ...formData, collection: e.target.value })}
                    placeholder="/api/articles"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Endpoint to post to (default: /api/articles); field keys are case-sensitive.
                  </p>
                </div>

                <div>
                  <Label>Bearer Token *</Label>
                  <Input
                    type="password"
                    value={formData.token}
                    onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                    placeholder="Strapi API token"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Create in Strapi Settings → API Tokens; needs create/publish for this collection.
                  </p>
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">Strapi tips</p>
                  <p>• Endpoint: keep /api/articles unless your collection path differs.</p>
                  <p>• Fields: use exact case (e.g. Title, Content in your Articles type).</p>
                  <p>• Token: Settings → API Tokens; grant create/publish for that collection.</p>
                  <p>• Scheduling: we set publishedAt; Strapi will publish at that time.</p>
                  <p>• Errors like “Invalid key …”: fix field names or endpoint to match your model.</p>
                </div>
              </>
            )}

            {formData.provider_type === "joomla" && (
              <>
                <div>
                  <Label>Joomla Site URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://joomla.example.com"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Base URL (no trailing slash), e.g. https://joomla.example.com
                  </p>
                </div>

                <div>
                  <Label>Articles Endpoint</Label>
                  <Input
                    value={formData.endpoint}
                    onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
                    placeholder="/api/index.php/v1/content/articles"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Default: /api/index.php/v1/content/articles (Joomla 4/5 core API)
                  </p>
                </div>

                <div>
                  <Label>Bearer Token *</Label>
                  <Input
                    type="password"
                    value={formData.token}
                    onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                    placeholder="Joomla API token"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Users → Your User → API Token (requires API Authentication - Joomla Token plugin).
                  </p>
                </div>

                <div>
                  <Label>Category ID (catid) *</Label>
                  <Input
                    value={formData.catid}
                    onChange={(e) => setFormData({ ...formData, catid: e.target.value })}
                    placeholder="e.g., 2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Target category id for the article.
                  </p>
                </div>

                <div>
                  <Label>State</Label>
                  <Select
                    value={formData.state}
                    onValueChange={(val) => setFormData({ ...formData, state: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Published</SelectItem>
                      <SelectItem value="0">Unpublished</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-1">
                    1 = Published (default), 0 = Unpublished.
                  </p>
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">Joomla tips</p>
                  <p>• Enable plugins: API Authentication - Joomla Token, Content - Joomla API.</p>
                  <p>• Get token: Users → Your User → API Token.</p>
                  <p>• Endpoint: /api/index.php/v1/content/articles (Joomla 4/5).</p>
                  <p>• Required: catid (category id), token, base site URL.</p>
                  <p>• Frontend visibility: create a menu item (Category Blog/List) pointing to this category so published articles appear.</p>
                  <p>• Scheduling not yet supported; we publish immediately with state.</p>
                </div>
              </>
            )}

            {formData.provider_type === "drupal" && (
              <>
                <div>
                  <Label>Drupal Site URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://drupal.example.com"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Base URL (no trailing slash), e.g. https://drupal.example.com
                  </p>
                </div>

                <div>
                  <Label>Endpoint</Label>
                  <Input
                    value={formData.endpoint}
                    onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
                    placeholder="/entity/node?_format=json"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Default REST: /entity/node?_format=json (Basic Auth or cookie+CSRF). For JSON:API use /jsonapi/node/&lt;type&gt;.
                  </p>
                </div>

                <div>
                  <Label>Username *</Label>
                  <Input
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder="Drupal username"
                  />
                </div>

                <div>
                  <Label>Password *</Label>
                  <Input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="Password for this user"
                  />
                </div>

                <div>
                  <Label>Content Type (machine name) *</Label>
                  <Input
                    value={formData.content_type}
                    onChange={(e) => setFormData({ ...formData, content_type: e.target.value })}
                    placeholder="page, article, etc."
                  />
                </div>

                <div>
                  <Label>Body Format</Label>
                  <Input
                    value={formData.body_format}
                    onChange={(e) => setFormData({ ...formData, body_format: e.target.value })}
                    placeholder="basic_html"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Must be an allowed text format for the user; basic_html is typical.
                  </p>
                </div>

                <div>
                  <Label>Publish Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(val) => setFormData({ ...formData, status: val })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Published</SelectItem>
                      <SelectItem value="0">Unpublished</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">Drupal tips</p>
                  <p>• Enable REST (entity:node POST) or JSON:API; allow Basic Auth or cookie+CSRF.</p>
                  <p>• Required: username/password with permissions to create the chosen content type.</p>
                  <p>• Endpoint defaults to REST /entity/node?_format=json; for JSON:API use /jsonapi/node/&lt;type&gt;.</p>
                  <p>• Fields: title + body (value + format); status controls published/unpublished.</p>
                  <p>• Frontend visibility: add a menu item or view listing for the target content type.</p>
                </div>
              </>
            )}

            {formData.provider_type === "contentful" && (
              <>
                <div>
                  <Label>Contentful API URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://api.contentful.com"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Management API base URL (default: https://api.contentful.com)
                  </p>
                </div>

                <div>
                  <Label>Management Token *</Label>
                  <Input
                    type="password"
                    value={formData.management_token}
                    onChange={(e) => setFormData({ ...formData, management_token: e.target.value })}
                    placeholder="Contentful CMA token"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Create in Contentful: Settings → API keys → Content management tokens
                  </p>
                </div>

                <div>
                  <Label>Space ID *</Label>
                  <Input
                    value={formData.space_id}
                    onChange={(e) => setFormData({ ...formData, space_id: e.target.value })}
                    placeholder="space_id"
                  />
                </div>

                <div>
                  <Label>Environment ID *</Label>
                  <Input
                    value={formData.environment_id}
                    onChange={(e) => setFormData({ ...formData, environment_id: e.target.value })}
                    placeholder="master"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Defaults to master if not set.
                  </p>
                </div>

                <div>
                  <Label>Content Type ID *</Label>
                  <Input
                    value={formData.content_type_id}
                    onChange={(e) => setFormData({ ...formData, content_type_id: e.target.value })}
                    placeholder="e.g., page, blogPost"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    The Content Type ID used when creating entries.
                  </p>
                </div>

                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground">Contentful tips</p>
                  <p>• Token: Settings → API keys → Content management tokens → create CMA token.</p>
                  <p>• Space/Env: Use your Space ID and Environment ID (default master).</p>
                  <p>• Content type: Create/locate the Content Type ID you want to publish into.</p>
                  <p>• Endpoint: POST https://api.contentful.com/spaces/&lt;space_id&gt;/environments/&lt;env_id&gt;/entries with header X-Contentful-Content-Type: &lt;content_type_id&gt;.</p>
                  <p>• Headers: Authorization: Bearer &lt;CMA token&gt;, Content-Type: application/vnd.contentful.management.v1+json.</p>
                  <p>• Body shape: fields.title.en-US, fields.body.en-US (use your locale code if different).</p>
                  <p>• Publish: After create, call CMA publish on the entry (publish step not wired here yet).</p>
                </div>
              </>
            )}

            {!["wordpress", "strapi", "joomla", "drupal", "contentful"].includes(formData.provider_type) && (
              <>
                <div>
                  <Label>API URL *</Label>
                  <Input
                    value={formData.api_url}
                    onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                    placeholder="https://your-cms.example.com/api"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Base API URL for this provider
                  </p>
                </div>
                <div>
                  <Label>Token (optional)</Label>
                  <Input
                    type="password"
                    value={formData.token}
                    onChange={(e) => setFormData({ ...formData, token: e.target.value })}
                    placeholder="API token if required"
                  />
                </div>
              </>
            )}

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_active: checked })
                  }
                />
                <Label>Active</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.is_default}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_default: checked })
                  }
                />
                <Label>Set as Default</Label>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} className="gradient-primary">
              {editingProvider ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CMSProviderManager;

