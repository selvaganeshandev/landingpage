import { Nav } from "@/components/Nav";
import { Hero, type HeroParams } from "@/components/Hero";
import { Faq, FinalCta, HowItWorks, Sample, WhatYouGet, WhyUs } from "@/components/Sections";
import { Platform } from "@/components/Platform";
import { Footer } from "@/components/Footer";

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) || "";

export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  // Prefill from email-blast links, resolved on the server so the form is
  // filled on first paint. Values are capped; the form re-validates them.
  const q = await searchParams;
  const params: HeroParams = {
    d: first(q.d).slice(0, 253), e: first(q.e).slice(0, 254), b: first(q.b).slice(0, 255),
    c: first(q.c).slice(0, 64), m: first(q.m).slice(0, 2),
  };
  return (
    <>
      <Nav />
      <Hero params={params} />
      <WhatYouGet />
      <HowItWorks />
      <Sample />
      <Platform />
      <WhyUs />
      <Faq />
      <FinalCta />
      <Footer />
    </>
  );
}
