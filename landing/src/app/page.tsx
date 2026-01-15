import {
  Header,
  Hero,
  LogoCloud,
  Features,
  HowItWorks,
  SocialProof,
  Statistics,
  Pricing,
  CTA,
  FAQ,
  Footer,
} from "@/components/landing";

export default function Home() {
  return (
    <main className="min-h-screen">
      <Header />
      <Hero />
      <LogoCloud />
      <Features />
      <HowItWorks />
      <SocialProof />
      <Statistics />
      <Pricing />
      <CTA />
      <FAQ />
      <Footer />
    </main>
  );
}
