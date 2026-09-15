/**
 * Account menu at the foot of the sidebar: who you are, then Settings, Switch
 * project, What's new and Sign out.
 *
 * Replaces the old footer (a Settings fly-out plus a separate Sign Out row)
 * with one trigger so the footer reads like an account card. Settings keeps
 * the same targets the fly-out had (Organization / Billing / Profile, gated by
 * role) — as a sub-menu when there is more than one, a plain row otherwise.
 * Switching a project reuses the sidebar's own switch logic via `onSwitchDomain`
 * so the two entry points can never drift.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, Building2, LogOut, Settings, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
  DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { User } from "@/types/auth";
import type { Domain } from "@/stores/domainStore";
import { getFaviconUrl, handleFaviconError } from "@/utils/faviconHelper";
import { WhatsNewDialog } from "./WhatsNewDialog";

const ROLE_LABEL: Record<User["role"], string> = { super_admin: "Owner", admin: "Admin", user: "Member", client: "Client" };

function initials(user: Pick<User, "first_name" | "last_name" | "email">) {
  const a = (user.first_name || "").trim();
  const b = (user.last_name || "").trim();
  if (a || b) return `${a[0] || ""}${b[0] || ""}`.toUpperCase();
  return (user.email || "?")[0].toUpperCase();
}

function displayName(user: Pick<User, "first_name" | "last_name" | "email">) {
  const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
  return name || user.email;
}

interface SettingsTarget { name: string; path: string; icon: typeof Settings }

interface Props {
  user: User;
  collapsed: boolean;
  settingsTargets: SettingsTarget[];
  domains: Domain[];
  selectedDomain: Domain | null;
  onSwitchDomain: (domain: Domain) => void | Promise<void>;
  onSignOut: () => void;
}

export function UserMenu({ user, collapsed, settingsTargets, domains, selectedDomain, onSwitchDomain, onSignOut }: Props) {
  const navigate = useNavigate();
  const [whatsNew, setWhatsNew] = useState(false);
  const name = displayName(user);
  const role = ROLE_LABEL[user.role] || user.role;

  const trigger = collapsed ? (
    <button className="mx-auto flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent" aria-label="Account menu">
      <Avatar className="h-7 w-7"><AvatarFallback className="text-[11px] font-semibold">{initials(user)}</AvatarFallback></Avatar>
    </button>
  ) : (
    <button className="flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left hover:bg-accent" aria-label="Account menu">
      <Avatar className="h-8 w-8 mt-0.5"><AvatarFallback className="text-xs font-semibold">{initials(user)}</AvatarFallback></Avatar>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold leading-tight break-words">{name}</span>
        <span className="block text-xs text-muted-foreground leading-tight truncate" title={`${user.email} · ${role}`}>{user.email} · {role}</span>
      </span>
    </button>
  );

  return (
    <>
      <DropdownMenu>
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger asChild><DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger></TooltipTrigger>
            <TooltipContent side="right"><p>{name}</p></TooltipContent>
          </Tooltip>
        ) : (
          <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
        )}
        <DropdownMenuContent side={collapsed ? "right" : "top"} align={collapsed ? "end" : "start"} className="w-64">
          <DropdownMenuLabel className="font-normal">
            <p className="text-sm font-semibold leading-tight">{name}</p>
            <p className="text-xs text-muted-foreground leading-tight truncate">{user.email} · {role}</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />

          {settingsTargets.length > 1 ? (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger><Settings className="mr-2 h-4 w-4" />Settings</DropdownMenuSubTrigger>
              <DropdownMenuSubContent className="w-48">
                {settingsTargets.map((t) => (
                  <DropdownMenuItem key={t.path} onSelect={() => navigate(t.path)}><t.icon className="mr-2 h-4 w-4" />{t.name}</DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          ) : (
            <DropdownMenuItem onSelect={() => navigate(settingsTargets[0]?.path || "/profile")}><Settings className="mr-2 h-4 w-4" />Settings</DropdownMenuItem>
          )}

          <DropdownMenuSub>
            <DropdownMenuSubTrigger><ArrowLeftRight className="mr-2 h-4 w-4" />Switch project</DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="w-60 max-h-72 overflow-y-auto">
              {domains.length === 0 && <DropdownMenuItem disabled>No projects yet</DropdownMenuItem>}
              {domains.map((d) => {
                const busy = !!d.processing_status && ["INIT", "SCHD", "PROC", "FAIL"].includes(d.processing_status);
                const favicon = getFaviconUrl(d.url, 32);
                return (
                  <DropdownMenuItem key={d.id} disabled={busy} onSelect={() => onSwitchDomain(d)}
                                    className={cn("flex items-center gap-2", selectedDomain?.id === d.id && "bg-accent")}>
                    {favicon ? (
                      <img src={favicon} alt="" className="h-4 w-4 rounded-sm flex-none" onError={(e) => handleFaviconError(e, d.url, d.name, 32)} />
                    ) : (
                      <Building2 className="h-4 w-4 flex-none text-muted-foreground" />
                    )}
                    <span className="truncate flex-1">{d.name}</span>
                    {busy && <span className="text-[10px] text-muted-foreground">{d.processing_status === "FAIL" ? "failed" : "processing"}</span>}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuSubContent>
          </DropdownMenuSub>

          <DropdownMenuItem onSelect={() => setWhatsNew(true)}><Sparkles className="mr-2 h-4 w-4" />What's new</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={onSignOut}><LogOut className="mr-2 h-4 w-4" />Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <WhatsNewDialog open={whatsNew} onOpenChange={setWhatsNew} />
    </>
  );
}

