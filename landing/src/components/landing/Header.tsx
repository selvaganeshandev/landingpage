"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToSection = (e: React.MouseEvent<HTMLAnchorElement>, sectionId: string) => {
    e.preventDefault();
    const element = document.getElementById(sectionId);
    if (element) {
      const headerOffset = 80; // Account for fixed header
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth"
      });
    }
    setMobileMenuOpen(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <Image
                src="/logo.png"
                alt="PromptMaxx"
                width={140}
                height={32}
                className="h-8 w-auto"
                priority
              />
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" onClick={(e) => scrollToSection(e, "features")} className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer">
              Features
            </a>
            <a href="#how-it-works" onClick={(e) => scrollToSection(e, "how-it-works")} className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer">
              How it works
            </a>
            <a href="#pricing" onClick={(e) => scrollToSection(e, "pricing")} className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer">
              Pricing
            </a>
            <a href="#faq" onClick={(e) => scrollToSection(e, "faq")} className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer">
              FAQ
            </a>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="https://app.promptmaxx.co/">
              <Button variant="ghost" className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                Sign in
              </Button>
            </Link>
            <Link href="https://app.promptmaxx.co/">
              <Button className="text-sm bg-primary text-white hover:bg-primary/90 rounded-full px-5 cursor-pointer">
                Get started
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6 text-gray-600" />
            ) : (
              <Menu className="w-6 h-6 text-gray-600" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-100">
            <div className="flex flex-col gap-4">
              <a href="#features" onClick={(e) => scrollToSection(e, "features")} className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                Features
              </a>
              <a href="#how-it-works" onClick={(e) => scrollToSection(e, "how-it-works")} className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                How it works
              </a>
              <a href="#pricing" onClick={(e) => scrollToSection(e, "pricing")} className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                Pricing
              </a>
              <a href="#faq" onClick={(e) => scrollToSection(e, "faq")} className="text-sm text-gray-600 hover:text-gray-900 cursor-pointer">
                FAQ
              </a>
              <div className="flex flex-col gap-2 pt-4 border-t border-gray-100">
                <Link href="https://app.promptmaxx.co/">
                  <Button variant="ghost" className="justify-start text-sm text-gray-600 w-full cursor-pointer">
                    Sign in
                  </Button>
                </Link>
                <Link href="https://app.promptmaxx.co/">
                  <Button className="text-sm bg-primary text-white hover:bg-primary/90 rounded-full w-full cursor-pointer">
                    Get started
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
