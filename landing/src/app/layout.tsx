import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PromptMaxx - AI Search Analytics for Marketing Teams",
  description: "Monitor your brand visibility across AI platforms like ChatGPT, Claude, Gemini, and Perplexity. Get actionable insights to optimize your AI search presence.",
  keywords: ["AI search analytics", "brand monitoring", "ChatGPT", "Claude", "Gemini", "Perplexity", "AI visibility", "marketing analytics"],
  authors: [{ name: "PromptMaxx" }],
  openGraph: {
    title: "PromptMaxx - AI Search Analytics for Marketing Teams",
    description: "Monitor your brand visibility across AI platforms like ChatGPT, Claude, Gemini, and Perplexity.",
    type: "website",
    locale: "en_US",
    siteName: "PromptMaxx",
  },
  twitter: {
    card: "summary_large_image",
    title: "PromptMaxx - AI Search Analytics for Marketing Teams",
    description: "Monitor your brand visibility across AI platforms like ChatGPT, Claude, Gemini, and Perplexity.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
