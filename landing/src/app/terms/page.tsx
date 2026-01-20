import Link from "next/link";
import Image from "next/image";
import { ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Terms of Service - PromptMaxx",
  description: "Terms of Service for PromptMaxx - AI Search Analytics Platform",
};

export default function TermsPage() {
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
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Terms of Service</h1>

        <div className="prose prose-gray max-w-none">
          <p className="text-gray-600 mb-6">
            <strong>Last Updated:</strong> January 20, 2026
          </p>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
            <p className="text-gray-600 mb-4">
              By accessing or using PromptMaxx ("Service"), you agree to be bound by these Terms of Service ("Terms").
              If you do not agree to these Terms, please do not use our Service.
            </p>
            <p className="text-gray-600 mb-4">
              PromptMaxx is operated by PromptMaxx Inc. ("we," "us," or "our"). These Terms govern your access to and
              use of our website, applications, and services.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Description of Service</h2>
            <p className="text-gray-600 mb-4">
              PromptMaxx provides AI search analytics and brand monitoring services that help businesses track their
              visibility across AI platforms including ChatGPT, Claude, Gemini, and Perplexity. Our services include:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Brand mention monitoring across AI platforms</li>
              <li>Competitor analysis and tracking</li>
              <li>Citation and source tracking</li>
              <li>AI-generated content optimization tools</li>
              <li>Analytics and reporting dashboards</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">3. Account Registration</h2>
            <p className="text-gray-600 mb-4">
              To use certain features of the Service, you must register for an account. When you register, you agree to:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Provide accurate, current, and complete information</li>
              <li>Maintain and update your information to keep it accurate</li>
              <li>Maintain the security of your account credentials</li>
              <li>Accept responsibility for all activities under your account</li>
              <li>Notify us immediately of any unauthorized use of your account</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Subscription and Payment</h2>
            <p className="text-gray-600 mb-4">
              PromptMaxx offers various subscription plans. By subscribing to a paid plan, you agree to:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Pay all fees associated with your chosen plan</li>
              <li>Provide valid payment information</li>
              <li>Authorize us to charge your payment method on a recurring basis</li>
              <li>Understand that subscriptions auto-renew unless cancelled</li>
            </ul>
            <p className="text-gray-600 mb-4">
              Refunds are handled on a case-by-case basis. Contact our support team for refund requests.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Acceptable Use</h2>
            <p className="text-gray-600 mb-4">
              You agree not to use the Service to:
            </p>
            <ul className="list-disc pl-6 text-gray-600 mb-4 space-y-2">
              <li>Violate any applicable laws or regulations</li>
              <li>Infringe on the intellectual property rights of others</li>
              <li>Transmit harmful, offensive, or illegal content</li>
              <li>Attempt to gain unauthorized access to our systems</li>
              <li>Interfere with or disrupt the Service</li>
              <li>Use automated means to access the Service without permission</li>
              <li>Resell or redistribute the Service without authorization</li>
            </ul>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Intellectual Property</h2>
            <p className="text-gray-600 mb-4">
              The Service and its original content, features, and functionality are owned by PromptMaxx Inc. and are
              protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
            </p>
            <p className="text-gray-600 mb-4">
              You retain ownership of any content you submit to the Service. By submitting content, you grant us a
              license to use, modify, and display that content in connection with providing the Service.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Data and Privacy</h2>
            <p className="text-gray-600 mb-4">
              Your use of the Service is also governed by our <Link href="/privacy" className="text-primary hover:underline">Privacy Policy</Link>.
              By using the Service, you consent to the collection and use of information as described in our Privacy Policy.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Third-Party Services</h2>
            <p className="text-gray-600 mb-4">
              Our Service may integrate with or provide access to third-party services and platforms (such as AI platforms
              we monitor). We are not responsible for the content, privacy policies, or practices of these third-party services.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Disclaimer of Warranties</h2>
            <p className="text-gray-600 mb-4">
              THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED.
              WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED, SECURE, OR ERROR-FREE.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Limitation of Liability</h2>
            <p className="text-gray-600 mb-4">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, PROMPTMAXX INC. SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
              SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS OR REVENUES, WHETHER INCURRED DIRECTLY
              OR INDIRECTLY.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">11. Termination</h2>
            <p className="text-gray-600 mb-4">
              We may terminate or suspend your account and access to the Service immediately, without prior notice, for
              conduct that we believe violates these Terms or is harmful to other users, us, or third parties, or for
              any other reason at our sole discretion.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">12. Changes to Terms</h2>
            <p className="text-gray-600 mb-4">
              We reserve the right to modify these Terms at any time. We will notify users of any material changes by
              posting the new Terms on this page and updating the "Last Updated" date. Your continued use of the Service
              after any changes constitutes acceptance of the new Terms.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">13. Governing Law</h2>
            <p className="text-gray-600 mb-4">
              These Terms shall be governed by and construed in accordance with the laws of the State of Delaware,
              United States, without regard to its conflict of law provisions.
            </p>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">14. Contact Us</h2>
            <p className="text-gray-600 mb-4">
              If you have any questions about these Terms, please contact us at:
            </p>
            <p className="text-gray-600">
              <strong>Email:</strong> legal@promptmaxx.co<br />
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
