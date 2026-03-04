import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDomainStore } from "@/stores/domainStore";
import { useToast } from "@/hooks/use-toast";

const ReportIllustration = () => (
  <svg viewBox="0 0 220 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-44 h-44 drop-shadow-xl">
    <circle cx="110" cy="110" r="100" fill="#7c3aed" opacity="0.08" />
    <circle cx="110" cy="110" r="80" fill="#7c3aed" opacity="0.1" />
    <rect x="50" y="30" width="120" height="155" rx="10" fill="url(#docGrad)" />
    <path d="M 138 30 L 170 62 L 138 62 Z" fill="#5b21b6" />
    <path d="M 138 30 L 170 62 L 138 62 Z" fill="black" opacity="0.15" />
    <rect x="65" y="75" width="70" height="7" rx="3.5" fill="white" opacity="0.9" />
    <rect x="65" y="115" width="14" height="40" rx="3" fill="white" opacity="0.5" />
    <rect x="85" y="100" width="14" height="55" rx="3" fill="white" opacity="0.75" />
    <rect x="105" y="108" width="14" height="47" rx="3" fill="white" opacity="0.6" />
    <rect x="125" y="90" width="14" height="65" rx="3" fill="white" opacity="0.9" />
    <rect x="65" y="165" width="90" height="5" rx="2.5" fill="white" opacity="0.35" />
    <rect x="65" y="175" width="60" height="5" rx="2.5" fill="white" opacity="0.25" />
    <circle cx="44" cy="55" r="5" fill="#a78bfa" opacity="0.7" />
    <circle cx="180" cy="160" r="7" fill="#c4b5fd" opacity="0.5" />
    <circle cx="175" cy="45" r="4" fill="#ddd6fe" opacity="0.6" />
    <defs>
      <linearGradient id="docGrad" x1="50" y1="30" x2="170" y2="185" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#8b5cf6" />
        <stop offset="100%" stopColor="#6d28d9" />
      </linearGradient>
    </defs>
  </svg>
);

const SeoReports = () => {
  const { selectedDomain } = useDomainStore();
  const { toast } = useToast();

  const faviconUrl = selectedDomain?.url
    ? `https://www.google.com/s2/favicons?domain=${selectedDomain.url}&sz=64`
    : null;

  const handleLetsStart = () => {
    toast({
      title: "Coming Soon",
      description: "Organic reports functionality will be available shortly.",
    });
  };

  return (
    <div className="p-8 space-y-8 bg-background animate-fade-in">
      {/* Header — matches RankMax style */}
      <div className="flex items-center gap-3">
        {/* Favicon box */}
        <div className="w-11 h-11 rounded-lg border border-border bg-muted flex items-center justify-center flex-shrink-0 overflow-hidden">
          {faviconUrl ? (
            <img
              src={faviconUrl}
              alt={selectedDomain?.name}
              className="w-7 h-7 object-contain"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          ) : (
            <span className="text-xs font-bold text-muted-foreground">
              {selectedDomain?.name?.slice(0, 2).toUpperCase() ?? "—"}
            </span>
          )}
        </div>

        {/* Title + domain URL */}
        <div>
          <h1 className="text-xl font-bold leading-tight">Reports</h1>
          {selectedDomain?.url ? (
            <a
              href={selectedDomain.url.startsWith("http") ? selectedDomain.url : `https://${selectedDomain.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors mt-0.5"
            >
              {selectedDomain.url}
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : (
            <p className="text-sm text-muted-foreground mt-0.5">No domain selected</p>
          )}
        </div>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center min-h-[65vh] gap-8">
        <ReportIllustration />

        <div className="text-center space-y-3 max-w-md">
          <h2 className="text-2xl font-bold">Configure Report</h2>
          <p className="text-muted-foreground leading-relaxed">
            Customize and control reports. If you've added the report, please check
            back in 5 minutes.
          </p>
        </div>

        <Button
          className="gradient-primary shadow-md shadow-primary/20 px-10 h-11 text-base"
          onClick={handleLetsStart}
        >
          Let's start
        </Button>
      </div>
    </div>
  );
};

export default SeoReports;
