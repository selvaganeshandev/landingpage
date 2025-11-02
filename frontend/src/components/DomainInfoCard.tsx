import React from 'react';
import { useDomainStore } from '@/stores/domainStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Globe, TrendingUp, MessageSquare, AlertTriangle } from 'lucide-react';

/**
 * Example component showing how to access the selected domain from any component
 * using the Zustand domain store
 */
export const DomainInfoCard = () => {
  const { selectedDomain, domains } = useDomainStore();

  if (!selectedDomain) {
    return (
      <Card className="border border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Domain Information
          </CardTitle>
          <CardDescription>
            No domain selected
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Please select a domain to view information.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe className="h-5 w-5" />
          {selectedDomain.name}
        </CardTitle>
        <CardDescription>
          {selectedDomain.url}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-blue-500" />
            <div>
              <p className="text-sm font-medium">{selectedDomain.total_mentions}</p>
              <p className="text-xs text-muted-foreground">Mentions</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-500" />
            <div>
              <p className="text-sm font-medium">{selectedDomain.visibility_score}</p>
              <p className="text-xs text-muted-foreground">Visibility Score</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-500" />
            <div>
              <p className="text-sm font-medium">{selectedDomain.active_alerts}</p>
              <p className="text-xs text-muted-foreground">Active Alerts</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded-full bg-gray-200 flex items-center justify-center">
              <div className={`h-2 w-2 rounded-full ${
                selectedDomain.sentiment === 'positive' ? 'bg-green-500' :
                selectedDomain.sentiment === 'negative' ? 'bg-red-500' : 'bg-yellow-500'
              }`} />
            </div>
            <div>
              <p className="text-sm font-medium capitalize">{selectedDomain.sentiment}</p>
              <p className="text-xs text-muted-foreground">Sentiment</p>
            </div>
          </div>
        </div>
        
        <div className="text-xs text-muted-foreground">
          <p>Total domains: {domains.length}</p>
          <p>Last updated: {new Date(selectedDomain.modified_at).toLocaleDateString()}</p>
        </div>
      </CardContent>
    </Card>
  );
};

export default DomainInfoCard;
