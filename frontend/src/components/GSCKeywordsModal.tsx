import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2, MousePointer, Eye } from "lucide-react";

interface GSCKeyword {
  keyword: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

interface GSCKeywordsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  keywords: GSCKeyword[];
  isLoading: boolean;
  onAddKeywords: (keywords: string[]) => void;
  existingKeywords: string[];
}

export function GSCKeywordsModal({
  open,
  onOpenChange,
  keywords,
  isLoading,
  onAddKeywords,
  existingKeywords,
}: GSCKeywordsModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedKeywords, setSelectedKeywords] = useState<Set<string>>(new Set());

  // Reset selection when modal opens
  useEffect(() => {
    if (open) {
      setSelectedKeywords(new Set());
      setSearchQuery("");
    }
  }, [open]);

  // Filter keywords based on search and exclude existing
  const filteredKeywords = useMemo(() => {
    const existingSet = new Set(existingKeywords.map(k => k.toLowerCase()));
    return keywords.filter(k => {
      const matchesSearch = k.keyword.toLowerCase().includes(searchQuery.toLowerCase());
      const notExisting = !existingSet.has(k.keyword.toLowerCase());
      return matchesSearch && notExisting;
    });
  }, [keywords, searchQuery, existingKeywords]);

  const handleToggleKeyword = (keyword: string) => {
    const newSelected = new Set(selectedKeywords);
    if (newSelected.has(keyword)) {
      newSelected.delete(keyword);
    } else {
      newSelected.add(keyword);
    }
    setSelectedKeywords(newSelected);
  };

  const handleSelectAll = () => {
    const allFiltered = new Set(filteredKeywords.map(k => k.keyword));
    setSelectedKeywords(allFiltered);
  };

  const handleDeselectAll = () => {
    setSelectedKeywords(new Set());
  };

  const handleAddSelected = () => {
    onAddKeywords(Array.from(selectedKeywords));
    onOpenChange(false);
  };

  const formatNumber = (num: number) => {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Keywords from Google Search Console</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <span className="ml-2 text-muted-foreground">Loading keywords...</span>
          </div>
        ) : (
          <>
            {/* Search and Actions */}
            <div className="flex items-center gap-3 py-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search keywords..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button variant="outline" size="sm" onClick={handleSelectAll}>
                Select All
              </Button>
              <Button variant="outline" size="sm" onClick={handleDeselectAll}>
                Clear
              </Button>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-4 text-sm text-muted-foreground pb-2 border-b">
              <span>{filteredKeywords.length} keywords available</span>
              <span className="text-primary font-medium">
                {selectedKeywords.size} selected
              </span>
            </div>

            {/* Keywords List */}
            <div className="flex-1 min-h-0 overflow-y-auto">
              {filteredKeywords.length === 0 ? (
                <div className="flex items-center justify-center py-12 text-muted-foreground">
                  {searchQuery ? "No keywords match your search" : "No new keywords available"}
                </div>
              ) : (
                <div className="space-y-1 pr-1">
                  {filteredKeywords.map((kw) => (
                    <div
                      key={kw.keyword}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedKeywords.has(kw.keyword)
                          ? "bg-primary/5 border-primary/30"
                          : "bg-background hover:bg-muted/50 border-transparent"
                      }`}
                      onClick={() => handleToggleKeyword(kw.keyword)}
                    >
                      <Checkbox
                        checked={selectedKeywords.has(kw.keyword)}
                        onCheckedChange={() => handleToggleKeyword(kw.keyword)}
                        className="pointer-events-none"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{kw.keyword}</p>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1" title="Clicks">
                          <MousePointer className="h-3 w-3" />
                          <span>{formatNumber(kw.clicks)}</span>
                        </div>
                        <div className="flex items-center gap-1" title="Impressions">
                          <Eye className="h-3 w-3" />
                          <span>{formatNumber(kw.impressions)}</span>
                        </div>
                        <Badge variant="secondary" className="text-xs" title="Avg Position">
                          #{kw.position.toFixed(1)}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <DialogFooter className="pt-4 border-t">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleAddSelected}
                disabled={selectedKeywords.size === 0}
                className="gradient-primary"
              >
                Add {selectedKeywords.size} Keyword{selectedKeywords.size !== 1 ? 's' : ''}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
