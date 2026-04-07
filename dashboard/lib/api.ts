import { auth } from "@clerk/nextjs/server";
import type {
  Engagement,
  EngagementListItem,
  CategorySummary,
  MonthlyData,
  EngagementSupplier,
  ReductionData,
  TransactionPage,
  SupplierListItem,
  SupplierDetail,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();

  console.log(`[api] ${path} — token present: ${!!token}, token length: ${token?.length || 0}`);

  const res = await fetch(`${API_URL}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text();
    console.error(`[api] ${path} — ${res.status}: ${body}`);
    throw new Error(`API error ${res.status}: ${body}`);
  }

  return res.json();
}

export async function listEngagements() {
  return apiFetch<EngagementListItem[]>("/engagements");
}

export async function getEngagement(id: number) {
  return apiFetch<Engagement>(`/engagements/${id}`);
}

export async function getCategories(id: number) {
  return apiFetch<CategorySummary[]>(`/engagements/${id}/categories`);
}

export async function getMonthly(id: number) {
  return apiFetch<MonthlyData>(`/engagements/${id}/monthly`);
}

export async function getEngagementSuppliers(id: number) {
  return apiFetch<EngagementSupplier[]>(`/engagements/${id}/suppliers`);
}

export async function getReduction(id: number) {
  return apiFetch<ReductionData>(`/engagements/${id}/reduction`);
}

export async function getTransactions(
  id: number,
  params?: { scope?: number; category?: string; limit?: number; offset?: number }
) {
  const searchParams = new URLSearchParams();
  if (params?.scope) searchParams.set("scope", String(params.scope));
  if (params?.category) searchParams.set("category", params.category);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<TransactionPage>(`/engagements/${id}/transactions${qs ? `?${qs}` : ""}`);
}

export async function getSuppliers(q?: string, limit = 50) {
  const searchParams = new URLSearchParams();
  if (q) searchParams.set("q", q);
  searchParams.set("limit", String(limit));
  return apiFetch<SupplierListItem[]>(`/suppliers?${searchParams}`);
}

export async function getSupplier(id: number) {
  return apiFetch<SupplierDetail>(`/suppliers/${id}`);
}

export async function getDataQuality(engagementId: number) {
  return apiFetch<Record<string, unknown>>(`/reports/${engagementId}/data-quality`);
}

export function getPdfUrl(engagementId: number) {
  return `${API_URL}/api/reports/${engagementId}/pdf`;
}
