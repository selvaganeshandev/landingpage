import { AlertTriangle, TrendingUp, Link2, FileEdit, Globe } from "lucide-react";

export function Features() {
  return (
    <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-sm font-medium text-primary uppercase tracking-wider mb-4">Why PromptMaxx</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-gray-900 mb-6">
            Features you won&apos;t find anywhere else
          </h2>
          <p className="text-lg text-gray-600">
            We built what other tools forgot. These capabilities exist only in PromptMaxx.
          </p>
        </div>

        {/* Top Row - 3 Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-6">
          {/* Card 1: Misinformation Detection */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-48 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[220px] space-y-2">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                        <AlertTriangle className="w-4 h-4 text-red-500" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-900">AI Said Wrong Price</p>
                        <p className="text-[10px] text-gray-500">&quot;$99/mo&quot; → Actually $49/mo</p>
                      </div>
                    </div>
                    <div className="mt-2 h-1.5 bg-red-100 rounded-full overflow-hidden">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: '85%' }} />
                    </div>
                  </div>
                  <div className="bg-primary/10 rounded-lg p-2 border border-primary/20">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                        <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-xs font-medium text-primary">Alert Sent to Team</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Catch AI Lies Instantly</h3>
            <p className="text-gray-600">
              AI makes mistakes about your brand. Get real-time alerts when platforms spread wrong pricing, outdated features, or inaccurate info.
            </p>
          </div>

          {/* Card 2: Traffic Attribution */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-48 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[200px]">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="w-4 h-4 text-primary" />
                      <span className="text-xs font-medium text-gray-700">AI Traffic Sources</span>
                    </div>
                    <div className="text-center mb-3">
                      <span className="text-2xl font-bold text-primary">12,847</span>
                      <p className="text-xs text-green-600 font-medium">+89% visitors from AI</p>
                    </div>
                    <div className="space-y-1.5">
                      {[
                        { name: "ChatGPT", value: "5,420" },
                        { name: "Perplexity", value: "4,127" },
                        { name: "Claude", value: "3,300" },
                      ].map((item, i) => (
                        <div key={i} className="flex justify-between text-xs">
                          <span className="text-gray-500">{item.name}</span>
                          <span className="font-medium text-gray-900">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Track Traffic from AI</h3>
            <p className="text-gray-600">
              See exactly how many visitors come from AI platforms. Know which AI—ChatGPT, Claude, or Perplexity—sends you the most traffic.
            </p>
          </div>

          {/* Card 3: Citation Tracking */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-48 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[220px] space-y-2">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Link2 className="w-4 h-4 text-primary" />
                      <span className="text-xs font-medium text-gray-700">Sources AI Cites</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="text-[10px] text-gray-600 truncate">yourbrand.com/pricing</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="text-[10px] text-gray-600 truncate">yourbrand.com/features</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                        <span className="text-[10px] text-gray-600 truncate">competitor.com/compare</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-amber-50 rounded-lg p-2 border border-amber-200">
                    <span className="text-xs font-medium text-amber-700">1 competitor source detected</span>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">See What Sources AI Trusts</h3>
            <p className="text-gray-600">
              Know which URLs AI platforms cite when recommending brands. Track if they&apos;re using your content—or your competitor&apos;s.
            </p>
          </div>
        </div>

        {/* Bottom Row - 2 Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Card 4: AI Content Editor */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-56 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[300px]">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileEdit className="w-4 h-4 text-primary" />
                        <span className="text-xs font-medium text-gray-700">AI Content Editor</span>
                      </div>
                      <div className="flex items-center gap-1 bg-green-100 px-2 py-0.5 rounded-full">
                        <span className="text-[10px] font-medium text-green-700">Score: 94</span>
                      </div>
                    </div>
                    <div className="space-y-2 mb-3">
                      <div className="h-2 bg-gray-200 rounded w-full"></div>
                      <div className="h-2 bg-gray-200 rounded w-4/5"></div>
                      <div className="h-2 bg-primary/30 rounded w-3/5"></div>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-[10px] px-2 py-1 bg-primary/10 text-primary rounded-full">AI Rewrite</span>
                      <span className="text-[10px] px-2 py-1 bg-primary/10 text-primary rounded-full">Link Map</span>
                      <span className="text-[10px] px-2 py-1 bg-primary/10 text-primary rounded-full">Outline</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Content That Ranks in AI</h3>
            <p className="text-gray-600">
              Create content optimized for AI recommendations, not just Google. AI-powered rewriting, internal link mapping, and visibility scoring built-in.
            </p>
          </div>

          {/* Card 5: Multilingual Monitoring */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-56 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[300px]">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Globe className="w-5 h-5 text-primary" />
                      <span className="text-sm font-medium text-gray-900">Global AI Monitoring</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { lang: "EN", flag: "🇺🇸", sentiment: "positive" },
                        { lang: "DE", flag: "🇩🇪", sentiment: "positive" },
                        { lang: "FR", flag: "🇫🇷", sentiment: "neutral" },
                        { lang: "ES", flag: "🇪🇸", sentiment: "positive" },
                        { lang: "JP", flag: "🇯🇵", sentiment: "positive" },
                        { lang: "BR", flag: "🇧🇷", sentiment: "negative" },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center gap-1.5 bg-gray-50 rounded-lg p-2">
                          <span className="text-sm">{item.flag}</span>
                          <span className="text-[10px] font-medium text-gray-700">{item.lang}</span>
                          <div className={`w-1.5 h-1.5 rounded-full ml-auto ${
                            item.sentiment === 'positive' ? 'bg-green-500' :
                            item.sentiment === 'negative' ? 'bg-red-500' : 'bg-yellow-500'
                          }`}></div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Monitor Your Brand Globally</h3>
            <p className="text-gray-600">
              AI speaks every language. Track how AI describes your brand in 50+ languages. Catch regional misinformation before it spreads.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
