import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, Check, Eye, EyeOff, Copy, Pencil, KeyRound, Wallet } from "lucide-react";

interface DataForSeoState {
  configured: boolean;
  /** 'organisation' when this org supplies its own account, else 'system'. */
  source: "organisation" | "system";
  login: string;
  login_preview: string | null;
  password_preview: string | null;
  status: string;
  balance: number | null;
  error: string;
}

/**
 * DataForSEO credentials.
 *
 * Kept apart from the LLM provider grid on purpose: DataForSEO is not a chat
 * model, is never quota-probed as one, and authenticates with HTTP Basic — a
 * login plus a password rather than a single bearer key.
 *
 * The balance is shown because the validation endpoint returns it for free, and
 * "how much credit is left" is the question anyone opening this screen actually
 * has. Backlink fetches draw down that balance.
 */
export const DataForSeoCredentialsCard = () => {
  const { toast } = useToast();

  const [state, setState] = useState<DataForSeoState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [revealed, setRevealed] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setState((await apiClient.getDataForSeoCredentials()) as DataForSeoState);
    } catch {
      setState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    if (!login.trim() || !password.trim()) return;
    setSaving(true);
    try {
      const next = (await apiClient.saveDataForSeoCredentials({
        login: login.trim(), password: password.trim(),
      })) as DataForSeoState;
      setState(next);
      setEditing(false);
      setPassword("");
      setShowPassword(false);
      setRevealed(null);
      toast({ title: "DataForSEO credentials saved", description: "Verified against DataForSEO." });
    } catch (err: any) {
      // The server validates before storing, so a rejection here is a real
      // credential problem rather than something to retry.
      toast({
        title: "Could not save",
        description: err?.data?.error || err?.message || "Please check the login and password.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    setSaving(true);
    try {
      setState((await apiClient.clearDataForSeoCredentials()) as DataForSeoState);
      setRevealed(null);
      toast({
        title: "Credentials cleared",
        description: "This organisation now uses the system DataForSEO account.",
      });
    } catch (err: any) {
      toast({ title: "Could not clear credentials", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleReveal = async () => {
    try {
      const res = (await apiClient.revealDataForSeoPassword()) as { password: string };
      setRevealed(res.password);
    } catch {
      toast({ title: "Could not reveal the password", variant: "destructive" });
    }
  };

  const connected = state?.status === "CONNECTED";
  const ownAccount = state?.source === "organisation";

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle>Data Provider</CardTitle>
        <CardDescription>
          DataForSEO powers backlink profiles and keyword search volume. Leave this empty to use
          the system-level account. The password is encrypted at rest.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          </div>
        ) : (
          <Card className="border border-border md:max-w-xl">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <KeyRound className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-sm">DataForSEO</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {ownAccount ? "This organisation's own account" : "Using the system account"}
                    </p>
                  </div>
                </div>
                <Badge variant={connected ? "default" : "secondary"} className="flex-shrink-0">
                  {connected ? "Connected" : state?.configured ? "Invalid" : "Not configured"}
                </Badge>
              </div>

              {/* Free to read, and the only number that matters before a fetch. */}
              {state?.balance != null && (
                <div className="flex items-center gap-2 text-sm">
                  <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">Balance</span>
                  <span className="font-semibold">${state.balance.toFixed(2)}</span>
                </div>
              )}

              {state?.error && (
                <p className="text-xs text-destructive">{state.error}</p>
              )}

              {!editing ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2">
                    <span className="text-sm font-mono truncate">
                      {revealed ?? state?.login_preview ?? "Not set"}
                    </span>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {ownAccount && (
                        <>
                          <Button variant="ghost" size="sm" onClick={handleReveal} className="gap-1.5">
                            <Eye className="h-3.5 w-3.5" /> Reveal
                          </Button>
                          {revealed && (
                            <Button
                              variant="ghost" size="sm" className="gap-1.5"
                              onClick={() => {
                                navigator.clipboard.writeText(revealed);
                                toast({ title: "Password copied" });
                              }}
                            >
                              <Copy className="h-3.5 w-3.5" /> Copy
                            </Button>
                          )}
                        </>
                      )}
                      <Button
                        variant="ghost" size="sm" className="gap-1.5"
                        onClick={() => {
                          setEditing(true);
                          setLogin(ownAccount ? state?.login ?? "" : "");
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" /> Edit
                      </Button>
                    </div>
                  </div>
                  {ownAccount && (
                    <Button variant="ghost" size="sm" onClick={handleClear} disabled={saving}>
                      Use the system account instead
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="dfs-login" className="text-xs">Login</Label>
                    <Input
                      id="dfs-login"
                      value={login}
                      onChange={(e) => setLogin(e.target.value)}
                      placeholder="you@example.com"
                      autoComplete="off"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="dfs-password" className="text-xs">API password</Label>
                    <div className="relative">
                      <Input
                        id="dfs-password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Your DataForSEO API password"
                        autoComplete="new-password"
                        className="pr-9"
                      />
                      <button
                        type="button"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                        onClick={() => setShowPassword((v) => !v)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={!login.trim() || !password.trim() || saving}
                      onClick={handleSave}
                      className="gap-1.5"
                    >
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                      Save
                    </Button>
                    <Button
                      size="sm" variant="ghost"
                      onClick={() => { setEditing(false); setPassword(""); setShowPassword(false); }}
                    >
                      Cancel
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Verified against DataForSEO before it is stored, so a typo is caught here
                    rather than as a failed backlink fetch later.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  );
};
