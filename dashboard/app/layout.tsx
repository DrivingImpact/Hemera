import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { PostHogProvider } from "@/components/posthog-provider";
import { CookieBanner } from "@/components/cookie-banner";
import "./globals.css";

export const metadata: Metadata = {
  title: "HemeraScope — Carbon & Supply Chain Intelligence",
  description: "Carbon footprints with confidence intervals, not guesswork. Supplier intelligence across 13 public registries. Analyst-verified, DEFRA-aligned, fully traceable.",
  icons: {
    icon: "/favicon.svg",
    apple: "/favicon.svg",
  },
  openGraph: {
    title: "HemeraScope — Carbon & Supply Chain Intelligence",
    description: "Carbon footprints with confidence intervals, not guesswork. Supplier intelligence across 13 public registries.",
    url: "https://hemerascope.com",
    siteName: "HemeraScope",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "HemeraScope — Carbon & Supply Chain Intelligence",
    description: "Carbon footprints with confidence intervals, not guesswork.",
  },
  metadataBase: new URL("https://hemerascope.com"),
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-paper text-slate font-sans antialiased">
          <PostHogProvider>
            {children}
          </PostHogProvider>
          <CookieBanner />
        </body>
      </html>
    </ClerkProvider>
  );
}
