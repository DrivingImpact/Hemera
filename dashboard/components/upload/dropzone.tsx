"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

type UploadState = "idle" | "uploading" | "processing" | "done" | "error";

interface UploadResult {
  engagement_id: number;
  transaction_count: number;
  total_co2e: number;
  supplier_count: number;
}

export function UploadDropzone() {
  const { getToken } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [state, setState] = useState<UploadState>("idle");
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const uploadFile = useCallback(
    async (file: File) => {
      setState("uploading");
      setErrorMsg("");

      try {
        const token = await getToken();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const formData = new FormData();
        formData.append("file", file);

        setState("uploading");
        const res = await fetch(`${apiUrl}/api/upload`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `Upload failed with status ${res.status}`);
        }

        setState("processing");
        const data: UploadResult = await res.json();
        setResult(data);
        setState("done");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Upload failed");
        setState("error");
      }
    },
    [getToken]
  );

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      uploadFile(files[0]);
    },
    [uploadFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => fileInputRef.current?.click();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const reset = () => {
    setState("idle");
    setResult(null);
    setErrorMsg("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  if (state === "done" && result) {
    return (
      <div className="text-center space-y-4 py-8">
        <div className="w-14 h-14 rounded-full bg-[#D1FAE5] flex items-center justify-center mx-auto">
          <svg className="w-7 h-7 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold">Upload Complete</h3>
          <p className="text-muted text-sm mt-1">Your data has been processed successfully.</p>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-6 max-w-sm mx-auto">
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">{result.transaction_count.toLocaleString()}</div>
            <div className="text-[11px] text-muted mt-0.5">Transactions</div>
          </div>
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">{result.total_co2e.toFixed(1)}</div>
            <div className="text-[11px] text-muted mt-0.5">tCO₂e</div>
          </div>
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">{result.supplier_count}</div>
            <div className="text-[11px] text-muted mt-0.5">Suppliers</div>
          </div>
        </div>
        <div className="flex gap-3 justify-center mt-6">
          <button
            onClick={() => router.push(`/dashboard/${result.engagement_id}`)}
            className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            View Results
          </button>
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-paper border border-[#E5E5E0] rounded-lg text-sm font-medium hover:bg-[#F0F0EB] transition-colors"
          >
            Upload Another
          </button>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="text-center space-y-4 py-8">
        <div className="w-14 h-14 rounded-full bg-[#FEE2E2] flex items-center justify-center mx-auto">
          <svg className="w-7 h-7 text-[#991B1B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold">Upload Failed</h3>
          <p className="text-muted text-sm mt-1 max-w-md mx-auto break-words">{errorMsg}</p>
        </div>
        <button
          onClick={reset}
          className="mt-4 px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (state === "uploading" || state === "processing") {
    return (
      <div className="text-center py-12 space-y-4">
        <div className="w-14 h-14 rounded-full border-4 border-teal/20 border-t-teal animate-spin mx-auto" />
        <div>
          <p className="font-medium">
            {state === "uploading" ? "Uploading file…" : "Processing transactions…"}
          </p>
          <p className="text-muted text-sm mt-1">
            {state === "uploading"
              ? "Please wait while we transfer your file."
              : "Classifying emissions and matching suppliers."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        className="hidden"
        onChange={handleInputChange}
      />
      <div
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragging
            ? "border-teal bg-teal/5"
            : "border-[#CBD5E1] hover:border-teal hover:bg-[#F8FBF9]"
        }`}
      >
        <div className="w-14 h-14 rounded-full bg-teal-tint flex items-center justify-center mx-auto">
          <svg className="w-7 h-7 text-teal" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p className="mt-4 font-semibold">
          {isDragging ? "Drop your file here" : "Drag & drop or click to upload"}
        </p>
        <p className="text-muted text-sm mt-1.5">CSV, Excel (.xlsx, .xls) — spend data with supplier and amount columns</p>
      </div>
    </>
  );
}
