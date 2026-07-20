import { Card } from "@/components/ui/card";

interface CountryShare {
  code: string;
  name: string;
  percentage: number;
  count: number;
  color: string;
}

interface MentionsByCountryProps {
  data?: CountryShare[];
  totalMentions?: number;
}

const DEFAULT_COUNTRIES: CountryShare[] = [
  { code: "IN", name: "IN", percentage: 79.1, count: 36300, color: "bg-[#7C3AED]" },
  { code: "US", name: "US", percentage: 9.6,  count: 4400,  color: "bg-[#10B981]" },
  { code: "UK", name: "UK", percentage: 1.7,  count: 800,   color: "bg-[#8B5CF6]" },
  { code: "Other", name: "Other", percentage: 9.5, count: 4400, color: "bg-[#F59E0B]" },
];

const fmt = (n: number): string => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
};

// Inline SVG Flag Component for cross-OS support (especially Windows)
const Flag = ({ code }: { code: string }) => {
  if (code === "IN") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 2" className="w-5 h-3.5 rounded-sm border border-border/40 flex-shrink-0 shadow-sm">
        <rect width="3" height="2" fill="#138808"/>
        <rect width="3" height="1.33" fill="#ffffff"/>
        <rect width="3" height="0.67" fill="#FF9933"/>
        <circle cx="1.5" cy="1" r="0.15" fill="#000080"/>
      </svg>
    );
  }
  if (code === "US") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 7410 3900" className="w-5 h-3.5 rounded-sm border border-border/40 flex-shrink-0 shadow-sm">
        <rect width="7410" height="3900" fill="#b22234"/>
        <path d="M0,300h7410M0,900h7410M0,1500h7410M0,2100h7410M0,2700h7410M0,3300h7410" stroke="#fff" stroke-width="300"/>
        <rect width="2964" height="2100" fill="#3c3b6e"/>
        <circle cx="400" cy="400" r="80" fill="#fff"/>
        <circle cx="900" cy="400" r="80" fill="#fff"/>
        <circle cx="1400" cy="400" r="80" fill="#fff"/>
        <circle cx="1900" cy="400" r="80" fill="#fff"/>
        <circle cx="2400" cy="400" r="80" fill="#fff"/>
        <circle cx="650" cy="800" r="80" fill="#fff"/>
        <circle cx="1150" cy="800" r="80" fill="#fff"/>
        <circle cx="1650" cy="800" r="80" fill="#fff"/>
        <circle cx="2150" cy="800" r="80" fill="#fff"/>
        <circle cx="400" cy="1200" r="80" fill="#fff"/>
        <circle cx="900" cy="1200" r="80" fill="#fff"/>
        <circle cx="1400" cy="1200" r="80" fill="#fff"/>
        <circle cx="1900" cy="1200" r="80" fill="#fff"/>
        <circle cx="2400" cy="1200" r="80" fill="#fff"/>
        <circle cx="650" cy="1600" r="80" fill="#fff"/>
        <circle cx="1150" cy="1600" r="80" fill="#fff"/>
        <circle cx="1650" cy="1600" r="80" fill="#fff"/>
        <circle cx="2150" cy="1600" r="80" fill="#fff"/>
      </svg>
    );
  }
  if (code === "UK" || code === "GB") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 30" className="w-5 h-3.5 rounded-sm border border-border/40 flex-shrink-0 shadow-sm">
        <clipPath id="t">
          <path d="M30,15 L0,0 v30 z M30,15 L60,0 v30 z M30,15 L0,0 h60 z M30,15 L0,30 h60 z"/>
        </clipPath>
        <path d="M0,0 v30 h60 v-30 z" fill="#012169"/>
        <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>
        <path d="M0,0 L60,30 M60,0 L0,30" stroke="#C8102E" stroke-width="4" clipPath="url(#t)"/>
        <path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>
        <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/>
      </svg>
    );
  }
  // Other / Global — inline SVG for the same reason the flags above are SVG:
  // the 🌐 emoji this replaced has no glyph in the default Windows UI font, so
  // it rendered as a question mark or an empty box. Every row that is not
  // IN/US/UK lands here, and region data is currently "GLOBAL" for everything,
  // so this is the icon nearly every row actually shows.
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-5 h-3.5 flex-shrink-0 opacity-60"
      role="img"
      aria-label="Global"
    >
      <title>Global</title>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
};

export const MentionsByCountry = ({ data, totalMentions = 0 }: MentionsByCountryProps) => {
  const countries = data && data.length ? data : DEFAULT_COUNTRIES;

  return (
    <Card className="p-6 shadow-elegant border border-border backdrop-blur-sm bg-card/80 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 gap-3 flex-wrap">
        <div className="flex items-center gap-1.5">
          <h3 className="text-base font-semibold font-inter">Mentions by Country</h3>
          <span
            title="Which countries your brand mentions came from, based on the country context each prompt was run for. 'Other' groups every country outside the top three."
            aria-label="Which countries your brand mentions came from, based on the country context each prompt was run for."
            className="inline-flex cursor-help"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-40 flex-shrink-0" role="img"><title>Which countries your brand mentions came from, based on the country context each prompt was run for.</title><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          </span>
        </div>
      </div>

      {/* Stacked bar */}
      <div className="h-5 w-full rounded-md overflow-hidden flex mb-6 bg-muted/40 border border-border/50">
        {countries.map((c) => {
          if (c.percentage <= 0) return null;
          return (
            <div
              key={c.code}
              className={`${c.color} h-full transition-all`}
              style={{ width: `${c.percentage}%` }}
              title={`${c.name}: ${c.percentage}% (${fmt(c.count)} mentions)`}
            />
          );
        })}
      </div>

      {/* Country list */}
      <div className="flex flex-col gap-4 flex-1">
        {/* Table header */}
        <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground pb-1 border-b border-border/40">
          <span>Country</span>
          <span className="flex items-center gap-1">
            Mentions
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 16l4 4 4-4"/><path d="M7 20V4"/><path d="M21 8l-4-4-4 4"/><path d="M17 4v16"/></svg>
          </span>
        </div>

        {countries.map((c) => (
          <div key={c.code} className="flex items-center justify-between py-0.5">
            <div className="flex items-center gap-3">
              <Flag code={c.code} />
              <span className="text-sm font-medium text-foreground">{c.name}</span>
            </div>
            <div className="flex items-center gap-6">
              <span className="text-sm text-muted-foreground w-12 text-right tabular-nums flex items-center justify-end gap-1.5 font-medium">
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: c.color.replace('bg-[', '').replace(']', '') }} />
                {c.percentage.toFixed(1)}%
              </span>
              <span className="text-sm font-semibold w-16 text-right text-primary tabular-nums">
                {fmt(c.count)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
