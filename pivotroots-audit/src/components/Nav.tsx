import { CONTACT_URL, LOGO_URL } from "@/lib/site";

export function Logo({ height = 24, tag = true }: { height?: number; tag?: boolean }) {
  return (
    <div className="logo">
      {/* eslint-disable-next-line @next/next/no-img-element -- remote SVG, no optimisation possible */}
      <img src={LOGO_URL} alt="PivotRoots" style={{ height }} />
      {tag && <small>A Havas Company</small>}
    </div>
  );
}

const LINKS = [
  { href: "#product", label: "Product" },
  { href: "#agent", label: "Ask Agent" },
  { href: "#seo", label: "SEO + Tech" },
  { href: "#how", label: "Free audit" },
  { href: "#modules", label: "All modules" },
  { href: "#faq", label: "FAQ" },
];

/**
 * Section links only make sense on the home page; pass links={false} elsewhere.
 * MotionRoot adds .scrolled once the page moves, for the hairline border.
 */
export function Nav({ ctaHref = "#audit", links = true, linkBase = "" }: { ctaHref?: string; links?: boolean; linkBase?: string }) {
  return (
    <header className="nav" id="nav">
      <div className="wrap">
        <a href={linkBase || "#audit"} aria-label="PivotRoots AI Visibility, home"><Logo /></a>
        {links && (
          <ul className="nav-links">
            {LINKS.map((l) => <li key={l.href}><a href={`${linkBase}${l.href}`}>{l.label}</a></li>)}
          </ul>
        )}
        <div className="nav-r">
          <a className="link" href={CONTACT_URL}>Talk to us</a>
          <a className="btn btn-dark btn-sm" href={ctaHref}>Get free audit</a>
        </div>
      </div>
    </header>
  );
}
