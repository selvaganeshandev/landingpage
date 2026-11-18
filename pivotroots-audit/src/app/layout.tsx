import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-inter", display: "swap" });
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["500", "600", "700", "800"], variable: "--font-head", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });

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
