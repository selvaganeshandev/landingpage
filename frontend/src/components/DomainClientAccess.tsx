import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { Loader2, UserPlus, ShieldCheck, MailCheck } from "lucide-react";

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

  const handleInvite = async () => {
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail) return;
    setSubmitting(true);
    try {
      await apiClient.sendInvitation({
        email: trimmedEmail,
        role: "client",
        domain: domainId,
      });
      toast({
        title: "Invitation sent",
        description: `We've emailed ${trimmedEmail} a link to set up their read-only login.`,
      });
      setShowForm(false);
      setEmail("");
      await load();
    } catch (error) {
      toast({
        title: "Could not send invitation",
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
          Invite a client to a read-only login for {domainName ? <strong>{domainName}</strong> : "this domain"} only.
          They receive an email to set their own password, and cannot see other domains or change any data.
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
              <p className="text-sm text-muted-foreground">No client access yet for this domain.</p>
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
                <div className="space-y-1.5">
                  <Label htmlFor="dc-email">Client email</Label>
                  <Input
                    id="dc-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="client@example.com"
                  />
                  <p className="text-xs text-muted-foreground">
                    They'll get an invitation link to create their password and name.
                  </p>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setShowForm(false)} disabled={submitting}>
                    Cancel
                  </Button>
                  <Button onClick={handleInvite} disabled={submitting || !email.trim()}>
                    {submitting ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <MailCheck className="h-4 w-4 mr-2" />
                    )}
                    Send invitation
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="outline" onClick={() => setShowForm(true)}>
                <UserPlus className="h-4 w-4 mr-2" />
                Invite client
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
