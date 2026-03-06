import { FileBarChart2 } from "lucide-react";

const SeoReports = () => {
  return (
    <div className="p-8 bg-background animate-fade-in">
      <div className="flex flex-col items-center justify-center min-h-[75vh] text-center">
        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mb-6">
          <FileBarChart2 className="h-10 w-10 text-primary" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Organic Reports</h2>
        <p className="text-muted-foreground max-w-sm">
          We're working on something great. This feature will be available soon.
        </p>
      </div>
    </div>
  );
};

export default SeoReports;
