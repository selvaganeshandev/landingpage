import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Fonts are bundled (latin, variable, SIL OFL) so the build never needs Google Fonts.
const inter = localFont({ src: "./fonts/inter.woff2", weight: "400 600", variable: "--font-inter", display: "swap" });
const jakarta = localFont({ src: "./fonts/jakarta.woff2", weight: "500 800", variable: "--font-head", display: "swap" });
const mono = localFont({ src: "./fonts/mono.woff2", weight: "400 500", variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "Is AI recommending you, or your competitor? | Free AI Visibility Audit · PivotRoots",
  description:
    "Enter your domain. In 2 minutes, see exactly what ChatGPT, Gemini, Claude, Perplexity, Grok and DeepSeek say when your customers ask — and who they recommend instead.",
  openGraph: {
    title: "Is AI recommending you, or your competitor?",
    description: "Free AI Visibility Audit from PivotRoots. 6 engines. 2 minutes. No card.",
    type: "website",
  },
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    // suppressHydrationWarning: the inline script adds "js" to <html> before React hydrates.
    <html lang="en" className={`${inter.variable} ${jakarta.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        {/* Reveal animations hide content only once we know scripts run. */}
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
