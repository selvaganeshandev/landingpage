import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: React.ReactNode;
  trend?: "up" | "down";
}

export const MetricCard = ({ title, value, change, icon, trend }: MetricCardProps) => {
  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground font-medium">{title}</p>
          <h3 className="text-3xl font-bold tracking-tight">{value}</h3>
          {change !== undefined && (
            <div className="flex items-center gap-1 text-sm">
              {trend === "up" ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
              <span
                className={cn(
                  "font-medium",
                  trend === "up" ? "text-success" : "text-destructive"
                )}
              >
                {change > 0 ? "+" : ""}
                {change}%
              </span>
              <span className="text-muted-foreground">vs last period</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-3 rounded-xl bg-gradient-to-br from-primary to-secondary text-primary-foreground">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};
