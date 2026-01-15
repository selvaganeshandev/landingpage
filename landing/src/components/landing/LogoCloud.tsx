const brands = [
  "Breitling",
  "Attio",
  "Squarespace",
  "Brevo",
  "Hugo Boss",
  "n8n",
  "ElevenLabs",
  "Omio",
  "TUI Group",
  "Wix",
];

const agencies = [
  "Seer Interactive",
  "Previsible.io",
  "Peak Ace",
  "Eskimoz",
  "Omniscient",
  "Kinesso",
  "We Communications",
  "Mindshare",
  "Jas Global",
  "FirstPage",
];

export function LogoCloud() {
  return (
    <section className="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50 border-y border-gray-100">
      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12">
          {/* Brands */}
          <div>
            <div className="flex justify-center mb-8">
              <span className="px-4 py-1.5 bg-white rounded-full border border-gray-200 text-sm text-gray-600 font-medium">
                Brands
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-x-8 gap-y-6 items-center">
              {brands.map((brand, i) => (
                <div
                  key={i}
                  className="flex items-center justify-center h-8 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <span className="text-sm font-semibold tracking-wide whitespace-nowrap">
                    {brand}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Agencies */}
          <div className="lg:border-l lg:border-gray-200 lg:pl-12">
            <div className="flex justify-center mb-8">
              <span className="px-4 py-1.5 bg-white rounded-full border border-gray-200 text-sm text-gray-600 font-medium">
                Agencies
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-x-8 gap-y-6 items-center">
              {agencies.map((agency, i) => (
                <div
                  key={i}
                  className="flex items-center justify-center h-8 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <span className="text-sm font-semibold tracking-wide whitespace-nowrap">
                    {agency}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
