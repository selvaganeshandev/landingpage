import { Link, useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Search,
  MessageSquare,
  TrendingUp,
  BarChart3,
  Target,
  Link2,
  LineChart,
  Globe,
  Bell,
  Users,
  User,
  FileText,
  Brain,
  Sparkles,
  AlertTriangle,
  Network,
  Settings,
  ChevronDown,
  ChevronRight,
  Activity,
  Lightbulb,
  Zap,
  LogOut,
  Calendar,
  ChevronsLeft,
  ChevronsRight,
  Check,
  Eye,
  EyeOff,
  Trash2,
} from "lucide-react";
import { DomainSelector } from "./DomainSelector";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { useNavigationStore } from "@/stores/navigationStore";
import { useDomainStore } from "@/stores/domainStore";
import { MODULES } from "@/types/auth";
import { useSidebar } from "@/contexts/SidebarContext";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";

// Icons are passed as components from the navigation store; fall back to LayoutDashboard when missing

const NavGroup = ({ group, location, isSidebarOpen, onItemClick, navigate, isDomainProcessing }: { group: any; location: any; isSidebarOpen: boolean; onItemClick: () => void; navigate: any; isDomainProcessing?: boolean }) => {
  const [submenuOpen, setSubmenuOpen] = useState(false);
  const [recentsVisible, setRecentsVisible] = useState(true);

  // Check if any item in group is active
  const hasActiveItem = group.items.some((item: any) => location.pathname === item.path);

  // Special handling for scrollable recent chats
  if (group.scrollable && isSidebarOpen) {
    return (
      <div className="flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 mt-2">
          <p className="text-xs font-semibold text-muted-foreground">{group.name}</p>
          <button
            onClick={() => setRecentsVisible(!recentsVisible)}
            className="text-muted-foreground hover:text-foreground"
          >
            {recentsVisible ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          </button>
        </div>
        <div
          className={cn(
            "overflow-hidden transition-all duration-300 ease-in-out",
            recentsVisible ? "max-h-[300px] opacity-100" : "max-h-0 opacity-0"
          )}
        >
          <div className="overflow-y-auto space-y-0.5" style={{ maxHeight: '300px' }}>
          {group.items.map((item: any, idx: number) => {
            const isActive = location.pathname === item.path;

            return (
              <div
                key={idx}
                className={cn(
                  "recent-chat-item group w-full flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg hover:bg-accent",
                  isActive && "text-primary"
                )}
              >
                <button
                  type="button"
                  onClick={() => {
                    navigate(item.path);
                    onItemClick();
                  }}
                  className="flex-1 text-left truncate"
                >
                  <span className="truncate">{item.name}</span>
                </button>
                {item.conversationId && (
                  <button
                    type="button"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const { api } = await import('@/services/api');
                        await api.deleteChatConversation(item.conversationId);
                        // Refresh recent conversations
                        const { useNavigationStore } = await import('@/stores/navigationStore');
                        const { updateRecentChats } = useNavigationStore.getState();
                        const response = await api.getChatConversations();
                        if (response.conversations) {
                          const sorted = [...response.conversations].sort((a: any, b: any) =>
                            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
                          );
                          updateRecentChats(sorted.slice(0, 20));
                        }
                        // Navigate to new chat if deleting current conversation
                        const urlParams = new URLSearchParams(window.location.search);
                        if (urlParams.get('conversation') === String(item.conversationId)) {
                          navigate('/chat');
                        }
                      } catch (error) {
                        console.error('Failed to delete conversation:', error);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/10 rounded"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
        </div>
      </div>
    );
  }

  // Don't show scrollable groups in closed state
  if (group.scrollable && !isSidebarOpen) {
    return null;
  }

  // If group has only one item, render it directly
  if (group.items.length === 1) {
    const item = group.items[0];
    const Icon = (item.icon as any) || LayoutDashboard;
    // Check if active - for chat routes, match both / and /chat
    const isActive = item.path === '/chat'
      ? (location.pathname === '/' || location.pathname === '/chat')
      : location.pathname === item.path;

    // Disable navigation when domain is processing (except for settings and chat)
    const isDisabled = isDomainProcessing && !['/chat', '/', '/organization-settings'].includes(item.path);

    const linkContent = isDisabled ? (
      <div
        className={cn(
          "flex items-center opacity-50 cursor-not-allowed",
          "text-muted-foreground",
          isSidebarOpen
            ? "gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
            : "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
        )}
      >
        <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
        {isSidebarOpen && <span>{item.name}</span>}
      </div>
    ) : (
      <Link
        to={item.path}
        onClick={onItemClick}
        className={cn(
          "flex items-center",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          isSidebarOpen
            ? "gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
            : "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
        )}
      >
        <Icon className={cn("h-5 w-5 flex-shrink-0", isActive ? "text-primary-foreground" : "text-muted-foreground")} />
        {isSidebarOpen && <span>{item.name}</span>}
      </Link>
    );

    if (!isSidebarOpen) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            {linkContent}
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>{item.name}</p>
          </TooltipContent>
        </Tooltip>
      );
    }

    return linkContent;
  }

  const GroupIcon = (group.icon as any) || LayoutDashboard;

  // Always use popover for submenus (both open and closed states)
  const popoverContent = (
    <Popover open={submenuOpen} onOpenChange={setSubmenuOpen}>
      <PopoverTrigger asChild>
        {isSidebarOpen ? (
          <button
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium",
              hasActiveItem
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <GroupIcon className={cn("h-5 w-5 flex-shrink-0", hasActiveItem ? "text-primary-foreground" : "text-foreground")} />
            <span className="flex-1 text-left">{group.name}</span>
            <ChevronRight className="h-4 w-4 flex-shrink-0" />
          </button>
        ) : (
          <button
            className={cn(
              "flex items-center justify-center rounded-md aspect-square w-10 h-10 p-0 mx-auto",
              hasActiveItem
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <GroupIcon className="h-5 w-5 flex-shrink-0" />
          </button>
        )}
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-2" side="right" align="start">
        <div className="space-y-1">
          <p className="text-xs font-semibold text-muted-foreground px-2 py-1">{group.name}</p>
          {group.items.map((item: any) => {
            const Icon = (item.icon as any) || LayoutDashboard;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => {
                  onItemClick();
                  setSubmenuOpen(false);
                }}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className={cn("h-5 w-5", isActive ? "text-primary-foreground" : "text-muted-foreground")} />
                {item.name}
              </Link>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );

  if (!isSidebarOpen) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div>
            {popoverContent}
          </div>
        </TooltipTrigger>
        <TooltipContent side="right">
          <p>{group.name}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return popoverContent;
};

export const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Safely get auth context - handle case when not available
  let user, logout, checkPermission;
  try {
    const auth = useAuth();
    user = auth.user;
    logout = auth.logout;
    checkPermission = auth.checkPermission;
  } catch (error) {
    // Auth context not available yet - return null or loading state
    return null;
  }
  const { toast } = useToast();
  const { filteredNavGroups, filterByPermissions } = useNavigationStore();
  const { isOpen, toggleSidebar } = useSidebar();
  const { selectedDomain, domains, setSelectedDomain, setDomainSwitching } = useDomainStore();
  const [domainPopoverOpen, setDomainPopoverOpen] = useState(false);
  const [logoutDialogOpen, setLogoutDialogOpen] = useState(false);

  // Check if domain is currently processing
  const domainProcessingStatus = selectedDomain?.processing_status || null;
  const isDomainProcessing = Boolean(selectedDomain && domainProcessingStatus && ['INIT', 'SCHD', 'PROC'].includes(domainProcessingStatus));

  // Filter navigation based on user permissions
  useEffect(() => {
    if (user && checkPermission) {
      filterByPermissions(checkPermission);
    }
  }, [user, checkPermission, filterByPermissions]);

  const handleItemClick = () => {
    // Close any open popovers when clicking on items
  };

  const handleLogoutClick = () => {
    setLogoutDialogOpen(true);
  };

  const confirmLogout = async () => {
    try {
      await logout();
      toast({
        title: "Signed out",
        description: "You have been successfully signed out.",
      });
      navigate("/signin");
    } catch (error) {
      toast({
        title: "Logout failed",
        description: "There was an error signing you out. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLogoutDialogOpen(false);
    }
  };

  return (
    <TooltipProvider>
      <aside className={cn(
        "bg-card border-r border-border h-screen sticky top-0 overflow-y-auto flex flex-col transition-all duration-150",
        isOpen ? "w-64" : "w-16"
      )}>
        <div className={cn("border-b border-border transition-all duration-150", isOpen ? "px-4 pt-4 pb-3" : "px-3 py-4")}>
          <div className="flex items-center justify-between">
          {isOpen ? (
            <>
              <div>
                <img
                  src="/logo.png"
                  alt="PromptMaxx"
                  className="h-8"
                />
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8"
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-4 w-full">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8"
              >
                <ChevronsRight className="h-5 w-5" />
              </Button>
              {selectedDomain && getFaviconUrl(selectedDomain.url, 32) && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Popover open={domainPopoverOpen} onOpenChange={setDomainPopoverOpen}>
                        <PopoverTrigger asChild>
                          <button className="relative rounded-md overflow-hidden shadow-sm bg-background hover:ring-2 hover:ring-primary/50 transition-all" style={{ width: '36px', height: '36px' }}>
                            <img
                              src={getFaviconUrl(selectedDomain.url, 32) || ''}
                              alt={selectedDomain.name}
                              className={cn("w-full h-full object-cover", isDomainProcessing && "opacity-60")}
                              onError={(e) => handleFaviconError(e, selectedDomain.url, selectedDomain.name, 32)}
                            />
                            {isDomainProcessing && (
                              <div className="absolute inset-0 flex items-center justify-center bg-background/30">
                                <Activity className="h-4 w-4 text-orange-500 animate-pulse" />
                              </div>
                            )}
                          </button>
                        </PopoverTrigger>
                  <PopoverContent className="w-[240px] p-0" side="right" align="start">
                    <Command>
                      <CommandInput placeholder="Search domains..." />
                      <CommandList>
                        <CommandEmpty>No domains found.</CommandEmpty>
                        <CommandGroup heading="Your Domains">
                          {domains.map((domain) => {
                            const faviconUrl = getFaviconUrl(domain.url, 32);
                            const isProcessing = domain.processing_status && ['INIT', 'SCHD', 'PROC'].includes(domain.processing_status);
                            const isFailed = domain.processing_status === 'FAIL';
                            const isDisabled = isProcessing || isFailed;
                            const processingLabel = domain.processing_status === 'INIT' ? 'Initializing...' :
                                                   domain.processing_status === 'SCHD' ? 'Scheduled...' :
                                                   domain.processing_status === 'PROC' ? 'Processing...' : 'Processing...';

                            return (
                              <CommandItem
                                key={domain.id}
                                value={domain.name}
                                onSelect={async () => {
                                  // Don't allow selecting processing or failed domains
                                  if (isDisabled) {
                                    toast({
                                      title: isFailed ? "Domain Processing Failed" : "Domain Processing",
                                      description: isFailed
                                        ? `Processing failed: ${domain.track_message || 'Unknown error'}. Please try re-adding this domain.`
                                        : "This domain is still being processed. Please wait until processing completes.",
                                      variant: isFailed ? "destructive" : "default",
                                    });
                                    return;
                                  }

                                  setDomainSwitching(true);
                                  setSelectedDomain(domain);
                                  setDomainPopoverOpen(false);
                                  if (user) {
                                    // Use updateActiveDomain to sync both systems properly
                                    const { updateActiveDomain } = await import('@/utils/activeDomain');
                                    await updateActiveDomain(user.id, domain.id, domain);
                                  }
                                  // Hide page loader after data has had time to load
                                  setTimeout(() => {
                                    setDomainSwitching(false);
                                  }, 1000);
                                }}
                                className={cn(
                                  "flex items-center justify-between gap-2",
                                  isDisabled && "opacity-60 cursor-not-allowed"
                                )}
                                disabled={isDisabled}
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  {faviconUrl ? (
                                    <img
                                      src={faviconUrl}
                                      alt=""
                                      className="h-4 w-4 flex-shrink-0 rounded"
                                      onError={(e) => handleFaviconError(e, domain.url, domain.name, 32)}
                                    />
                                  ) : null}
                                  <Globe className={cn("h-4 w-4 flex-shrink-0", faviconUrl && "hidden")} />
                                  <div className="flex flex-col flex-1 min-w-0">
                                    <span className="truncate">{domain.name}</span>
                                    {isProcessing ? (
                                      <span className="text-xs text-orange-500 flex items-center gap-1">
                                        <Activity className="h-3 w-3 animate-pulse" />
                                        {processingLabel}
                                      </span>
                                    ) : isFailed ? (
                                      <span className="text-xs text-red-500 flex items-center gap-1">
                                        <AlertTriangle className="h-3 w-3" />
                                        Failed
                                      </span>
                                    ) : (
                                      <span className="text-xs text-muted-foreground">
                                        {domain.total_mentions} mentions
                                      </span>
                                    )}
                                  </div>
                                </div>
                                {isProcessing ? (
                                  <AlertTriangle className="h-4 w-4 flex-shrink-0 text-orange-500" />
                                ) : isFailed ? (
                                  <AlertTriangle className="h-4 w-4 flex-shrink-0 text-red-500" />
                                ) : (
                                  <Check
                                    className={cn(
                                      "h-4 w-4 flex-shrink-0",
                                      selectedDomain?.id === domain.id ? "opacity-100" : "opacity-0"
                                    )}
                                  />
                                )}
                              </CommandItem>
                            );
                          })}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right">
              {isDomainProcessing ? (
                <div className="flex items-center gap-2">
                  <Activity className="h-3 w-3 text-orange-500 animate-pulse" />
                  <span>
                    {domainProcessingStatus === 'INIT' ? 'Initializing...' :
                     domainProcessingStatus === 'SCHD' ? 'Scheduled...' :
                     domainProcessingStatus === 'PROC' ? 'Processing...' : 'Processing...'}
                  </span>
                </div>
              ) : (
                <p>{selectedDomain.name}</p>
              )}
            </TooltipContent>
          </Tooltip>
              )}
            </div>
          )}
        </div>
        {isOpen && (
          <div className="mt-4">
            <DomainSelector />
          </div>
        )}
      </div>

      <nav className={cn("space-y-1 flex-1", isOpen ? "p-4" : "px-3 py-4")}>
          {filteredNavGroups.map((group, index) => (
            <div key={index}>
              {group.separator && isOpen && <Separator className="mt-4 mb-0" />}
              <NavGroup
                group={group}
                location={location}
                isSidebarOpen={isOpen}
                onItemClick={handleItemClick}
                navigate={navigate}
                isDomainProcessing={isDomainProcessing}
              />
            </div>
          ))}
      </nav>

      <div className={cn("border-t border-border mt-auto space-y-1 pt-0", isOpen ? "px-4 pb-4" : "px-3 pb-4")}>
          {/* Organization / Profile shortcuts */}
          {user && (
            <div className="space-y-1 mt-4">
              {(user.role === 'admin' || user.role === 'super_admin') && (
                !isOpen ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link
                        to="/organization-settings"
                        className={cn(
                          "flex items-center",
                          location.pathname === "/organization-settings"
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                          "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
                        )}
                      >
                        <Settings className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/organization-settings" ? "text-primary-foreground" : "text-muted-foreground")} />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>Organization</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link
                    to="/organization-settings"
                    className={cn(
                      "flex items-center",
                      location.pathname === "/organization-settings"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      "gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
                    )}
                  >
                    <Settings className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/organization-settings" ? "text-primary-foreground" : "text-muted-foreground")} />
                    <span>Organization</span>
                  </Link>
                )
              )}
              {user.role === 'admin' && (
                !isOpen ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link
                        to="/profile"
                        className={cn(
                          "flex items-center",
                          location.pathname === "/profile"
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                          "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
                        )}
                      >
                        <User className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>Profile</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link
                    to="/profile"
                    className={cn(
                      "flex items-center",
                      location.pathname === "/profile"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      "gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
                    )}
                  >
                    <User className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                    <span>Profile</span>
                  </Link>
                )
              )}
              {user.role === 'user' && (
                !isOpen ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link
                        to="/profile"
                        className={cn(
                          "flex items-center",
                          location.pathname === "/profile"
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                          "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
                        )}
                      >
                        <User className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>Profile</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <Link
                    to="/profile"
                    className={cn(
                      "flex items-center",
                      location.pathname === "/profile"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      "gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
                    )}
                  >
                    <User className={cn("h-5 w-5 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                    <span>Profile</span>
                  </Link>
                )
              )}
            </div>
          )}

          {!isOpen ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleLogoutClick}
                  className={cn(
                    "flex items-center text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    "rounded-md justify-center aspect-square w-10 h-10 p-0 mx-auto"
                  )}
                >
                  <LogOut className="h-5 w-5 flex-shrink-0" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Sign Out</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <button
              onClick={handleLogoutClick}
              className={cn(
                "flex items-center text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                "w-full gap-3 px-3 py-2.5 text-sm font-medium rounded-lg"
              )}
            >
              <LogOut className="h-5 w-5 flex-shrink-0" />
              <span>Sign Out</span>
            </button>
          )}
      </div>
    </aside>

    {/* Sign Out Confirmation Dialog */}
    <ConfirmDialog
      open={logoutDialogOpen}
      onOpenChange={setLogoutDialogOpen}
      title="Sign Out"
      description="Are you sure you want to sign out? You will need to sign in again to access your account."
      confirmText="Sign Out"
      onConfirm={confirmLogout}
    />
    </TooltipProvider>
  );
};
