import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import Image from "next/image";
import { AuditForm } from "./AuditForm";

export function Hero() {
  return (
    <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Badge */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/5 rounded-full border border-primary/20">
            <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
            <span className="text-sm text-gray-600">GEO Monitoring & AI Brand Visibility Platform</span>
          </div>
        </div>

        {/* Headline */}
        <div className="text-center max-w-4xl mx-auto mb-8">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-semibold text-gray-900 leading-tight mb-6">
            See How AI Represents
            <br />
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">Your Brand Online</span>
          </h1>
          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
            Monitor your brand presence across ChatGPT, Claude, Gemini, and Perplexity.
            Track AI mentions, optimize for generative engine visibility, and protect your brand reputation in the age of AI search.
          </p>
        </div>

        {/* Free audit — the lead-capture form. The trial CTA stays as the
            secondary action underneath it. */}
        <div className="mb-6">
          <AuditForm />
        </div>
        <div className="flex items-center justify-center mb-16">
          <a href="https://app.promptmaxx.co/">
            <Button variant="ghost" className="rounded-full h-10 !px-6 text-sm font-medium text-gray-600 hover:text-gray-900 cursor-pointer">
              <span>or start a free trial</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </a>
        </div>

        {/* Product Screenshot */}
        <div className="relative max-w-6xl mx-auto">
          <div className="bg-gradient-to-b from-gray-50 to-white rounded-2xl p-2 shadow-2xl shadow-gray-200/50 border border-gray-200">
            <div className="bg-white rounded-xl overflow-hidden">
              {/* Browser Chrome */}
              <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-100">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                  <div className="w-3 h-3 rounded-full bg-green-400"></div>
                </div>
                <div className="flex-1 flex justify-center">
                  <div className="px-4 py-1 bg-white rounded-md text-xs text-gray-400 border border-gray-200">
                    app.promptmaxx.com
                  </div>
                </div>
              </div>
              {/* Dashboard Preview */}
              <div className="relative">
                <Image
                  src="/dashboard-preview.png"
                  alt="PromptMaxx Dashboard - AI Search Analytics"
                  width={1920}
                  height={1080}
                  className="w-full h-auto"
                  priority
                />
              </div>
            </div>
          </div>

          {/* Decorative Elements */}
          <div className="absolute -z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-gradient-to-r from-primary/10 via-secondary/10 to-primary/5 rounded-full blur-3xl opacity-50"></div>
        </div>
      </div>
    </section>
  );
}
