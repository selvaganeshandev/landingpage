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
  CreditCard,
} from "lucide-react";
import { DomainSelector } from "./DomainSelector";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { useNavigationStore } from "@/stores/navigationStore";
import { useDomainStore } from "@/stores/domainStore";
import { MODULES } from "@/types/auth";
import { useSidebar } from "@/contexts/SidebarContext";
import { apiClient } from "@/services/api";
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

/* ─── Row styling ─────────────────────────────────────────────────────────────
   One definition shared by every sidebar entry — flat links, submenu triggers,
   popover items and the footer — so they cannot drift apart.

   The active state is a soft accent wash plus a thin brand-coloured bar on the
   left edge, rather than a saturated full-width pill. The pill dominated the
   panel, fought with the domain selector above it, and made the icon invert to
   white while every neighbouring icon stayed grey. Idle rows are muted and
   only the label weight changes when active, which keeps the column quiet and
   the eye on the content. */
const ROW_BASE =
  "relative flex items-center gap-2.5 rounded-md text-sm transition-colors";
const ROW_OPEN = "px-2.5 py-1.5 w-full";
const ROW_COLLAPSED = "justify-center aspect-square w-9 h-9 p-0 mx-auto";
const ROW_ACTIVE = "bg-accent text-foreground font-medium";
const ROW_IDLE =
  "text-foreground/75 font-normal hover:bg-accent/60 hover:text-foreground";
// Idle icons sit a step lighter than their label so the row still reads
// label-first, without being as washed out as --muted-foreground was.
const ICON_IDLE = "text-foreground/60";
const ICON_BASE = "h-4 w-4 flex-shrink-0";

