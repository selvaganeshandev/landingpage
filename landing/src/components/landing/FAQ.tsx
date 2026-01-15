"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    question: "What AI platforms does PromptMaxx monitor?",
    answer: "PromptMaxx monitors all major AI platforms including ChatGPT (GPT-4, GPT-4o), Claude (Anthropic), Google Gemini, Perplexity AI, and Grok (xAI). We continuously add support for new platforms as they emerge.",
  },
  {
    question: "How does PromptMaxx track AI mentions?",
    answer: "We use a combination of automated queries and AI-powered analysis to track how different AI platforms respond to questions about your brand, products, and industry. Our system runs thousands of relevant prompts daily and analyzes the responses for mentions, sentiment, and accuracy.",
  },
  {
    question: "Can I track my competitors as well?",
    answer: "Yes! PromptMaxx allows you to track unlimited competitors. You can compare your brand's share of voice, sentiment, and mention frequency against competitors to understand your position in the AI search landscape.",
  },
  {
    question: "What kind of reports can I generate?",
    answer: "You can generate various reports including Executive Dashboards, Detailed Analytics, Content Strategy reports, and Competitor Analysis. All reports can be exported as PDF or Excel files and can be scheduled for automatic delivery.",
  },
  {
    question: "How quickly can I get started?",
    answer: "You can get started in less than 5 minutes. Simply sign up, add your brand and competitors, and PromptMaxx will begin monitoring immediately. Initial insights are typically available within 24 hours.",
  },
  {
    question: "Is there a free trial available?",
    answer: "Yes, we offer a 14-day free trial with full access to all features. No credit card is required to start your trial. You can upgrade to a paid plan at any time during or after the trial.",
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
                  <AccordionTrigger className="text-left text-gray-900 hover:text-primary py-5 text-sm font-medium [&[data-state=open]]:text-primary">
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
