import { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/services/api";
import { PageLoader } from "@/components/PageLoader";
import { DomainClientAccess } from "@/components/DomainClientAccess";
import { Users, Search, ChevronDown, ChevronRight, Globe } from "lucide-react";

interface DomainRow {
  id: number;
  name: string;
  url: string;
}

export default function Clients() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [domains, setDomains] = useState<DomainRow[]>([]);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiClient.getDomains({ fields: "minimal" });
        setDomains((res as { domains: DomainRow[] }).domains || []);
      } catch (error) {
        toast({
          title: "Failed to load domains",
          description: error instanceof Error ? error.message : "Please try again.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return domains;
    return domains.filter((d) => d.name.toLowerCase().includes(q) || d.url.toLowerCase().includes(q));
  }, [domains, search]);

  if (loading) return <PageLoader />;

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Users className="h-6 w-6 text-primary" />
          Clients
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Each domain is a client. Give a client a read-only login to view their own domain.
        </p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search domains…"
          className="pl-9"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground py-8 text-center">No domains found.</p>
      ) : (
        <div className="space-y-2">
          {filtered.map((domain) => {
            const isOpen = expandedId === domain.id;
            return (
              <Card key={domain.id} className="overflow-hidden">
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent/50 transition-colors"
                  onClick={() => setExpandedId(isOpen ? null : domain.id)}
                >
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  )}
                  <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="min-w-0">
                    <span className="font-medium block truncate">{domain.name}</span>
                    <span className="text-xs text-muted-foreground block truncate">{domain.url}</span>
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {isOpen ? "Hide" : "Manage client login"}
                  </span>
                </button>
                {isOpen && (
                  <CardContent className="border-t pt-4">
                    <DomainClientAccess domainId={domain.id} domainName={domain.name} />
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
