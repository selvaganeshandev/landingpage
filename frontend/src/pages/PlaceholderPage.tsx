import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
  features?: string[];
}

const PlaceholderPage = ({ title, description, features = [] }: PlaceholderPageProps) => {
  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
        <p className="text-muted-foreground mt-2">{description}</p>
      </div>

      <Card className="p-12 text-center">
        <div className="flex flex-col items-center gap-6 max-w-2xl mx-auto">
          <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
            <Construction className="h-10 w-10 text-primary" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold">Coming Soon</h2>
            <p className="text-muted-foreground">
              This feature is currently under development and will be available soon.
            </p>
          </div>
          {features.length > 0 && (
            <div className="text-left w-full space-y-2">
              <p className="font-medium text-sm text-muted-foreground">Planned Features:</p>
              <ul className="space-y-1">
                {features.map((feature, idx) => (
                  <li key={idx} className="text-sm flex items-start gap-2">
                    <span className="text-primary">•</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Button>Request Early Access</Button>
        </div>
      </Card>
    </div>
  );
};

export default PlaceholderPage;
