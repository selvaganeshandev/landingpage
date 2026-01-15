import { Eye, BarChart3, AlertTriangle, Users, FileText } from "lucide-react";

export function Features() {
  return (
    <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <p className="text-sm font-medium text-primary uppercase tracking-wider mb-4">Features</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-gray-900 mb-6">
            Everything you need to dominate AI search
          </h2>
          <p className="text-lg text-gray-600">
            Monitor, analyze, and optimize your brand&apos;s presence across all major AI platforms.
          </p>
        </div>

        {/* Top Row - 3 Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-6">
          {/* Card 1: AI Mention Tracking */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-48 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              {/* Dotted pattern background */}
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              {/* Visual content */}
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="space-y-2 w-full max-w-[200px]">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded bg-green-500 flex items-center justify-center">
                        <span className="text-white text-xs font-bold">G</span>
                      </div>
                      <span className="text-xs font-medium text-gray-700">ChatGPT</span>
                      <span className="ml-auto text-xs text-green-600 font-medium">+24</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-orange-500 flex items-center justify-center">
                        <span className="text-white text-xs font-bold">C</span>
                      </div>
                      <span className="text-xs font-medium text-gray-700">Claude</span>
                      <span className="ml-auto text-xs text-green-600 font-medium">+18</span>
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-2 border border-green-200">
                    <div className="flex items-center gap-2">
                      <Eye className="w-4 h-4 text-green-600" />
                      <span className="text-xs font-medium text-green-700">Live Tracking</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Mention Tracking</h3>
            <p className="text-gray-600">
              Monitor brand mentions in real-time across ChatGPT, Claude, Gemini, Perplexity, and Grok.
            </p>
          </div>

          {/* Card 2: Share of Voice */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-48 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex items-center justify-center p-4">
                <div className="w-full max-w-[200px]">
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div className="text-center mb-3">
                      <span className="text-2xl font-bold text-primary">45%</span>
                      <p className="text-xs text-gray-500">Share of Voice</p>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: '45%' }} />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-gray-500">
                      <span>You</span>
                      <span>Competitors</span>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-center gap-1">
                    <BarChart3 className="w-4 h-4 text-gray-400" />
                    <span className="text-xs text-gray-500">vs 12 competitors</span>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Share of Voice</h3>
            <p className="text-gray-600">
              See exactly how your brand visibility compares to competitors in AI responses.
            </p>
          </div>

          {/* Card 3: Misinformation Alerts */}
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
                        <p className="text-xs font-medium text-gray-900">Alert Detected</p>
                        <p className="text-[10px] text-gray-500">Inaccurate pricing info</p>
                      </div>
                    </div>
                    <div className="mt-2 h-1.5 bg-red-100 rounded-full overflow-hidden">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: '70%' }} />
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-2 border border-green-200">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                        <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-xs font-medium text-green-700">Correction Sent</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Misinformation Alerts</h3>
            <p className="text-gray-600">
              Get instant notifications when AI platforms spread incorrect information about your brand.
            </p>
          </div>
        </div>

        {/* Bottom Row - 2 Cards */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Card 4: Competitor Analysis */}
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
                      <Users className="w-5 h-5 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">Competitor Analysis</span>
                    </div>
                    <div className="space-y-3">
                      {[
                        { name: "Your Brand", score: 87, color: "bg-primary" },
                        { name: "Competitor A", score: 65, color: "bg-gray-300" },
                        { name: "Competitor B", score: 52, color: "bg-gray-200" },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <span className="text-xs text-gray-600 w-24">{item.name}</span>
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.score}%` }} />
                          </div>
                          <span className="text-xs font-medium text-gray-900 w-8">{item.score}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Competitor Analysis</h3>
            <p className="text-gray-600">
              Benchmark your AI visibility against competitors. Identify gaps and opportunities to outperform them in AI search results.
            </p>
          </div>

          {/* Card 5: Automated Reports */}
          <div className="bg-white rounded-3xl p-6 border border-gray-200 shadow-sm">
            <div className="h-56 mb-6 relative overflow-hidden rounded-2xl bg-gray-50/50">
              <div className="absolute inset-0" style={{
                backgroundImage: 'radial-gradient(circle, #e5e7eb 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }} />
              <div className="relative h-full flex flex-col items-center justify-center p-4">
                <div className="flex items-center gap-4 mb-4">
                  {[
                    { icon: BarChart3, label: "Executive", color: "bg-blue-50 border-blue-100 text-blue-600" },
                    { icon: ({ className }: { className?: string }) => (
                      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 3v18h18" />
                        <path d="M18 9l-5 5-4-4-3 3" />
                      </svg>
                    ), label: "Analytics", color: "bg-orange-50 border-orange-100 text-orange-600" },
                    { icon: FileText, label: "Content", color: "bg-yellow-50 border-yellow-100 text-yellow-600" },
                  ].map((report, i) => (
                    <div key={i} className={`rounded-xl p-4 border shadow-sm bg-white`}>
                      <div className={`w-10 h-10 rounded-lg ${report.color.split(' ').slice(0, 2).join(' ')} flex items-center justify-center mb-2`}>
                        <report.icon className={`w-5 h-5 ${report.color.split(' ')[2]}`} />
                      </div>
                      <p className="text-xs font-medium text-gray-700">{report.label}</p>
                    </div>
                  ))}
                </div>
                <div className="bg-primary/10 rounded-full px-4 py-1.5 border border-primary/20">
                  <div className="flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-medium text-primary">PDF & Excel Export</span>
                  </div>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Automated Reports</h3>
            <p className="text-gray-600">
              Generate beautiful, stakeholder-ready reports. Schedule weekly or monthly delivery with custom templates.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
