"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function ExcelDownloadButton({
  engagementId,
  orgName,
}: {
  engagementId: number;
  orgName: string;
}) {
  const { getToken } = useAuth();
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const token = await getToken();
      const res = await fetch(
        `${API_URL}/api/engagements/${engagementId}/export/xlsx`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);

      const blob = await res.blob();
      const slug = orgName.replace(/\s+/g, "-").toLowerCase();
      const filename = `hemera-${slug}-${engagementId}.xlsx`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Excel download failed:", err);
    }
    setDownloading(false);
  };

  return (
    <button
      onClick={handleDownload}
      disabled={downloading}
      className="flex-shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold border border-[#E5E5E0] text-muted hover:text-teal hover:border-teal/30 transition-colors disabled:opacity-50"
      title="Download Excel summary for Power BI"
    >
      {downloading ? (
        <>
          <div className="w-3.5 h-3.5 rounded-full border-2 border-teal/30 border-t-teal animate-spin" />
          Exporting...
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="7,10 12,15 17,10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export Excel
        </>
      )}
    </button>
  );
}
