"use client";

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { useEffect, useState } from "react";

const COOKIE_NAME = "hemera_consent";

function getConsent(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_NAME}=([^;]*)`));
  return match ? match[1] : null;
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const host = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";

    // Only initialise if user accepted cookies AND we have a key
    if (!key) return;
    if (getConsent() !== "accepted") return;
    if (loaded) return;

    posthog.init(key, {
      api_host: host,
      person_profiles: "identified_only",
      capture_pageview: true,
      capture_pageleave: true,
      persistence: "localStorage+cookie",
      loaded: () => setLoaded(true),
    });
  }, [loaded]);

  // Re-check consent when cookie changes (user clicks accept after page load)
  useEffect(() => {
    if (loaded) return;
    const interval = setInterval(() => {
      if (getConsent() === "accepted") {
        const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
        const host = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://eu.i.posthog.com";
        if (key && !loaded) {
          posthog.init(key, {
            api_host: host,
            person_profiles: "identified_only",
            capture_pageview: true,
            capture_pageleave: true,
            persistence: "localStorage+cookie",
            loaded: () => setLoaded(true),
          });
        }
        clearInterval(interval);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [loaded]);

  if (!loaded) return <>{children}</>;

  return <PHProvider client={posthog}>{children}</PHProvider>;
}
