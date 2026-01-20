import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function CTA() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-900 relative overflow-hidden">
      {/* Background gradient accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-secondary/20 opacity-50"></div>

      <div className="max-w-4xl mx-auto text-center relative z-10">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-full border border-gray-700 mb-8">
          <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
          <span className="text-sm text-gray-300">Start monitoring in minutes</span>
        </div>

        {/* Headline */}
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-white mb-6">
          Find out what AI says
          <br />
          about your brand
        </h2>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-10">
          Join hundreds of marketing teams already using PromptMaxx to monitor and optimize their brand presence across AI platforms.
        </p>

        {/* CTA Button */}
        <div className="flex items-center justify-center">
          <a href="https://app.promptmaxx.co/">
            <Button className="bg-primary text-white hover:bg-primary/90 rounded-full h-12 !px-8 text-base font-medium cursor-pointer">
              <span>Start free trial</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </a>
        </div>

        {/* Trust Indicators */}
        <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-gray-500">
          <span className="flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            No credit card required
          </span>
          <span className="flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            14-day free trial
          </span>
          <span className="flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Cancel anytime
          </span>
        </div>
      </div>
    </section>
  );
}
