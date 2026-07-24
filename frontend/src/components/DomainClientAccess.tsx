import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Loader2, UserPlus, ShieldCheck } from "lucide-react";

interface DomainClient {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  account_status: "active" | "suspended" | "pending" | "disabled";
  last_login: string | null;
  created_at: string;
}

const STATUS_STYLES: Record<DomainClient["account_status"], string> = {
  active: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  suspended: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  pending: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  disabled: "bg-muted text-muted-foreground",
};

function generatePassword(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$";
  const bytes = new Uint32Array(14);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => chars[b % chars.length]).join("");
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Never";
}

interface Props {
  domainId: number;
  domainName?: string;
}

export function DomainClientAccess({ domainId, domainName }: Props) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<DomainClient[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState(() => generatePassword());

  const load = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getDomainClients(domainId);
      setClients((res as { clients: DomainClient[] }).clients || []);
    } catch (error) {
      toast({
        title: "Failed to load client access",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainId]);

  const handleCreate = async () => {
    if (!email.trim() || !password.trim()) return;
    setSubmitting(true);
    try {
      await apiClient.createDomainClient(domainId, {
        email: email.trim().toLowerCase(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      toast({ title: "Client access granted", description: `${email} can now sign in to view this domain.` });
      setShowForm(false);
      setEmail(""); setFirstName(""); setLastName(""); setPassword(generatePassword());
      await load();
    } catch (error) {
      toast({
        title: "Could not grant access",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (client: DomainClient) => {
    const next = client.account_status === "suspended" ? "active" : "suspended";
    setSubmitting(true);
    try {
      await apiClient.updateDomainClient(domainId, client.id, { account_status: next });
      toast({ title: next === "active" ? "Access reactivated" : "Access suspended" });
      await load();
    } catch (error) {
      toast({
        title: "Update failed",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (client: DomainClient) => {
    setSubmitting(true);
    try {
      await apiClient.removeDomainClient(domainId, client.id);
      toast({ title: "Client access removed" });
      await load();
    } catch (error) {
      toast({
        title: "Remove failed",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ShieldCheck className="h-5 w-5 text-primary" />
          Client access
        </CardTitle>
        <CardDescription>
          Give this client a read-only login to view {domainName ? <strong>{domainName}</strong> : "this domain"} only.
          They cannot see other domains or change any data.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-6">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <>
            {clients.length === 0 ? (
              <p className="text-sm text-muted-foreground">No client login yet for this domain.</p>
            ) : (
              <div className="space-y-2">
                {clients.map((client) => (
                  <div
                    key={client.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate">
                        {[client.first_name, client.last_name].filter(Boolean).join(" ") || client.email}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {client.email} · last login {formatDate(client.last_login)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={STATUS_STYLES[client.account_status]} variant="secondary">
                        {client.account_status}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={submitting}
                        onClick={() => handleToggleStatus(client)}
                      >
                        {client.account_status === "suspended" ? "Reactivate" : "Suspend"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        disabled={submitting}
                        onClick={() => handleRemove(client)}
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {showForm ? (
              <div className="space-y-3 rounded-md border p-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="dc-first">First name</Label>
                    <Input id="dc-first" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="dc-last">Last name</Label>
                    <Input id="dc-last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="dc-email">Email</Label>
                  <Input
                    id="dc-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="client@example.com"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="dc-pass">Temporary password</Label>
                  <div className="flex gap-2">
                    <Input id="dc-pass" value={password} onChange={(e) => setPassword(e.target.value)} />
                    <Button type="button" variant="outline" onClick={() => setPassword(generatePassword())}>
                      Regenerate
                    </Button>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowForm(false)} disabled={submitting}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreate} disabled={submitting || !email.trim() || !password.trim()}>
                    {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Grant access
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="outline" onClick={() => setShowForm(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Add client login
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
