import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hemera",
  description: "Supply Chain & Carbon Intelligence",
};

function MaybeClerkProvider({ children }: { children: React.ReactNode }) {
  // Skip Clerk when keys aren't configured (local preview)
  const key = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  if (!key || key.includes("REPLACE_ME")) {
    return <>{children}</>;
  }
  // Dynamic import to avoid build error when Clerk isn't configured
  const { ClerkProvider } = require("@clerk/nextjs");
  return <ClerkProvider>{children}</ClerkProvider>;
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-paper text-slate font-sans antialiased">
        <MaybeClerkProvider>{children}</MaybeClerkProvider>
      </body>
    </html>
  );
}
