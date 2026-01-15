"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
            <Link href="#features" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Features
            </Link>
            <Link href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              How it works
            </Link>
            <Link href="#pricing" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Pricing
            </Link>
            <Link href="#faq" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              FAQ
            </Link>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-3">
            <Button variant="ghost" className="text-sm text-gray-600 hover:text-gray-900">
              Sign in
            </Button>
            <Button className="text-sm bg-primary text-white hover:bg-primary/90 rounded-full px-5">
              Get started
            </Button>
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
              <Link href="#features" className="text-sm text-gray-600 hover:text-gray-900">
                Features
              </Link>
              <Link href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900">
                How it works
              </Link>
              <Link href="#pricing" className="text-sm text-gray-600 hover:text-gray-900">
                Pricing
              </Link>
              <Link href="#faq" className="text-sm text-gray-600 hover:text-gray-900">
                FAQ
              </Link>
              <div className="flex flex-col gap-2 pt-4 border-t border-gray-100">
                <Button variant="ghost" className="justify-start text-sm text-gray-600">
                  Sign in
                </Button>
                <Button className="text-sm bg-primary text-white hover:bg-primary/90 rounded-full">
                  Get started
                </Button>
              </div>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
