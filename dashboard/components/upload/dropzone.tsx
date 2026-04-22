"use client";

import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";

type UploadState = "idle" | "uploading" | "processing" | "done" | "error";

interface UploadResult {
  engagement_id: number;
  filename: string;
  status: string;
  parsing: {
    transactions_parsed: number;
    duplicates_removed: number;
    date_range: string;
    total_spend_gbp: number;
    unique_suppliers: number;
    data_type?: string;
    activity_type?: string | null;
    detected_unit?: string | null;
    total_quantity?: number | null;
  };
}

type DataType = "spend" | "activity";

type ActivityType =
  | ""
  | "electricity"
  | "natural_gas"
  | "diesel"
  | "petrol"
  | "lpg"
  | "heating_oil"
  | "heat"
  | "water"
  | "waste"
  | "distance"
  | "refrigerants"
  | "other";

const ACTIVITY_OPTIONS: { value: ActivityType; label: string; hint: string }[] = [
  { value: "",             label: "Auto-detect from columns", hint: "Let us infer from column headers (kWh, litres, etc.)" },
  { value: "electricity",  label: "Electricity",              hint: "kWh from utility bills" },
  { value: "natural_gas",  label: "Natural gas",              hint: "kWh or m³ from gas bills" },
  { value: "diesel",       label: "Diesel fuel",              hint: "Litres purchased" },
  { value: "petrol",       label: "Petrol fuel",              hint: "Litres purchased" },
  { value: "lpg",          label: "LPG",                      hint: "Litres purchased" },
  { value: "heating_oil",  label: "Heating oil",              hint: "Litres purchased" },
  { value: "heat",         label: "District heat",            hint: "kWh delivered" },
  { value: "water",        label: "Water",                    hint: "m³ supplied" },
  { value: "waste",        label: "Waste",                    hint: "Tonnes, by category" },
  { value: "distance",     label: "Travel / freight",         hint: "km by vehicle class" },
  { value: "refrigerants", label: "Refrigerant leakage",      hint: "kg of gas lost" },
  { value: "other",        label: "Other (type it below)",    hint: "Describe the activity in your own words" },
];

export function UploadDropzone() {
  const { getToken } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [state, setState] = useState<UploadState>("idle");
  const [isDragging, setIsDragging] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // New: data type selection
  const [dataType, setDataType] = useState<DataType>("spend");
  const [activityType, setActivityType] = useState<ActivityType>("");
  const [rawActivityLabel, setRawActivityLabel] = useState<string>("");

  const uploadFile = useCallback(
    async (file: File) => {
      setState("uploading");
      setErrorMsg("");

      try {
        const token = await getToken();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const formData = new FormData();
        formData.append("file", file);
        formData.append("data_type", dataType);
        if (dataType === "activity") {
          if (activityType) formData.append("activity_type", activityType);
          if (rawActivityLabel) formData.append("raw_activity_label", rawActivityLabel);
        }

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
        router.refresh();
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Upload failed");
        setState("error");
      }
    },
    [getToken, dataType, activityType, rawActivityLabel, router]
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
    const p = result.parsing;
    const isActivity = p.data_type === "activity";
    return (
      <div className="text-center space-y-4 py-8">
        <div className="w-14 h-14 rounded-full bg-[#D1FAE5] flex items-center justify-center mx-auto">
          <svg className="w-7 h-7 text-[#065F46]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold">Upload complete!</h3>
          <p className="text-muted text-sm mt-1 max-w-sm mx-auto">
            Our team will review your data and be in touch shortly.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-6 max-w-sm mx-auto">
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">{p.transactions_parsed.toLocaleString()}</div>
            <div className="text-[11px] text-muted mt-0.5">{isActivity ? "Rows" : "Transactions"}</div>
          </div>
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">
              {isActivity && p.total_quantity != null
                ? `${p.total_quantity.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                : `£${(p.total_spend_gbp / 1000).toFixed(0)}k`}
            </div>
            <div className="text-[11px] text-muted mt-0.5">
              {isActivity ? `Total ${p.detected_unit ?? "quantity"}` : "Total spend"}
            </div>
          </div>
          <div className="bg-paper rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-teal tabular-nums">{p.unique_suppliers}</div>
            <div className="text-[11px] text-muted mt-0.5">Suppliers</div>
          </div>
        </div>
        <div className="flex justify-center mt-6">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-teal text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
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
    <div className="space-y-5">
      {/* Data type picker */}
      <div>
        <label className="text-xs font-semibold uppercase tracking-wide text-muted mb-2 block">
          What kind of data is this?
        </label>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => setDataType("spend")}
            className={`p-3 rounded-lg border text-left transition-colors ${
              dataType === "spend"
                ? "border-teal bg-teal/5"
                : "border-[#E5E5E0] hover:border-teal/40"
            }`}
          >
            <div className="font-semibold text-sm">Spend data</div>
            <div className="text-[11px] text-muted mt-0.5">
              Accounting export with supplier names + GBP amounts
            </div>
          </button>
          <button
            type="button"
            onClick={() => setDataType("activity")}
            className={`p-3 rounded-lg border text-left transition-colors ${
              dataType === "activity"
                ? "border-teal bg-teal/5"
                : "border-[#E5E5E0] hover:border-teal/40"
            }`}
          >
            <div className="font-semibold text-sm">Activity data</div>
            <div className="text-[11px] text-muted mt-0.5">
              Utility bills, fuel records, travel — kWh, litres, km, etc.
            </div>
          </button>
        </div>
      </div>

      {/* Activity subtype picker — only visible when activity mode is selected */}
      {dataType === "activity" && (
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wide text-muted block">
            Activity type
          </label>
          <select
            value={activityType}
            onChange={(e) => setActivityType(e.target.value as ActivityType)}
            className="w-full border border-[#E5E5E0] rounded-lg px-3 py-2 text-sm bg-white focus:border-teal outline-none"
          >
            {ACTIVITY_OPTIONS.map((opt) => (
              <option key={opt.value || "auto"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {activityType && (
            <p className="text-[11px] text-muted">
              {ACTIVITY_OPTIONS.find((o) => o.value === activityType)?.hint}
            </p>
          )}
          {activityType === "other" && (
            <input
              type="text"
              value={rawActivityLabel}
              onChange={(e) => setRawActivityLabel(e.target.value)}
              placeholder="e.g. Steam (kg) from on-site boiler"
              className="w-full border border-[#E5E5E0] rounded-lg px-3 py-2 text-sm focus:border-teal outline-none"
            />
          )}
        </div>
      )}

      {/* Dropzone */}
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
        <p className="text-muted text-sm mt-1.5">
          {dataType === "spend"
            ? "CSV, Excel (.xlsx, .xls) — spend data with supplier and amount columns"
            : "CSV, Excel (.xlsx, .xls) — activity data with supplier and a quantity column (kWh, litres, m³, kg, km)"}
        </p>
      </div>
    </div>
  );
}
