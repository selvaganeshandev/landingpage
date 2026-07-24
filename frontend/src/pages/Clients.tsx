import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import { UserPlus, Users, Loader2, RefreshCw } from "lucide-react";

interface ClientDomain {
  id: number;
  name: string;
  url: string;
}

interface Client {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  account_status: "active" | "suspended" | "pending" | "disabled";
  last_login: string | null;
  active_domain_id: number | null;
  domains: ClientDomain[];
  created_at: string;
}

interface DomainOption {
  id: number;
  name: string;
  url: string;
}

const STATUS_STYLES: Record<Client["account_status"], string> = {
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
  if (!value) return "Never";
  return new Date(value).toLocaleString();
}

export default function Clients() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<Client[]>([]);
  const [domains, setDomains] = useState<DomainOption[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [manageClient, setManageClient] = useState<Client | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [clientsRes, domainsRes] = await Promise.all([
        apiClient.getClients(),
        apiClient.getDomains({ fields: "minimal" }),
      ]);
      setClients((clientsRes as { clients: Client[] }).clients || []);
      setDomains((domainsRes as { domains: DomainOption[] }).domains || []);
    } catch (error) {
      toast({
        title: "Failed to load clients",
        description: error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <PageLoader />;

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" />
            Clients
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Give each client a read-only login scoped to the domains you assign them.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={loadData} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Client
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">
            {clients.length} client{clients.length === 1 ? "" : "s"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {clients.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-muted-foreground">
              No clients yet. Add one to give them access to their domain.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Domains</TableHead>
                  <TableHead>Last login</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {clients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell>
                      <div className="font-medium">
                        {[client.first_name, client.last_name].filter(Boolean).join(" ") || client.email}
                      </div>
                      <div className="text-xs text-muted-foreground">{client.email}</div>
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_STYLES[client.account_status]} variant="secondary">
                        {client.account_status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {client.domains.length === 0 ? (
                          <span className="text-xs text-muted-foreground">None</span>
                        ) : (
                          client.domains.map((d) => (
                            <Badge key={d.id} variant="outline" className="text-xs">
                              {d.name}
                            </Badge>
                          ))
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(client.last_login)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" onClick={() => setManageClient(client)}>
                        Manage
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {createOpen && (
        <CreateClientDialog
          domains={domains}
          submitting={submitting}
          onClose={() => setCreateOpen(false)}
          onCreate={async (payload) => {
            setSubmitting(true);
            try {
              await apiClient.createClient(payload);
              toast({ title: "Client created", description: `Invite sent to ${payload.email}.` });
              setCreateOpen(false);
              await loadData();
            } catch (error) {
              toast({
                title: "Could not create client",
                description: error instanceof Error ? error.message : "Please try again.",
                variant: "destructive",
              });
            } finally {
              setSubmitting(false);
            }
          }}
        />
      )}

      {manageClient && (
        <ManageClientDialog
          client={manageClient}
          domains={domains}
          submitting={submitting}
          onClose={() => setManageClient(null)}
          onSave={async (domainIds, accountStatus) => {
            setSubmitting(true);
            try {
              await apiClient.updateClient(manageClient.id, {
                domain_ids: domainIds,
                account_status: accountStatus,
              });
              toast({ title: "Client updated" });
              setManageClient(null);
              await loadData();
            } catch (error) {
              toast({
                title: "Could not update client",
                description: error instanceof Error ? error.message : "Please try again.",
                variant: "destructive",
              });
            } finally {
              setSubmitting(false);
            }
          }}
          onDeactivate={async () => {
            setSubmitting(true);
            try {
              await apiClient.deactivateClient(manageClient.id);
              toast({ title: "Client deactivated" });
              setManageClient(null);
              await loadData();
            } catch (error) {
              toast({
                title: "Could not deactivate client",
                description: error instanceof Error ? error.message : "Please try again.",
                variant: "destructive",
              });
            } finally {
              setSubmitting(false);
            }
          }}
        />
      )}
    </div>
  );
}

interface DomainPickerProps {
  domains: DomainOption[];
  selected: Set<number>;
  onToggle: (id: number) => void;
}

function DomainPicker({ domains, selected, onToggle }: DomainPickerProps) {
  return (
    <div className="max-h-48 overflow-y-auto rounded-md border divide-y">
      {domains.length === 0 ? (
        <div className="px-3 py-4 text-sm text-muted-foreground">No domains available.</div>
      ) : (
        domains.map((domain) => (
          <label
            key={domain.id}
            className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-accent"
          >
            <Checkbox
              checked={selected.has(domain.id)}
              onCheckedChange={() => onToggle(domain.id)}
            />
            <span className="text-sm">
              {domain.name}
              <span className="text-muted-foreground ml-2 text-xs">{domain.url}</span>
            </span>
          </label>
        ))
      )}
    </div>
  );
}

interface CreateClientDialogProps {
  domains: DomainOption[];
  submitting: boolean;
  onClose: () => void;
  onCreate: (payload: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    domain_ids: number[];
  }) => void;
}

function CreateClientDialog({ domains, submitting, onClose, onCreate }: CreateClientDialogProps) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState(() => generatePassword());
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const canSubmit = email.trim() && password.trim() && selected.size > 0 && !submitting;

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add client</DialogTitle>
          <DialogDescription>
            They receive a read-only login for the domains you select.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="first">First name</Label>
              <Input id="first" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="last">Last name</Label>
              <Input id="last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="client@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Temporary password</Label>
            <div className="flex gap-2">
              <Input id="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <Button
                type="button"
                variant="outline"
                onClick={() => setPassword(generatePassword())}
              >
                Regenerate
              </Button>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Domains ({selected.size} selected)</Label>
            <DomainPicker domains={domains} selected={selected} onToggle={toggle} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() =>
              onCreate({
                email: email.trim().toLowerCase(),
                password,
                first_name: firstName.trim(),
                last_name: lastName.trim(),
                domain_ids: Array.from(selected),
              })
            }
          >
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Create client
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ManageClientDialogProps {
  client: Client;
  domains: DomainOption[];
  submitting: boolean;
  onClose: () => void;
  onSave: (domainIds: number[], accountStatus: string) => void;
  onDeactivate: () => void;
}

function ManageClientDialog({
  client, domains, submitting, onClose, onSave, onDeactivate,
}: ManageClientDialogProps) {
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(client.domains.map((d) => d.id)),
  );
  const isSuspended = client.account_status === "suspended";
  const nextStatus = isSuspended ? "active" : "suspended";

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const displayName = useMemo(
    () => [client.first_name, client.last_name].filter(Boolean).join(" ") || client.email,
    [client],
  );

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Manage {displayName}</DialogTitle>
          <DialogDescription>{client.email}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Assigned domains ({selected.size})</Label>
            <DomainPicker domains={domains} selected={selected} onToggle={toggle} />
          </div>

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <div className="text-sm font-medium">
                {isSuspended ? "Reactivate access" : "Suspend access"}
              </div>
              <div className="text-xs text-muted-foreground">
                {isSuspended
                  ? "Restore this client's login immediately."
                  : "Blocks login and ends any live session immediately."}
              </div>
            </div>
            <Button
              variant={isSuspended ? "default" : "secondary"}
              size="sm"
              disabled={submitting}
              onClick={() => onSave(Array.from(selected), nextStatus)}
            >
              {isSuspended ? "Reactivate" : "Suspend"}
            </Button>
          </div>
        </div>

        <DialogFooter className="justify-between sm:justify-between">
          <Button variant="destructive" onClick={onDeactivate} disabled={submitting}>
            Deactivate
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              disabled={submitting}
              onClick={() => onSave(Array.from(selected), client.account_status)}
            >
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save domains
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
