/**
 * /audit/<token> — the same page, resumed on an audit that is already running
 * or finished. This is the link a visitor bookmarks or forwards; it renders the
 * live panel in place of the form. The token is validated by the API route.
 */
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { Faq, FinalCta, HowItWorks, Sample, WhatYouGet, WhyUs } from "@/components/Sections";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Your AI Visibility Audit · PivotRoots",
  robots: { index: false, follow: false },
};

export default async function AuditPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return (
    <>
      <Nav ctaHref="/#audit" />
      <Hero initialToken={token} />
      <WhatYouGet />
      <HowItWorks />
      <Sample />
      <WhyUs ctaHref="/#audit" />
      <Faq />
      <FinalCta ctaHref="/#audit" />
      <Footer />
    </>
  );
}
