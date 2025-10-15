import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Globe, Search } from "lucide-react";

interface AddLanguageDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd?: (languages: string[]) => void;
}

const availableLanguages = [
  { code: "zh", name: "Chinese (Simplified)", speakers: "1.1B", region: "Asia" },
  { code: "hi", name: "Hindi", speakers: "602M", region: "Asia" },
  { code: "ar", name: "Arabic", speakers: "274M", region: "Middle East" },
  { code: "ja", name: "Japanese", speakers: "125M", region: "Asia" },
  { code: "ru", name: "Russian", speakers: "258M", region: "Europe/Asia" },
  { code: "ko", name: "Korean", speakers: "81M", region: "Asia" },
  { code: "nl", name: "Dutch", speakers: "24M", region: "Europe" },
  { code: "pl", name: "Polish", speakers: "41M", region: "Europe" },
  { code: "sv", name: "Swedish", speakers: "10M", region: "Europe" },
  { code: "tr", name: "Turkish", speakers: "88M", region: "Europe/Asia" },
  { code: "vi", name: "Vietnamese", speakers: "85M", region: "Asia" },
  { code: "th", name: "Thai", speakers: "60M", region: "Asia" },
];

export const AddLanguageDialog = ({ open, onOpenChange, onAdd }: AddLanguageDialogProps) => {
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedLanguages, setSelectedLanguages] = useState<Set<string>>(new Set());

  const filteredLanguages = availableLanguages.filter(lang =>
    lang.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lang.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    lang.region.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleLanguage = (code: string) => {
    const newSelected = new Set(selectedLanguages);
    if (newSelected.has(code)) {
      newSelected.delete(code);
    } else {
      newSelected.add(code);
    }
    setSelectedLanguages(newSelected);
  };

  const handleAdd = () => {
    if (selectedLanguages.size === 0) {
      toast({
        title: "No Languages Selected",
        description: "Please select at least one language to add.",
        variant: "destructive",
      });
      return;
    }

    const selectedNames = availableLanguages
      .filter(lang => selectedLanguages.has(lang.code))
      .map(lang => lang.name);

    if (onAdd) {
      onAdd(Array.from(selectedLanguages));
    }

    toast({
      title: "Languages Added",
      description: `${selectedLanguages.size} language(s) added to monitoring: ${selectedNames.join(", ")}`,
    });

    setSelectedLanguages(new Set());
    setSearchQuery("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-outfit text-2xl flex items-center gap-2">
            <Globe className="h-6 w-6 text-primary" />
            Add Languages
          </DialogTitle>
          <DialogDescription>
            Select languages to add to your monitoring coverage
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search languages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 border-border/50"
            />
          </div>

          {/* Selection Summary */}
          {selectedLanguages.size > 0 && (
            <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
              <p className="text-sm font-medium mb-2">
                {selectedLanguages.size} language(s) selected
              </p>
              <div className="flex flex-wrap gap-2">
                {Array.from(selectedLanguages).map(code => {
                  const lang = availableLanguages.find(l => l.code === code);
                  return lang ? (
                    <Badge key={code} variant="secondary">
                      {lang.name}
                    </Badge>
                  ) : null;
                })}
              </div>
            </div>
          )}

          {/* Language List */}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {filteredLanguages.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No languages found matching "{searchQuery}"</p>
              </div>
            ) : (
              filteredLanguages.map((language) => (
                <div
                  key={language.code}
                  onClick={() => toggleLanguage(language.code)}
                  className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedLanguages.has(language.code)
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50 bg-card"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <Checkbox
                      checked={selectedLanguages.has(language.code)}
                      onCheckedChange={() => toggleLanguage(language.code)}
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="font-semibold">{language.name}</h4>
                        <Badge variant="outline" className="text-xs">
                          {language.code.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{language.speakers} speakers</span>
                        <span>•</span>
                        <span>{language.region}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleAdd} className="gradient-primary">
            Add Selected ({selectedLanguages.size})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
