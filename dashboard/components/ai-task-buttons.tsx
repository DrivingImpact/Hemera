"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

interface AITaskButtonsProps {
  taskType: string;
  targetType: string;
  targetId: number;
  context?: Record<string, unknown>;
  onResult: (responseText: string) => void;
  apiUrl?: string;
}

export default function AITaskButtons({
  taskType,
  targetType,
  targetId,
  context,
  onResult,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
}: AITaskButtonsProps) {
  const { getToken } = useAuth();
  const [status, setStatus] = useState<"idle" | "loading" | "awaiting_paste" | "done">("idle");
  const [taskId, setTaskId] = useState<number | null>(null);
  const [promptText, setPromptText] = useState("");
  const [clipboardFailed, setClipboardFailed] = useState(false);
  const [pasteValue, setPasteValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const token = await getToken();
    const res = await fetch(`${apiUrl}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options?.headers,
      },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `API error ${res.status}`);
    }
    return res.json();
  }

  async function handleGenerate(mode: "api" | "manual") {
    setStatus("loading");
    setError(null);
    try {
      const data = await apiFetch<{ id: number; response_text?: string; prompt_text?: string }>(
        "/api/ai-tasks",
        {
          method: "POST",
          body: JSON.stringify({
            task_type: taskType,
            target_type: targetType,
            target_id: targetId,
            mode,
            context: context || null,
          }),
        }
      );
      setTaskId(data.id);
      if (mode === "api") {
        setStatus("done");
        if (data.response_text) onResult(data.response_text);
      } else {
        const prompt = data.prompt_text ?? "";
        setPromptText(prompt);
        try {
          await navigator.clipboard.writeText(prompt);
          setClipboardFailed(false);
        } catch {
          setClipboardFailed(true);
        }
        setStatus("awaiting_paste");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("idle");
    }
  }

  async function handlePasteBack() {
    if (!taskId || !pasteValue.trim()) return;
    setStatus("loading");
    try {
      await apiFetch(`/api/ai-tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify({ response_text: pasteValue }),
      });
      setStatus("done");
      onResult(pasteValue);
      setPasteValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("awaiting_paste");
    }
  }

  if (status === "awaiting_paste") {
    return (
      <div className="space-y-2">
        {clipboardFailed ? (
          <>
            <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
              <span>Copy the prompt below, paste into Claude Max, then paste the response back.</span>
            </div>
            <div className="relative">
              <textarea
                readOnly
                value={promptText}
                className="w-full border border-amber-200 rounded-lg p-3 text-xs font-mono resize-y min-h-[120px] max-h-[200px] bg-amber-50/50"
              />
              <button
                onClick={() => navigator.clipboard.writeText(promptText).catch(() => {})}
                className="absolute top-2 right-2 px-2 py-1 bg-white border border-gray-200 rounded text-[10px] text-gray-600 hover:bg-gray-50"
              >
                Copy
              </button>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
            <span>Prompt copied to clipboard. Paste into Claude Max, then paste the response below.</span>
          </div>
        )}
        <textarea
          className="w-full border border-gray-200 rounded-lg p-3 text-sm font-mono resize-y min-h-[100px]"
          placeholder="Paste Claude Max response here..."
          value={pasteValue}
          onChange={(e) => setPasteValue(e.target.value)}
        />
        <div className="flex gap-2">
          <button
            onClick={handlePasteBack}
            disabled={!pasteValue.trim()}
            className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 disabled:opacity-50"
          >
            Apply Response
          </button>
          <button
            onClick={() => {
              setStatus("idle");
              setPasteValue("");
            }}
            className="px-4 py-2 border border-gray-200 text-gray-600 text-sm rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleGenerate("manual")}
        disabled={status === "loading"}
        className="px-3 py-1.5 border border-purple-400 bg-purple-50 text-purple-600 text-xs rounded-lg hover:bg-purple-100 disabled:opacity-50 font-semibold"
      >
        {status === "loading" ? "Preparing..." : "📋 Copy Prompt (Max)"}
      </button>
      <button
        onClick={() => handleGenerate("api")}
        disabled={status === "loading"}
        className="px-3 py-1.5 border border-gray-200 text-gray-500 text-xs rounded-lg hover:bg-gray-50 disabled:opacity-50"
      >
        {status === "loading" ? "Generating..." : "API"}
      </button>
      {error && <span className="text-xs text-red-500 self-center">{error}</span>}
      {status === "done" && <span className="text-xs text-green-600 self-center">✓ Done</span>}
    </div>
  );
}
