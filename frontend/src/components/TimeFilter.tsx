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
    { label: "90d", value: "90" },
    { label: "30d", value: "30" },
    { label: "7d", value: "7" }
  ]
}: TimeFilterProps) => {
  return (
    <div className="flex items-center gap-1 p-1 bg-muted/50 rounded-lg border border-border">
      {periods.map((period) => (
        <Button
          key={period.value}
          variant={selected === period.value ? "default" : "ghost"}
          size="sm"
          onClick={() => onSelect(period.value)}
          className={cn(
            "transition-all rounded-md font-medium h-8 px-3 text-xs",
            selected === period.value && "gradient-primary shadow-md shadow-primary/20"
          )}
        >
          {period.label}
        </Button>
      ))}
    </div>
  );
};
