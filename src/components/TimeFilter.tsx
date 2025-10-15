import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface TimeFilterProps {
  selected: string;
  onSelect: (period: string) => void;
  periods?: { label: string; value: string }[];
}

export const TimeFilter = ({ 
  selected, 
  onSelect,
  periods = [
    { label: "90 days", value: "90" },
    { label: "30 days", value: "30" },
    { label: "7 days", value: "7" }
  ]
}: TimeFilterProps) => {
  return (
    <div className="flex items-center gap-2 p-1 bg-muted/50 rounded-xl border border-border/50">
      {periods.map((period) => (
        <Button
          key={period.value}
          variant={selected === period.value ? "default" : "ghost"}
          size="sm"
          onClick={() => onSelect(period.value)}
          className={cn(
            "transition-all rounded-lg font-medium",
            selected === period.value && "gradient-primary shadow-md shadow-primary/20"
          )}
        >
          {period.label}
        </Button>
      ))}
    </div>
  );
};
