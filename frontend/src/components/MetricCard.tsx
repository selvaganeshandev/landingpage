import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { cloneElement, isValidElement } from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: React.ReactNode;
  trend?: "up" | "down";
}

export const MetricCard = ({ title, value, change, icon, trend }: MetricCardProps) => {
  // Clone the icon element and add white text color class
  const whiteIcon = icon && isValidElement(icon)
    ? cloneElement(icon as React.ReactElement, {
        className: cn((icon as React.ReactElement).props.className, "text-white")
      })
    : icon;

  return (
    <Card className="p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3 flex-1 min-w-0">
          <div className="h-10">
            <p className="text-sm text-muted-foreground font-medium uppercase tracking-wider leading-tight">{title}</p>
          </div>
          <h3 className="text-4xl font-bold tracking-tight font-outfit">{value}</h3>
          {change !== undefined && (
            <div className="flex items-center gap-2 text-sm whitespace-nowrap">
              {trend === "up" ? (
                <TrendingUp className="h-4 w-4 text-success" />
              ) : (
                <TrendingDown className="h-4 w-4 text-destructive" />
              )}
              <span
                className={cn(
                  "font-semibold",
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
          <div className="p-3 rounded-2xl gradient-primary shadow-glow flex-shrink-0">
            {whiteIcon}
          </div>
        )}
      </div>
    </Card>
  );
};
