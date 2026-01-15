const stats = [
  { value: "40%", label: "of Gen Z prefer AI over Google for search" },
  { value: "2B+", label: "AI search queries per month globally" },
  { value: "65%", label: "of marketers are unprepared for AI search" },
  { value: "3x", label: "higher conversion from AI referrals" },
];

export function Statistics() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-2xl sm:text-3xl font-semibold text-gray-900 mb-4">
            The shift to AI search is happening
          </h2>
          <p className="text-gray-600">
            AI assistants are replacing traditional search engines for millions of users.
          </p>
        </div>

        {/* Stats - Minimal Modern Design */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-gray-200 rounded-2xl overflow-hidden">
          {stats.map((stat, i) => (
            <div
              key={i}
              className="bg-white p-6 text-center hover:bg-gray-50 transition-colors"
            >
              <p className="text-3xl font-bold text-primary mb-1">
                {stat.value}
              </p>
              <p className="text-xs text-gray-500 leading-relaxed">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
