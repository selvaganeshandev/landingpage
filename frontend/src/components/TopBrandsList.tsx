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
  // Handle empty data
  if (!brands || brands.length === 0) {
    return (
      <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
        <div className="space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-border/50">
            <h3 className="text-lg font-semibold font-inter">Top Brands by Visibility</h3>
            <div className="text-right">
              <p className="text-3xl font-bold font-outfit gradient-primary bg-clip-text text-transparent">0</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">total mentions</p>
            </div>
          </div>
          <div className="flex items-center justify-center py-12">
            <p className="text-sm text-muted-foreground">No brands data available yet.</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80">
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-border/50">
          <h3 className="text-lg font-semibold font-inter">Top Brands by Visibility</h3>
          <div className="text-right">
            <p className="text-3xl font-bold font-inter gradient-primary bg-clip-text text-transparent">{totalMentions}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">total mentions</p>
          </div>
        </div>

        <div className="space-y-3">
          {brands.map((brand, idx) => (
            <div
              key={brand.name}
              className={`group p-4 rounded-xl border transition-all duration-300 hover:shadow-lg hover:scale-[1.02] ${
                brand.isYou 
                  ? "border-primary/30 bg-gradient-to-br from-primary/5 to-secondary/5 shadow-glow" 
                  : "border-border/50 hover:border-primary/20 bg-card/50"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl gradient-primary shadow-md flex items-center justify-center flex-shrink-0 group-hover:shadow-glow transition-all">
                  <Building2 className="h-5 w-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold truncate font-inter mb-1">{brand.name}</h4>
                  <p className="text-xs text-muted-foreground truncate">{brand.url}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xl font-bold font-inter">{brand.mentions}</p>
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
