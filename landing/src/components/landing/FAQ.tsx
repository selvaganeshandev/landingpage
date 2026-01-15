"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "How does PromptMaxx detect misinformation about my brand?",
    answer: "We automatically compare what AI platforms say about your brand against your actual website content using semantic analysis. When ChatGPT, Claude, or other AIs give wrong pricing, outdated features, or inaccurate information, you get instant alerts with the exact discrepancy highlighted.",
  },
  {
    question: "How do you track traffic coming from AI platforms?",
    answer: "PromptMaxx integrates with Google Analytics and Google Search Console to identify visitors referred from AI platforms like ChatGPT, Claude, Perplexity, and Gemini. You'll see exactly how many visitors each AI sends to your site and which pages they land on.",
  },
  {
    question: "What is citation tracking and why does it matter?",
    answer: "When AI platforms recommend brands, they often cite sources. Citation tracking shows you which URLs the AI is pulling information from—whether it's your website or a competitor's. This helps you understand why AI might be giving certain answers and what content you need to optimize.",
  },
  {
    question: "Which AI platforms does PromptMaxx monitor?",
    answer: "We monitor all major AI platforms including ChatGPT (GPT-4, GPT-4o), Claude (Anthropic), Google Gemini, Perplexity AI, and Grok (xAI). Our system runs relevant prompts frequently and analyzes responses for mentions, sentiment, and accuracy.",
  },
  {
    question: "Can I monitor my brand in multiple languages?",
    answer: "Yes! PromptMaxx supports 50+ languages. You can track how AI platforms describe your brand in different regions and languages, catch regional misinformation, and understand your global AI presence—all from one dashboard.",
  },
  {
    question: "How does the AI Content Editor help with AI visibility?",
    answer: "Our content editor is built specifically for AI optimization, not just SEO. It includes AI-powered rewriting, content scoring for AI visibility, internal link mapping, and two-phase generation (outline then full article) to create content that AI platforms are more likely to cite and recommend.",
  },
];

export function FAQ() {
  return (
    <section id="faq" className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-5xl mx-auto">
        {/* Two Column Layout */}
        <div className="grid lg:grid-cols-5 gap-12">
          {/* Left Column - Header */}
          <div className="lg:col-span-2">
            <div className="lg:sticky lg:top-24">
              <p className="text-sm font-medium text-primary uppercase tracking-wider mb-3">FAQ</p>
              <h2 className="text-2xl sm:text-3xl font-semibold text-gray-900 mb-4">
                Frequently asked questions
              </h2>
              <p className="text-gray-600 mb-6">
                Everything you need to know about PromptMaxx. Can&apos;t find what you&apos;re looking for?
              </p>
              <a
                href="mailto:support@promptmaxx.com"
                className="inline-flex items-center text-sm font-medium text-primary hover:text-primary/80 transition-colors"
              >
                Contact support
                <svg className="ml-1 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </a>
            </div>
          </div>

          {/* Right Column - Accordion */}
          <div className="lg:col-span-3">
            <Accordion type="single" collapsible className="space-y-3">
              {faqs.map((faq, i) => (
                <AccordionItem
                  key={i}
                  value={`item-${i}`}
                  className="bg-white rounded-xl border border-gray-200 px-6 data-[state=open]:shadow-sm transition-shadow"
                >
                  <AccordionTrigger className="text-left text-gray-900 hover:no-underline py-5 text-sm font-medium cursor-pointer [&[data-state=open]]:text-primary">
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-gray-600 text-sm pb-5 leading-relaxed">
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </div>
    </section>
  );
}
