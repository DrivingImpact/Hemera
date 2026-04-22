import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { PostHogProvider } from "@/components/posthog-provider";
import { CookieBanner } from "@/components/cookie-banner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hemera",
  description: "Supply Chain & Carbon Intelligence",
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
