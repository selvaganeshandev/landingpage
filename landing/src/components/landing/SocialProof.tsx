import Image from "next/image";

const testimonials = [
  {
    quote: "PromptMaxx helped us discover that ChatGPT was giving outdated information about our product. We fixed it within a week and saw a 30% increase in AI-referred traffic.",
    author: "Sarah Chen",
    role: "Marketing Director at TechCorp",
    avatar: "/avatars/avatar-1.png",
  },
  {
    quote: "The competitor analysis feature is incredible. We now know exactly how we stack up against our competitors in AI search and can make data-driven decisions.",
    author: "Michael Ross",
    role: "VP of Growth at ScaleUp Inc",
    avatar: "/avatars/avatar-2.png",
  },
  {
    quote: "Finally, a tool that helps us understand and optimize our presence in the new AI-first search landscape. It's become essential to our marketing stack.",
    author: "Emily Watson",
    role: "CMO at DataDriven",
    avatar: "/avatars/avatar-3.png",
  },
];

export function SocialProof() {
  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Testimonials */}
        <div className="text-center mb-12">
          <p className="text-sm font-medium text-primary uppercase tracking-wider mb-4">Testimonials</p>
          <h3 className="text-2xl sm:text-3xl font-semibold text-gray-900 mb-4">
            What marketers are saying about us
          </h3>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((testimonial, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 border border-gray-200 shadow-sm">
              <div className="flex items-center gap-1 mb-4">
                {[...Array(5)].map((_, j) => (
                  <svg key={j} className="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-gray-700 mb-6">&ldquo;{testimonial.quote}&rdquo;</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gray-200 overflow-hidden relative">
                  <Image
                    src={testimonial.avatar}
                    alt={testimonial.author}
                    fill
                    className="object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/80 to-secondary/80 flex items-center justify-center">
                    <span className="text-sm font-semibold text-white">{testimonial.author.charAt(0)}</span>
                  </div>
                </div>
                <div>
                  <p className="font-medium text-gray-900 text-sm">{testimonial.author}</p>
                  <p className="text-xs text-gray-500">{testimonial.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