const NavGroup = ({ group, location, isSidebarOpen, onItemClick, navigate, isDomainProcessing, popoverAlign = "start" }: { group: any; location: any; isSidebarOpen: boolean; onItemClick: () => void; navigate: any; isDomainProcessing?: boolean; popoverAlign?: "start" | "end" }) => {
  const [submenuOpen, setSubmenuOpen] = useState(false);

  // Check if any item in group is active
  const hasActiveItem = group.items.some((item: any) => location.pathname === item.path);

  // Section label - just render a text header (same style as Recents was)
  if (group.sectionLabel) {
    if (!isSidebarOpen) {
      // Collapsed: no room for the label, so a hairline keeps the grouping.
      return <Separator className="my-1.5" />;
    }
    return (
      <div className="px-2.5 pt-2.5 pb-0.5">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground/55">
          {group.name}
        </p>
      </div>
    );
  }

  // If group has only one item, render it directly
  if (group.items.length === 1) {
    const item = group.items[0];
    const Icon = (item.icon as any) || LayoutDashboard;
    // Check if active - for chat routes, match both / and /chat
    const isActive = item.path === '/chat'
      ? (location.pathname === '/' || location.pathname === '/chat')
      : location.pathname === item.path;

    // Navigation stays enabled while a domain processes — see the note on
    // isDomainProcessing below. Kept as a named constant so the disabled
    // branches below remain in place should a real reason to lock nav appear.
    const isDisabled = false;

    const linkContent = isDisabled ? (
      <div
        className={cn(
          ROW_BASE, "opacity-50 cursor-not-allowed text-muted-foreground",
          isSidebarOpen ? ROW_OPEN : ROW_COLLAPSED
        )}
      >
        <Icon className={cn(ICON_BASE, "text-muted-foreground")} />
        {isSidebarOpen && <span>{item.name}</span>}
      </div>
    ) : (
      <Link
        to={item.path}
        onClick={onItemClick}
        className={cn(
          ROW_BASE,
          isActive ? ROW_ACTIVE : ROW_IDLE,
          isSidebarOpen ? ROW_OPEN : ROW_COLLAPSED
        )}
      >
        <Icon className={cn(ICON_BASE, isActive ? "text-primary" : ICON_IDLE)} />
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
            className={cn(ROW_BASE, ROW_OPEN, hasActiveItem ? ROW_ACTIVE : ROW_IDLE)}
          >
            {/* Was text-foreground — near-black against grey neighbours, which
                made every group header shout. */}
            <GroupIcon className={cn(ICON_BASE, hasActiveItem ? "text-primary" : ICON_IDLE)} />
            <span className="flex-1 text-left">{group.name}</span>
            <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
          </button>
        ) : (
          <button
            className={cn(ROW_BASE, ROW_COLLAPSED, hasActiveItem ? ROW_ACTIVE : ROW_IDLE)}
          >
            <GroupIcon className={cn(ICON_BASE, hasActiveItem ? "text-primary" : ICON_IDLE)} />
          </button>
        )}
      </PopoverTrigger>
      {/* Same rhythm as the nav column: 0.5 row gap, and a heading matching
          the section labels so the flyout reads as a continuation of it. */}
      <PopoverContent className="w-[200px] p-1.5" side="right" align={popoverAlign}>
        <div className="space-y-0.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-foreground/55 px-2.5 pt-1 pb-1">{group.name}</p>
          {group.items.map((item: any) => {
            const Icon = (item.icon as any) || LayoutDashboard;
            const isActive = location.pathname === item.path;
            const isItemDisabled = false;

            if (isItemDisabled) {
              return (
                <div
                  key={item.path}
                  className={cn(ROW_BASE, ROW_OPEN, "opacity-50 cursor-not-allowed text-muted-foreground")}
                >
                  <Icon className={cn(ICON_BASE, "text-muted-foreground")} />
                  {item.name}
                </div>
              );
            }

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => {
                  onItemClick();
                  setSubmenuOpen(false);
                }}
                className={cn(ROW_BASE, ROW_OPEN, isActive ? ROW_ACTIVE : ROW_IDLE)}
              >
                <Icon className={cn(ICON_BASE, isActive ? "text-primary" : ICON_IDLE)} />
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

  // Check if domain is currently processing.
  //
  // This drives the spinner on the domain avatar only. It no longer disables
  // navigation: a processing domain is now selectable, and locking every menu
  // item behind it would hand the user a dead sidebar. Pages carry their own
  // empty states, and Layout shows a ProcessingBanner explaining what is still
  // running.
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
        <div className={cn("border-b border-border transition-all duration-150", isOpen ? "px-3 pt-3 pb-2" : "px-2 py-3")}>
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
          <div className="mt-2.5">
            <DomainSelector />
          </div>
        )}
      </div>

      {/* Tighter rhythm: the section labels already mark the boundaries, so the
          horizontal rules between them were redundant and cost ~16px each. */}
      <nav className={cn("space-y-0.5 flex-1", isOpen ? "px-3 py-1" : "px-2 py-1")}>
          {filteredNavGroups.map((group, index) => (
            <div key={index}>
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

      <div className={cn("border-t border-border mt-auto space-y-0.5 pt-0", isOpen ? "px-3 pb-2" : "px-2 pb-2")}>
          {/* Organization and Profile collapsed into one "Settings" entry —
              two near-identical cog/person rows in the footer read as clutter,
              and both are settings. Rendered through NavGroup so the flyout is
              styled exactly like the ones in the nav above; NavGroup also falls
              back to a flat link automatically when permissions leave only one
              item. isDomainProcessing is passed false deliberately: settings
              must stay reachable while a domain is being processed. */}
          {user && (
            <div className="space-y-0.5 mt-1.5">
              <NavGroup
                group={{
                  name: "Settings",
                  icon: Settings,
                  items: [
                    // Not for clients: their way into a project is the gear on
                    // the project pill at the top of this sidebar, and repeating
                    // it down here made two routes to one page. Profile is left,
                    // so a client's footer is a plain Profile link.
                    ...((user.role === 'admin' || user.role === 'super_admin' || (user.role === 'user' && checkPermission && checkPermission('organization_settings', 'read')))
                      ? [{ name: "Organization", path: "/organization-settings", icon: Settings }]
                      : []),
                    // Super admin only, matching the route guard on /billing.
                    ...(user.role === 'super_admin'
                      ? [{ name: "Billing", path: "/billing", icon: CreditCard }]
                      : []),
                    { name: "Profile", path: "/profile", icon: User },
                  ],
                }}
                location={location}
                isSidebarOpen={isOpen}
                onItemClick={handleItemClick}
                navigate={navigate}
                isDomainProcessing={false}
                popoverAlign="end"
              />
            </div>
          )}

          {!isOpen ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleLogoutClick}
                  className={cn(ROW_BASE, ROW_COLLAPSED, ROW_IDLE)}
                >
                  <LogOut className="h-4 w-4 flex-shrink-0" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>Sign Out</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <button
              onClick={handleLogoutClick}
              className={cn(ROW_BASE, ROW_OPEN, ROW_IDLE)}
            >
              <LogOut className="h-4 w-4 flex-shrink-0" />
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
