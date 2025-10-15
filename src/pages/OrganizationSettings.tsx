import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Plus, Trash2, Globe } from "lucide-react";

export default function OrganizationSettings() {
  const { toast } = useToast();
  const [orgName, setOrgName] = useState("Acme Corp");
  const [domains, setDomains] = useState([
    { id: "1", domain: "acme.com", verified: true },
    { id: "2", domain: "acmecorp.com", verified: false },
  ]);
  const [newDomain, setNewDomain] = useState("");

  const handleAddDomain = () => {
    if (!newDomain.trim()) return;

    // TODO: Connect to Supabase
    const domain = {
      id: Date.now().toString(),
      domain: newDomain.trim(),
      verified: false,
    };
    setDomains([...domains, domain]);
    setNewDomain("");
    toast({
      title: "Domain added",
      description: `${domain.domain} has been added to your organization.`,
    });
  };

  const handleRemoveDomain = (id: string) => {
    // TODO: Connect to Supabase
    setDomains(domains.filter(d => d.id !== id));
    toast({
      title: "Domain removed",
      description: "The domain has been removed from your organization.",
    });
  };

  const handleUpdateOrgName = () => {
    // TODO: Connect to Supabase
    toast({
      title: "Organization updated",
      description: "Your organization name has been updated.",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Organization Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your organization and domains
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
          <CardDescription>
            Update your organization information
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="org-name">Organization Name</Label>
            <div className="flex gap-2">
              <Input
                id="org-name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
              <Button onClick={handleUpdateOrgName}>Save</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Domains</CardTitle>
          <CardDescription>
            Add and manage domains for your organization. All brand monitoring will be scoped to these domains.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="example.com"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleAddDomain()}
            />
            <Button onClick={handleAddDomain}>
              <Plus className="h-4 w-4 mr-2" />
              Add Domain
            </Button>
          </div>

          <Separator />

          <div className="space-y-3">
            {domains.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Globe className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No domains added yet</p>
              </div>
            ) : (
              domains.map((domain) => (
                <div
                  key={domain.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{domain.domain}</p>
                      <Badge variant={domain.verified ? "default" : "secondary"} className="mt-1">
                        {domain.verified ? "Verified" : "Pending"}
                      </Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveDomain(domain.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>
            Manage team members and their roles (Coming soon)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            Team management features will be available after database integration.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
