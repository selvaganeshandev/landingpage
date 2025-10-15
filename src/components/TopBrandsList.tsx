import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2 } from "lucide-react";

interface Brand {
  name: string;
  url: string;
  mentions: number;
  percentage: number;
  isYou?: boolean;
}

interface TopBrandsListProps {
  brands: Brand[];
  totalMentions: number;
}

export const TopBrandsList = ({ brands, totalMentions }: TopBrandsListProps) => {
  return (
    <Card className="p-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Top Brands by Visibility</h3>
          <div className="text-right">
            <p className="text-3xl font-bold">{totalMentions}</p>
            <p className="text-xs text-muted-foreground">total mentions</p>
          </div>
        </div>

        <div className="space-y-3">
          {brands.map((brand, idx) => (
            <div
              key={brand.name}
              className={`p-4 rounded-lg border transition-all hover:shadow-md ${
                brand.isYou ? "border-primary bg-primary/5" : "border-border"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary text-primary-foreground flex items-center justify-center flex-shrink-0">
                  <Building2 className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold truncate">{brand.name}</h4>
                    {brand.isYou && (
                      <Badge variant="default" className="text-xs">You</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{brand.url}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xl font-bold">{brand.mentions}</p>
                  <p className="text-xs text-muted-foreground">{brand.percentage}%</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
};
