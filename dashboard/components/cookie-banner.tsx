"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const COOKIE_NAME = "hemera_consent";
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60; // 1 year in seconds

type Consent = "accepted" | "rejected" | null;

function getConsent(): Consent {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_NAME}=([^;]*)`));
  if (!match) return null;
  const val = match[1];
  return val === "accepted" || val === "rejected" ? val : null;
}

function setConsent(value: "accepted" | "rejected") {
  document.cookie = `${COOKIE_NAME}=${value}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax; Secure`;
}

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Only show if no consent choice has been made
    if (getConsent() === null) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const handleAccept = () => {
    setConsent("accepted");
    setVisible(false);
  };

  const handleReject = () => {
    setConsent("rejected");
    setVisible(false);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 sm:p-6">
      <div className="max-w-2xl mx-auto bg-slate text-white rounded-2xl shadow-2xl border border-white/10 p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold mb-1">Cookies</p>
            <p className="text-xs text-white/70 leading-relaxed">
              We use essential cookies to keep you signed in and protect against attacks. We don&apos;t
              use advertising or tracking cookies.{" "}
              <Link href="/legal/cookies" className="text-teal hover:underline font-medium">
                Cookie policy
              </Link>
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleReject}
              className="px-4 py-2 text-xs font-semibold rounded-lg border border-white/20 text-white/80 hover:text-white hover:border-white/40 transition-colors"
            >
              Reject non-essential
            </button>
            <button
              onClick={handleAccept}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-teal text-white hover:opacity-90 transition-opacity"
            >
              Accept all
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
