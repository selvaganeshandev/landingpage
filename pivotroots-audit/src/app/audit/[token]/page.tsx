/**
 * /audit/<token> — the same page, resumed on an audit that is already running
 * or finished. This is the link a visitor bookmarks or forwards; it renders the
 * live panel in place of the form. The token is validated by the API route.
 */
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { Agent, Faq, FinalCta, HowFree, Modules, Product, Seo, Shift, Trust } from "@/components/Sections";
import { Footer } from "@/components/Footer";
import { MotionRoot } from "@/components/MotionRoot";
import { HOME_AUDIT_HREF } from "@/lib/site";

export const metadata: Metadata = {
  title: "Your AI Visibility Audit · PivotRoots",
  robots: { index: false, follow: false },
};

export default async function AuditPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return (
    <>
      <Nav ctaHref={HOME_AUDIT_HREF} linkBase={HOME_AUDIT_HREF.replace("#audit", "")} />
      <Hero initialToken={token} />
      <Trust />
      <Shift />
      <Product />
      <Agent />
      <Seo />
      <HowFree />
      <Modules />
      <Faq />
      <FinalCta ctaHref={HOME_AUDIT_HREF} />
      <Footer />
      <MotionRoot />
    </>
  );
}
