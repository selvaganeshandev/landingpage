import { LOGO_URL } from "@/lib/site";

export function Logo({ height = 26 }: { height?: number }) {
  return (
    <div className="logo">
      {/* eslint-disable-next-line @next/next/no-img-element -- remote SVG, no optimisation possible */}
      <img src={LOGO_URL} alt="PivotRoots" style={{ height }} />
      <small>A Havas Company</small>
    </div>
  );
}

const LINKS = [
  { href: "#whats-in-it", label: "What's in it" },
  { href: "#how", label: "How it works" },
  { href: "#sample", label: "Sample" },
  { href: "#platform", label: "Beyond the audit" },
  { href: "#faq", label: "FAQ" },
];

/** Section links only make sense on the home page; the report route passes links={false}. */
export function Nav({ ctaHref = "#audit", links = true }: { ctaHref?: string; links?: boolean }) {
  return (
    <nav className="nav">
      <div className="wrap">
        <Logo />
        {links && (
          <ul className="nav-links">
            {LINKS.map((l) => <li key={l.href}><a href={l.href}>{l.label}</a></li>)}
          </ul>
        )}
        <a className="btn ghost sm" href={ctaHref}>Get my free audit</a>
      </div>
    </nav>
  );
}
