"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function DeleteEngagement({ engagementId }: { engagementId: number }) {
  const { getToken } = useAuth();
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);

  const handleDelete = async () => {
    const token = await getToken();
    await fetch(`${API_URL}/api/engagements/${engagementId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    router.refresh();
  };

  if (confirming) {
    return (
      <div className="flex gap-1">
        <button onClick={handleDelete} className="text-error text-xs font-semibold">Confirm</button>
        <button onClick={() => setConfirming(false)} className="text-muted text-xs">Cancel</button>
      </div>
    );
  }

  return (
    <button onClick={() => setConfirming(true)} className="text-muted text-xs hover:text-error">
      Delete
    </button>
  );
}
