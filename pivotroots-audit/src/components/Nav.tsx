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

export function Nav({ ctaHref = "#audit" }: { ctaHref?: string }) {
  return (
    <nav className="nav">
      <div className="wrap">
        <Logo />
        <a className="btn ghost sm" href={ctaHref}>Get my free audit</a>
      </div>
    </nav>
  );
}
