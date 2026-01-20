"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";

const plans = [
  {
    name: "Starter",
    description: "Essentials for small businesses",
    monthlyPrice: 29,
    originalPrice: 49,
    features: [
      "1 user",
      "1 domain",
      "3 AI platforms",
      "25 prompts/month",
      "1 competitor",
      "5 AI articles/month",
    ],
    additionalFeatures: [],
    extraFeatures: [],
  },
  {
    name: "Growth",
    description: "Perfect for growing startups and SMBs",
    monthlyPrice: 39,
    originalPrice: 66,
    features: [
      "3 users",
      "3 domains",
      "All 5 AI platforms",
      "50 prompts/month",
      "3 competitors",
      "15 AI articles/month",
    ],
    additionalFeatures: [
      "Citation tracking",
      "Content Editor",
    ],
    extraFeatures: [],
    popular: true,
  },
  {
    name: "Pro",
    description: "For SMEs and Agencies",
    monthlyPrice: 129,
    originalPrice: 219,
    features: [
      "10 users",
      "Unlimited domains",
      "All 5 AI platforms",
      "200 prompts/month",
      "5 competitors",
      "50 AI articles/month",
    ],
    additionalFeatures: [
      "Citation tracking",
      "Content Editor + AI Rewrite",
    ],
    extraFeatures: [],
  },
];

export function Pricing() {
  const [isYearly, setIsYearly] = useState(false);

  const getPrice = (monthlyPrice: number) => {
    if (isYearly) {
      return Math.round(monthlyPrice * 0.85);
    }
    return monthlyPrice;
  };

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <p className="text-sm font-medium text-primary uppercase tracking-wider mb-4">Pricing</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-gray-900 mb-3">
            Choose your plan
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Unlock your full potential by selecting the plan that best aligns with your specific business requirements.
          </p>
        </div>

        {/* Toggle */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center bg-gray-100 rounded-full p-1">
            <button
              onClick={() => setIsYearly(false)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all cursor-pointer ${
                !isYearly
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setIsYearly(true)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all cursor-pointer flex items-center gap-2 ${
                isYearly
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Yearly
              <span className="text-primary text-xs font-semibold">-15%</span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan, i) => (
            <div
              key={i}
              className={`bg-white rounded-2xl p-6 border ${
                plan.popular
                  ? "border-primary shadow-lg shadow-primary/10"
                  : "border-gray-200 shadow-sm"
              } relative`}
            >
              {plan.popular && (
                <span className="absolute -top-3 left-24 bg-amber-400 text-gray-900 text-xs font-medium px-2 py-1 rounded">
                  79% pick this option
                </span>
              )}

              {/* Plan Name */}
              <h3 className="text-xl font-semibold text-gray-900 mb-1">
                {plan.name}
              </h3>
              <p className="text-gray-500 text-sm mb-4">
                {plan.description}
              </p>

              {/* Price */}
              <div className="mb-4 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-gray-900">
                  ${getPrice(plan.monthlyPrice)}
                </span>
                <span className="text-gray-500">/mo</span>
                <span className="text-gray-400 line-through text-sm">
                  ${plan.originalPrice}/mo
                </span>
              </div>

              {/* CTA Button */}
              <a href="https://app.promptmaxx.co/" className="block mb-6">
                <Button
                  className={`w-full rounded-full h-11 text-sm font-medium cursor-pointer ${
                    plan.popular
                      ? "bg-primary text-white hover:bg-primary/90"
                      : "bg-gray-900 text-white hover:bg-gray-800"
                  }`}
                >
                  Get Started
                </Button>
              </a>

              {/* Features */}
              <div className="space-y-3">
                {plan.features.map((feature, j) => (
                  <div key={j} className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Check className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-gray-700 text-sm">{feature}</span>
                  </div>
                ))}

                {/* Additional Features Divider */}
                {plan.additionalFeatures.length > 0 && (
                  <>
                    <div className="flex items-center gap-3 py-1">
                      <div className="flex-1 h-px bg-gray-200"></div>
                      <div className="w-5 h-5 rounded border border-gray-200 flex items-center justify-center">
                        <span className="text-gray-400 text-[10px]">+</span>
                      </div>
                      <div className="flex-1 h-px bg-gray-200"></div>
                    </div>
                    {plan.additionalFeatures.map((feature, j) => (
                      <div key={j} className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <Check className="w-3 h-3 text-primary" />
                        </div>
                        <span className="text-gray-700 text-sm">{feature}</span>
                      </div>
                    ))}
                  </>
                )}

                {/* Extra Features Divider */}
                {plan.extraFeatures.length > 0 && (
                  <>
                    <div className="flex items-center gap-3 py-1">
                      <div className="flex-1 h-px bg-gray-200"></div>
                      <div className="w-5 h-5 rounded border border-gray-200 flex items-center justify-center">
                        <span className="text-gray-400 text-[10px]">+</span>
                      </div>
                      <div className="flex-1 h-px bg-gray-200"></div>
                    </div>
                    {plan.extraFeatures.map((feature, j) => (
                      <div key={j} className="flex items-center gap-3">
                        <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <Check className="w-3 h-3 text-primary" />
                        </div>
                        <span className="text-gray-700 text-sm">{feature}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
