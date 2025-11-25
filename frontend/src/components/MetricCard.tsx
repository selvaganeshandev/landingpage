import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { cloneElement, isValidElement } from "react";
import { useNavigate } from "react-router-dom";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon?: React.ReactNode;
  trend?: "up" | "down";
  onClick?: () => void;
  href?: string;
}

export const MetricCard = ({ title, value, change, icon, trend, onClick, href }: MetricCardProps) => {
  const navigate = useNavigate();
  
  // Clone the icon element and add primary text color class
  const themedIcon = icon && isValidElement(icon)
    ? cloneElement(icon as React.ReactElement, {
        className: cn((icon as React.ReactElement).props.className, "text-primary")
      })
    : icon;

  const handleClick = () => {
    if (href) {
      navigate(href);
    } else if (onClick) {
      onClick();
    }
  };

  const isClickable = !!onClick || !!href;

  return (
    <Card 
      className={cn(
        "p-6 transition-all duration-300 border border-border hover:border-primary backdrop-blur-sm bg-card/80",
        isClickable && "cursor-pointer"
      )}
      onClick={isClickable ? handleClick : undefined}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-3 flex-1 min-w-0">
          <div className="h-10">
            <p className="text-sm text-muted-foreground font-medium uppercase tracking-wider leading-tight">{title}</p>
          </div>
          <h3 className="text-4xl font-bold tracking-tight font-inter">{value}</h3>
          {change !== undefined && change !== 0 && (
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
          <div className="flex-shrink-0">
            {themedIcon}
          </div>
        )}
      </div>
    </Card>
  );
};
