/**
 * Settings > Get your API key — mint, copy, watch and revoke service API keys.
 *
 * A service key is a machine credential for external integrations (the MCP
 * server, Enque, scripts). It reads the whole organisation and can never
 * write. Keys are stored encrypted at rest, so an admin can copy one again
 * later; the usage box shows what each key has actually been used for.
 */
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Activity, BookOpen, Copy, KeyRound, ShieldOff } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface ServiceKey {
  id: number;
  name: string;
  key_prefix: string;
  created_at: string;
  created_by: string | null;
  revoked: boolean;
  last_used_at: string | null;
}

interface KeyUsage {
  total_calls: number;
  calls_24h: number;
  last_used_at: string | null;
  top_endpoints: { path: string; calls: number }[];
  recent: { path: string; method: string; created_at: string }[];
}

export default function ServiceApiKeysCard() {
  const { toast } = useToast();
  const [keys, setKeys] = useState<ServiceKey[]>([]);
  const [name, setName] = useState("");
  const [minting, setMinting] = useState(false);
  const [freshKey, setFreshKey] = useState<string | null>(null);
  const [usageFor, setUsageFor] = useState<number | null>(null);
  const [usage, setUsage] = useState<KeyUsage | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.get<{ keys: ServiceKey[] }>("/auth/service-api-keys/");
      setKeys(res.keys || []);
    } catch {
      toast({ title: "Could not load API keys", variant: "destructive" });
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const mint = async () => {
    if (!name.trim()) return;
    setMinting(true);
    try {
      const res = await apiClient.post<{ plaintext: string }>("/auth/service-api-keys/", { name: name.trim() });
      setFreshKey(res.plaintext);
      setName("");
      load();
    } catch {
      toast({ title: "Could not create the key", variant: "destructive" });
    } finally {
      setMinting(false);
    }
  };

  const copyKey = async (id: number) => {
    try {
      const res = await apiClient.post<{ plaintext: string }>(`/auth/service-api-keys/${id}/reveal/`);
      await navigator.clipboard.writeText(res.plaintext);
      toast({ title: "Key copied to clipboard" });
    } catch {
      toast({ title: "Could not reveal the key", variant: "destructive" });
    }
  };

  const revoke = async (id: number) => {
    try {
      await apiClient.post(`/auth/service-api-keys/${id}/revoke/`);
      toast({ title: "Key revoked" });
      if (usageFor === id) setUsageFor(null);
      load();
    } catch {
      toast({ title: "Could not revoke the key", variant: "destructive" });
    }
  };

  const toggleUsage = async (id: number) => {
    if (usageFor === id) { setUsageFor(null); setUsage(null); return; }
    try {
      const res = await apiClient.get<KeyUsage>(`/auth/service-api-keys/${id}/usage/`);
      setUsage(res);
      setUsageFor(id);
    } catch {
      toast({ title: "Could not load usage", variant: "destructive" });
    }
  };

  const copyFresh = () => {
    if (freshKey) {
      navigator.clipboard.writeText(freshKey);
      toast({ title: "Copied" });
    }
  };

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="h-4 w-4" /> Get your API key
          <Tooltip>
            <TooltipTrigger asChild>
              <a
                href="/docs/mcp-connection.html"
                target="_blank"
                rel="noopener"
                className="ml-auto inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              >
                <BookOpen className="h-3.5 w-3.5" /> Connection docs
              </a>
            </TooltipTrigger>
            <TooltipContent>
              How to connect Claude, Enque or any MCP client with this key
            </TooltipContent>
          </Tooltip>
        </CardTitle>
        <CardDescription>
          Machine credentials for external integrations (MCP, Enque, scripts). A service key can
          read everything in this organisation and can never write. Keys are stored encrypted, so
          you can copy one again later; revoking takes effect immediately.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Key name (e.g. enque-sync)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && mint()}
          />
          <Button onClick={mint} disabled={minting || !name.trim()}>
            {minting ? "Creating…" : "Create key"}
          </Button>
        </div>

        {freshKey && (
          <div className="rounded-md border border-primary/40 bg-primary/5 p-3 space-y-2">
            <p className="text-sm font-medium">Your new key:</p>
            <div className="flex items-center gap-2">
              <code className="text-xs break-all flex-1">{freshKey}</code>
              <Button size="sm" variant="outline" onClick={copyFresh}>
                <Copy className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}

        <div className="divide-y divide-border rounded-md border border-border">
          {keys.length === 0 && (
            <p className="p-3 text-sm text-muted-foreground">No keys yet.</p>
          )}
          {keys.map((k) => (
            <div key={k.id}>
              <div className="flex items-center gap-3 p-3 text-sm">
                <span className="font-medium">{k.name}</span>
                <code className="text-xs text-muted-foreground">{k.key_prefix}</code>
                <span className="text-xs text-muted-foreground ml-auto">
                  {k.revoked
                    ? "revoked"
                    : k.last_used_at
                      ? `last used ${new Date(k.last_used_at).toLocaleString()}`
                      : "never used"}
                </span>
                {!k.revoked && (
                  <Button size="sm" variant="ghost" onClick={() => copyKey(k.id)} title="Copy key">
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => toggleUsage(k.id)} title="Usage">
                  <Activity className="h-3.5 w-3.5" />
                </Button>
                {!k.revoked && (
                  <Button size="sm" variant="ghost" onClick={() => revoke(k.id)} title="Revoke">
                    <ShieldOff className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                )}
              </div>

              {usageFor === k.id && usage && (
                <div className="mx-3 mb-3 rounded-md border border-border bg-muted/30 p-3 text-sm space-y-3">
                  <div className="flex gap-6">
                    <div><span className="text-lg font-semibold">{usage.total_calls}</span>
                      <span className="text-xs text-muted-foreground ml-1.5">total calls</span></div>
                    <div><span className="text-lg font-semibold">{usage.calls_24h}</span>
                      <span className="text-xs text-muted-foreground ml-1.5">last 24 h</span></div>
                  </div>
                  {usage.top_endpoints.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">What it's used for</p>
                      {usage.top_endpoints.map((t) => (
                        <div key={t.path} className="flex justify-between text-xs py-0.5">
                          <code>{t.path}</code>
                          <span className="text-muted-foreground">{t.calls} calls</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {usage.recent.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Recent activity</p>
                      <div className="max-h-36 overflow-y-auto">
                        {usage.recent.map((r, i) => (
                          <div key={i} className="flex justify-between text-xs py-0.5">
                            <code>{r.method} {r.path}</code>
                            <span className="text-muted-foreground">{new Date(r.created_at).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {usage.total_calls === 0 && (
                    <p className="text-xs text-muted-foreground">No requests made with this key yet.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
