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
  iconColor?: string;
}

export const MetricCard = ({ title, value, change, icon, trend, onClick, href, iconColor = "primary" }: MetricCardProps) => {
  const navigate = useNavigate();

  // Clone the icon element and add the appropriate color class
  const themedIcon = icon && isValidElement(icon)
    ? cloneElement(icon as React.ReactElement, {
        className: cn((icon as React.ReactElement).props.className, `text-${iconColor}`, "h-6 w-6")
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
        "p-6 transition-all duration-300 border border-border hover:border-primary",
        isClickable && "cursor-pointer"
      )}
      onClick={isClickable ? handleClick : undefined}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-sm text-muted-foreground font-medium">{title}</p>
          <h3 className="text-3xl font-bold mt-3">{value}</h3>
        </div>
        {icon && (
          <div className={`p-3 rounded-xl bg-${iconColor}/10`}>
            {themedIcon}
          </div>
        )}
      </div>
      {change !== undefined && change !== 0 && (
        <div className="flex items-center gap-2 text-sm">
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
    </Card>
  );
};
