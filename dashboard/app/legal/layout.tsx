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
            must not be relied on as a legally binding statement. See{" "}
            <code className="bg-amber-100 px-1 rounded text-[11px]">docs/research/2026-04-12-legal-statements.md</code>{" "}
            for the full drafts and flagged review items.
          </p>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-6 py-12">{children}</main>

      <footer className="border-t border-[#E5E5E0] mt-16">
        <div className="max-w-3xl mx-auto px-6 py-6 text-[11px] text-muted">
          Hemera Intelligence Ltd, trading as HemeraScope. Registered in England and Wales, company
          number [########]. Registered office: [address]. ICO registration number [########].
        </div>
      </footer>
    </div>
  );
}
