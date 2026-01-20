import Link from "next/link";
import Image from "next/image";
import { ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Privacy Policy - PromptMaxx",
  description: "Privacy Policy for PromptMaxx - AI Search Analytics Platform",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center">
              <Image
                src="/logo.png"
                alt="PromptMaxx"
                width={140}
                height={32}
                className="h-8 w-auto"
              />
            </Link>
            <Link
              href="/"
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Home
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy</h1>

        <div className="prose prose-gray max-w-none">
          <p className="text-gray-600 mb-6">
            <strong>Last Updated:</strong> January 20, 2026
          </p>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
            <p className="text-gray-600 mb-4">
              PromptMaxx Inc. (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;) is committed to protecting your privacy. This Privacy Policy
              explains how we collect, use, disclose, and safeguard your information when you use our AI search analytics
              platform and related services (collectively, the &quot;Service&quot;).
            </p>
            <p className="text-gray-600 mb-4">
              By using our Service, you consent to the data practices described in this Privacy Policy. If you do not
              agree with the practices described here, please do not use our Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>

            <h3 className="text-lg font-medium text-gray-900 mb-3">2.1 Information You Provide</h3>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li><strong>Account Information:</strong> Name, email address, company name, and password when you register</li>
              <li><strong>Profile Information:</strong> Job title, industry, company size, and other business details</li>
              <li><strong>Payment Information:</strong> Billing address and payment details (processed securely by our payment processor)</li>
              <li><strong>Domain Information:</strong> Website URLs and brand names you wish to monitor</li>
              <li><strong>Communication Data:</strong> Messages you send to our support team</li>
            </ul>

            <h3 className="text-lg font-medium text-gray-900 mb-3">2.2 Information Collected Automatically</h3>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li><strong>Usage Data:</strong> Features used, pages visited, and interactions with our Service</li>
              <li><strong>Device Information:</strong> Browser type, operating system, and device identifiers</li>
              <li><strong>Log Data:</strong> IP address, access times, and referring URLs</li>
              <li><strong>Analytics Data:</strong> Performance metrics and error reports</li>
            </ul>

            <h3 className="text-lg font-medium text-gray-900 mb-3">2.3 Information from Third Parties</h3>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li><strong>AI Platform Data:</strong> Publicly available responses from AI platforms (ChatGPT, Claude, Gemini, Perplexity) that mention your monitored brands</li>
              <li><strong>Google Analytics/Search Console:</strong> Website traffic and search data (with your authorization)</li>
              <li><strong>OAuth Providers:</strong> Basic profile information if you sign in with Google</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
            <p className="text-gray-600 mb-4">We use the collected information to:</p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Provide, maintain, and improve our Service</li>
              <li>Monitor your brand mentions across AI platforms</li>
              <li>Generate analytics reports and insights</li>
              <li>Process payments and manage subscriptions</li>
              <li>Send you service-related communications and updates</li>
              <li>Respond to your inquiries and provide customer support</li>
              <li>Detect and prevent fraud, abuse, and security issues</li>
              <li>Comply with legal obligations</li>
              <li>Analyze usage patterns to improve user experience</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Information Sharing and Disclosure</h2>
            <p className="text-gray-600 mb-4">We may share your information in the following circumstances:</p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li><strong>Service Providers:</strong> Third-party vendors who assist in operating our Service (hosting, payment processing, email delivery)</li>
              <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
              <li><strong>Legal Requirements:</strong> When required by law or to protect our rights and safety</li>
              <li><strong>With Your Consent:</strong> When you explicitly authorize us to share information</li>
            </ul>
            <p className="text-gray-600 mb-4">
              We do not sell your personal information to third parties.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Data Security</h2>
            <p className="text-gray-600 mb-4">
              We implement appropriate technical and organizational measures to protect your information, including:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Encryption of data in transit and at rest</li>
              <li>Regular security assessments and audits</li>
              <li>Access controls and authentication measures</li>
              <li>Employee training on data protection</li>
              <li>Incident response procedures</li>
            </ul>
            <p className="text-gray-600 mb-4">
              However, no method of transmission over the Internet is 100% secure. We cannot guarantee absolute security
              of your data.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Data Retention</h2>
            <p className="text-gray-600 mb-4">
              We retain your information for as long as your account is active or as needed to provide our Service.
              We may also retain and use your information as necessary to:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Comply with legal obligations</li>
              <li>Resolve disputes</li>
              <li>Enforce our agreements</li>
              <li>Maintain business records</li>
            </ul>
            <p className="text-gray-600 mb-4">
              Upon account deletion, we will delete or anonymize your personal information within 90 days, unless
              retention is required by law.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Your Rights and Choices</h2>
            <p className="text-gray-600 mb-4">Depending on your location, you may have the following rights:</p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li><strong>Access:</strong> Request a copy of your personal information</li>
              <li><strong>Correction:</strong> Request correction of inaccurate information</li>
              <li><strong>Deletion:</strong> Request deletion of your personal information</li>
              <li><strong>Portability:</strong> Request your data in a portable format</li>
              <li><strong>Objection:</strong> Object to certain processing of your information</li>
              <li><strong>Restriction:</strong> Request restriction of processing</li>
              <li><strong>Withdraw Consent:</strong> Withdraw consent where processing is based on consent</li>
            </ul>
            <p className="text-gray-600 mb-4">
              To exercise these rights, please contact us at privacy@promptmaxx.co. We will respond to your request
              within 30 days.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">8. International Data Transfers</h2>
            <p className="text-gray-600 mb-4">
              Your information may be transferred to and processed in countries other than your country of residence.
              These countries may have different data protection laws. We ensure appropriate safeguards are in place
              for such transfers, including standard contractual clauses approved by relevant authorities.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Third-Party Links and Services</h2>
            <p className="text-gray-600 mb-4">
              Our Service may contain links to third-party websites and integrate with third-party services. We are
              not responsible for the privacy practices of these third parties. We encourage you to review their
              privacy policies before providing any information.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Children&apos;s Privacy</h2>
            <p className="text-gray-600 mb-4">
              Our Service is not intended for children under 16 years of age. We do not knowingly collect personal
              information from children. If we become aware that we have collected information from a child, we will
              take steps to delete it promptly.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">11. Changes to This Privacy Policy</h2>
            <p className="text-gray-600 mb-4">
              We may update this Privacy Policy from time to time. We will notify you of any material changes by
              posting the new Privacy Policy on this page and updating the &quot;Last Updated&quot; date. We encourage you to
              review this Privacy Policy periodically.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">12. Contact Us</h2>
            <p className="text-gray-600 mb-4">
              If you have any questions about this Privacy Policy or our data practices, please contact us at:
            </p>
            <p className="text-gray-600">
              <strong>Email:</strong> privacy@promptmaxx.co<br />
              <strong>Address:</strong> PromptMaxx Inc.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} PromptMaxx. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
