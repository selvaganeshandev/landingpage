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

// Icons are passed as components from the navigation store; fall back to LayoutDashboard when missing

const NavGroup = ({ group, location, isOpen, onToggle, isSidebarOpen, onItemClick }: { group: any; location: any; isOpen: boolean; onToggle: () => void; isSidebarOpen: boolean; onItemClick: () => void }) => {
  const [submenuOpen, setSubmenuOpen] = useState(false);

  // Check if any item in group is active
  const hasActiveItem = group.items.some((item: any) => location.pathname === item.path);

  // If group has only one item, render it directly
  if (group.items.length === 1) {
    const item = group.items[0];
    const Icon = (item.icon as any) || LayoutDashboard;
    const isActive = location.pathname === item.path;

    return (
      <Link
        to={item.path}
        onClick={onItemClick}
        className={cn(
          "flex items-center transition-all duration-150",
          isActive
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
          isSidebarOpen
            ? "gap-3 px-3 py-2 text-sm font-medium rounded-lg"
            : "rounded-md justify-center aspect-square w-9 h-9 p-0"
        )}
        style={!isSidebarOpen ? { marginLeft: '5px' } : undefined}
        title={!isSidebarOpen ? item.name : undefined}
      >
        <Icon className={cn("h-4 w-4 flex-shrink-0", isActive ? "text-primary-foreground" : "text-muted-foreground")} />
        {isSidebarOpen && <span className="transition-opacity duration-150">{item.name}</span>}
      </Link>
    );
  }

  const GroupIcon = (group.icon as any) || LayoutDashboard;

  // When sidebar is closed, show only icon with popover submenu
  if (!isSidebarOpen) {
    return (
      <Popover open={submenuOpen} onOpenChange={setSubmenuOpen}>
        <PopoverTrigger asChild>
          <button
            className={cn(
              "flex items-center justify-center rounded-md transition-all duration-150 aspect-square w-9 h-9 p-0",
              hasActiveItem
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
            style={{ marginLeft: '5px' }}
            title={group.name}
          >
            <GroupIcon className="h-4 w-4 flex-shrink-0" />
          </button>
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
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className={cn("h-3 w-3", isActive ? "text-primary-foreground" : "text-muted-foreground")} />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <div className="space-y-1">
      <button
        onClick={onToggle}
        className={cn(
          "w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
          hasActiveItem
            ? "text-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        )}
      >
        <div className="flex items-center gap-3">
          {GroupIcon && <GroupIcon className="h-4 w-4 text-foreground" />}
          <span>{group.name}</span>
        </div>
        <ChevronRight
          className={cn(
            "h-4 w-4 transition-transform duration-150 ease-in-out",
            isOpen ? "rotate-90" : "rotate-0"
          )}
        />
      </button>

      <div
        className={cn(
          "ml-4 space-y-1 overflow-hidden transition-all duration-200 ease-in-out",
          isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        )}
      >
        {group.items.map((item: any) => {
          const Icon = (item.icon as any) || LayoutDashboard;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onItemClick}
              className={cn(
                "flex items-center transition-all duration-150",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                "gap-3 px-3 py-2 rounded-lg text-sm font-medium"
              )}
            >
              <Icon className={cn("h-3 w-3", isActive ? "text-primary-foreground" : "text-muted-foreground")} />
              {item.name}
            </Link>
          );
        })}
      </div>
    </div>
  );
};

export const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, checkPermission } = useAuth();
  const { toast } = useToast();
  const { filteredNavGroups, filterByPermissions } = useNavigationStore();
  const [openGroupIndex, setOpenGroupIndex] = useState<number | null>(null);
  const { isOpen, toggleSidebar } = useSidebar();
  const { selectedDomain, domains, setSelectedDomain } = useDomainStore();
  const [domainPopoverOpen, setDomainPopoverOpen] = useState(false);

  // Helper function to get favicon URL
  const getFaviconUrl = (url: string) => {
    try {
      const domain = new URL(url).hostname;
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
      return null;
    }
  };

  // Filter navigation based on user permissions
  useEffect(() => {
    if (user && checkPermission) {
      filterByPermissions(checkPermission);
    }
  }, [user, checkPermission, filterByPermissions]);

  // Auto-open menu group if one of its items is active
  useEffect(() => {
    const activeGroupIndex = filteredNavGroups.findIndex((group) =>
      group.items.some((item: any) => location.pathname === item.path)
    );
    if (activeGroupIndex !== -1) {
      setOpenGroupIndex(activeGroupIndex);
    }
  }, [location.pathname, filteredNavGroups]);

  const handleToggleGroup = (index: number) => {
    setOpenGroupIndex(openGroupIndex === index ? null : index);
  };

  const handleItemClick = () => {
    // Don't close menu if clicking on a submenu item within an open group
    // The useEffect above will handle keeping it open if needed
  };

  const handleLogout = async () => {
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
    }
  };

  return (
    <aside className={cn(
      "bg-card border-r border-border h-screen sticky top-0 overflow-y-auto flex flex-col transition-all duration-150",
      isOpen ? "w-64" : "w-16"
    )}>
      <div className={cn("border-b border-border transition-all duration-150", isOpen ? "p-6" : "p-2")}>
        <div className="flex items-center justify-between">
          {isOpen ? (
            <>
              <div>
                <h2 className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
                  PromptMaxx
                </h2>
                <p className="text-xs text-muted-foreground mt-1">AI Visibility & Content Strategy</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8 -mr-2"
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2 w-full px-2 pb-3">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8"
              >
                <ChevronsRight className="h-5 w-5" />
              </Button>
              {selectedDomain && getFaviconUrl(selectedDomain.url) && (
                <Popover open={domainPopoverOpen} onOpenChange={setDomainPopoverOpen}>
                  <PopoverTrigger asChild>
                    <button className="rounded-md overflow-hidden shadow-sm bg-background hover:ring-2 hover:ring-primary/50 transition-all" style={{ width: '36px', height: '36px' }}>
                      <img
                        src={getFaviconUrl(selectedDomain.url) || ''}
                        alt={selectedDomain.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[240px] p-0" side="right" align="start">
                    <Command>
                      <CommandInput placeholder="Search domains..." />
                      <CommandList>
                        <CommandEmpty>No domains found.</CommandEmpty>
                        <CommandGroup heading="Your Domains">
                          {domains.map((domain) => {
                            const faviconUrl = getFaviconUrl(domain.url);
                            return (
                              <CommandItem
                                key={domain.id}
                                value={domain.name}
                                onSelect={() => {
                                  setSelectedDomain(domain);
                                  setDomainPopoverOpen(false);
                                  if (user) {
                                    localStorage.setItem(`selected_domain_user_${user.id}`, String(domain.id));
                                  }
                                }}
                                className="flex items-center justify-between gap-2"
                              >
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  {faviconUrl ? (
                                    <img
                                      src={faviconUrl}
                                      alt=""
                                      className="h-4 w-4 flex-shrink-0 rounded"
                                      onError={(e) => {
                                        e.currentTarget.style.display = 'none';
                                        e.currentTarget.nextElementSibling?.classList.remove('hidden');
                                      }}
                                    />
                                  ) : null}
                                  <Globe className={cn("h-4 w-4 flex-shrink-0", faviconUrl && "hidden")} />
                                  <div className="flex flex-col flex-1 min-w-0">
                                    <span className="truncate">{domain.name}</span>
                                    <span className="text-xs text-muted-foreground">
                                      {domain.total_mentions} mentions
                                    </span>
                                  </div>
                                </div>
                                <Check
                                  className={cn(
                                    "h-4 w-4 flex-shrink-0",
                                    selectedDomain?.id === domain.id ? "opacity-100" : "opacity-0"
                                  )}
                                />
                              </CommandItem>
                            );
                          })}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
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

      <nav className={cn("space-y-2 flex-1", isOpen ? "p-4" : "py-4 px-2")}>
          {filteredNavGroups.map((group, index) => (
            <NavGroup
              key={index}
              group={group}
              location={location}
              isOpen={openGroupIndex === index}
              onToggle={() => handleToggleGroup(index)}
              isSidebarOpen={isOpen}
              onItemClick={handleItemClick}
            />
          ))}
      </nav>

      <div className={cn("border-t border-border mt-auto space-y-2 transition-all duration-150", isOpen ? "p-4" : "py-4 px-2")}>
          {/* Organization / Profile shortcuts */}
          {user && (
            <div className="space-y-2">
              {(user.role === 'admin' || user.role === 'super_admin') && (
                <Link
                  to="/organization-settings"
                  className={cn(
                    "flex items-center transition-all duration-150",
                    location.pathname === "/organization-settings"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isOpen
                      ? "gap-3 px-3 py-2 text-sm font-medium rounded-lg"
                      : "rounded-md justify-center aspect-square w-9 h-9 p-0"
                  )}
                  style={!isOpen ? { marginLeft: '5px' } : undefined}
                  title={!isOpen ? "Organization" : undefined}
                >
                  <Settings className={cn("h-4 w-4 flex-shrink-0", location.pathname === "/organization-settings" ? "text-primary-foreground" : "text-muted-foreground")} />
                  {isOpen && <span className="transition-opacity duration-150">Organization</span>}
                </Link>
              )}
              {user.role === 'admin' && (
                <Link
                  to="/profile"
                  className={cn(
                    "flex items-center transition-all duration-150",
                    location.pathname === "/profile"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isOpen
                      ? "gap-3 px-3 py-2 text-sm font-medium rounded-lg"
                      : "rounded-md justify-center aspect-square w-9 h-9 p-0"
                  )}
                  style={!isOpen ? { marginLeft: '5px' } : undefined}
                  title={!isOpen ? "Profile" : undefined}
                >
                  <User className={cn("h-4 w-4 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                  {isOpen && <span className="transition-opacity duration-150">Profile</span>}
                </Link>
              )}
              {user.role === 'user' && (
                <Link
                  to="/profile"
                  className={cn(
                    "flex items-center transition-all duration-150",
                    location.pathname === "/profile"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                    isOpen
                      ? "gap-3 px-3 py-2 text-sm font-medium rounded-lg"
                      : "rounded-md justify-center aspect-square w-9 h-9 p-0"
                  )}
                  style={!isOpen ? { marginLeft: '5px' } : undefined}
                  title={!isOpen ? "Profile" : undefined}
                >
                  <User className={cn("h-4 w-4 flex-shrink-0", location.pathname === "/profile" ? "text-primary-foreground" : "text-muted-foreground")} />
                  {isOpen && <span className="transition-opacity duration-150">Profile</span>}
                </Link>
              )}
            </div>
          )}

          <button
            onClick={handleLogout}
            className={cn(
              "flex items-center text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-all duration-150",
              isOpen
                ? "w-full gap-3 px-3 py-2 text-sm font-medium rounded-lg"
                : "rounded-md justify-center aspect-square w-9 h-9 p-0"
            )}
            style={!isOpen ? { marginLeft: '5px' } : undefined}
            title={!isOpen ? "Sign Out" : undefined}
          >
            <LogOut className="h-4 w-4 flex-shrink-0" />
            {isOpen && <span className="transition-opacity duration-150">Sign Out</span>}
          </button>
      </div>
    </aside>
  );
};
