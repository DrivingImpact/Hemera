import { currentUser } from "@clerk/nextjs/server";

export interface HemeraUser {
  clerkId: string;
  email: string;
  role: "admin" | "client";
  orgName: string;
}

/**
 * Get the current user's role and org from Clerk's publicMetadata.
 * This uses currentUser() which always returns publicMetadata
 * (unlike session claims which need JWT template configuration).
 */
export async function getHemeraUser(): Promise<HemeraUser | null> {
  const user = await currentUser();
  if (!user) return null;

  const meta = user.publicMetadata as Record<string, unknown>;
  return {
    clerkId: user.id,
    email: user.emailAddresses[0]?.emailAddress || "",
    role: meta?.role === "admin" ? "admin" : "client",
    orgName: (meta?.org_name as string) || "",
  };
}
