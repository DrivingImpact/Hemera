import Link from "next/link";
import type { ReactNode } from "react";

export default function LegalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      {/* Minimal top nav back to home */}
      <header className="border-b border-[#E5E5E0]">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-sm font-bold text-slate hover:text-teal transition-colors">
            ← HemeraScope
          </Link>
          <nav className="flex items-center gap-5 text-xs">
            <Link href="/legal/privacy" className="text-muted hover:text-teal transition-colors">Privacy</Link>
            <Link href="/legal/terms" className="text-muted hover:text-teal transition-colors">Terms</Link>
            <Link href="/legal/cookies" className="text-muted hover:text-teal transition-colors">Cookies</Link>
          </nav>
        </div>
      </header>

      {/* Draft warning banner — remove once solicitor review complete */}
      <div className="bg-amber-50 border-b border-amber-200">
        <div className="max-w-3xl mx-auto px-6 py-3">
          <p className="text-[12px] text-amber-900 leading-relaxed">
            <strong>Draft — not yet legally reviewed.</strong> This document is a working draft
            prepared for internal use. It has not yet been reviewed by a qualified UK solicitor and
            must not be relied on as a legally binding statement.
          </p>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-6 py-12 relative">
        {/* Large DRAFT watermark across the page */}
        <div className="pointer-events-none fixed inset-0 z-10 flex items-center justify-center overflow-hidden" aria-hidden="true">
          <span className="text-[120px] sm:text-[180px] font-black text-amber-200/30 uppercase tracking-[0.2em] -rotate-12 select-none whitespace-nowrap">
            DRAFT
          </span>
        </div>
        <div className="relative z-20">{children}</div>
      </main>

      <footer className="border-t border-[#E5E5E0] mt-16">
        <div className="max-w-3xl mx-auto px-6 py-6 text-[11px] text-muted">
          Hemera Intelligence Ltd, trading as HemeraScope. Registered in England and Wales, company
          number [pending — Companies House]. Registered office: [pending — registered address]. ICO registration number [pending — ICO registration].
        </div>
      </footer>
    </div>
  );
}
