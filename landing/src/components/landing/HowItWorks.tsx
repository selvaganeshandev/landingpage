import { ArrowRight } from "lucide-react";

const steps = [
  {
    step: "STEP ONE",
    title: "Add Your Brand",
    content: "Enter your brand name, website URL, confirm your niche, and review the prompts.",
    description: "Quick Setup!",
    visual: (
      <div className="space-y-2">
        <div className="bg-white rounded-lg shadow-sm border border-primary/20 p-3 w-32">
          <div className="h-2 w-16 bg-primary/30 rounded mb-2"></div>
          <div className="h-2 w-24 bg-primary/10 rounded"></div>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-primary/20 p-3 w-36 ml-4">
          <div className="h-2 w-20 bg-secondary/30 rounded mb-2"></div>
          <div className="h-2 w-28 bg-secondary/10 rounded"></div>
        </div>
      </div>
    ),
  },
  {
    step: "STEP TWO",
    title: "We Monitor AI",
    content: "Sit back—PromptMaxx handles the rest across all major LLMs automatically.",
    description: "Frequent Monitoring!",
    visual: (
      <div className="relative">
        <div className="bg-white rounded-lg shadow-sm border border-primary/20 p-3 w-40">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-4 h-4 rounded bg-primary/30"></div>
            <div className="h-2 w-16 bg-primary/20 rounded"></div>
            <div className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center ml-auto">
              <svg className="w-2.5 h-2.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-secondary/30"></div>
            <div className="h-2 w-20 bg-secondary/20 rounded"></div>
            <div className="w-4 h-4 rounded-full bg-primary/20 flex items-center justify-center ml-auto">
              <svg className="w-2.5 h-2.5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    ),
  },
  {
    step: "STEP THREE",
    title: "Get Insights",
    content: "See mentions, sentiment, citations, and misinformation alerts in your dashboard.",
    description: "Data-Driven!",
    visual: (
      <div className="bg-white rounded-lg shadow-sm border border-primary/20 p-3 w-36">
        <div className="flex items-end gap-1.5 h-16 justify-center">
          <div className="w-4 bg-primary/20 rounded-t h-6"></div>
          <div className="w-4 bg-primary/40 rounded-t h-10"></div>
          <div className="w-4 bg-primary/70 rounded-t h-14"></div>
          <div className="w-4 bg-primary rounded-t h-12"></div>
        </div>
      </div>
    ),
  },
  {
    step: "STEP FOUR",
    title: "Take Action",
    content: "Use AI-powered content tools to improve your visibility and outrank competitors.",
    description: "Grow Visibility!",
    visual: (
      <div className="space-y-2">
        <div className="bg-white rounded-lg shadow-sm border border-primary/20 px-3 py-1.5 text-xs text-gray-600 w-fit rotate-[-5deg]">
          Optimize content
        </div>
        <div className="bg-primary text-white rounded-lg shadow-sm px-3 py-1.5 text-xs w-fit ml-2">
          Boost AI visibility
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-primary/20 px-3 py-1.5 text-xs text-gray-600 w-fit rotate-[3deg] ml-4">
          Outrank competitors
        </div>
      </div>
    ),
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Section Header - matching other sections */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-sm font-medium text-primary uppercase tracking-wider mb-4">How It Works</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-gray-900">
            Get Started in Four Simple Steps
          </h2>
        </div>

        {/* Steps Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map((step, i) => (
            <div key={i} className="relative">
              <div className="bg-primary/5 rounded-3xl p-6 h-full border border-primary/10">
                {/* Step Label */}
                <p className="text-xs font-medium text-primary/60 uppercase tracking-wider mb-2">
                  {step.step}
                </p>

                {/* Title */}
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {step.title}
                </h3>

                {/* Content */}
                <p className="text-sm text-gray-600 mb-4">
                  {step.content}
                </p>

                {/* Visual Area */}
                <div className="h-40 flex items-center justify-center mb-4">
                  {step.visual}
                </div>

                {/* Arrow Button (between cards) */}
                {i < steps.length - 1 && (
                  <div className="absolute top-1/2 -right-2 z-10 hidden lg:flex">
                    <div className="w-8 h-8 bg-white rounded-full shadow-md border border-primary/20 flex items-center justify-center">
                      <ArrowRight className="w-4 h-4 text-primary" />
                    </div>
                  </div>
                )}

                {/* Bottom Tag */}
                <div className="flex justify-center">
                  <span className="inline-flex items-center px-4 py-2 bg-white rounded-full text-sm font-medium text-primary shadow-sm border border-primary/20">
                    {step.description}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
