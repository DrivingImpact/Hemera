export interface Engagement {
  id: number;
  org_name: string;
  status: string;
  transaction_count: number;
  supplier_count: number;
  total_co2e: number;
  scope1_co2e: number;
  scope2_co2e: number;
  scope3_co2e: number;
  gsd_total: number;
  ci_lower: number;
  ci_upper: number;
  created_at: string;
}

export interface EngagementListItem {
  id: number;
  org_name: string;
  status: string;
  transaction_count: number;
  total_co2e: number;
  created_at: string;
  uploaded_by_email: string | null;
  display_name: string | null;
  admin_notes: string | null;
  qc_progress: { sampled: number; reviewed: number } | null;
}

export interface CategorySummary {
  name: string;
  scope: number;
  co2e_tonnes: number;
  spend_gbp: number;
  gsd: number;
}

export interface MonthlyData {
  has_data: boolean;
  months: { month: string; scope1: number; scope2: number; scope3: number }[];
}

export interface EngagementSupplier {
  supplier_id: number | null;
  name: string;
  co2e_tonnes: number;
  spend_gbp: number;
  intensity_kg_per_gbp: number;
  transaction_count: number;
}

export interface ReductionRec {
  type: string;
  category: string;
  action: string;
  current_co2e_kg: number;
  potential_reduction_pct: number;
  potential_reduction_kg: number;
  effort: string;
  timeline: string;
  explanation: string;
}

export interface Projections {
  baseline: number;
  ci_lower: number;
  ci_upper: number;
  year2_ci_lower: number;
  year2_ci_upper: number;
  year3_target: number;
  year3_ci_lower: number;
  year3_ci_upper: number;
  total_reduction: number;
}

export interface ReductionData {
  recommendations: ReductionRec[];
  projections: Projections;
}

export interface TransactionItem {
  id: number;
  date: string | null;
  description: string;
  supplier: string;
  amount_gbp: number;
  scope: number;
  category: string;
  ef_source: string;
  ef_level: number;
  co2e_kg: number;
  gsd: number;
}

export interface TransactionPage {
  total: number;
  offset: number;
  limit: number;
  transactions: TransactionItem[];
}

export interface SupplierListItem {
  id: number;
  ch_number: string;
  name: string;
  sector: string;
  hemera_score: number;
  confidence: string;
  critical_flag: boolean;
}

export interface SupplierDetail {
  id: number;
  ch_number: string;
  hemera_id: string;
  name: string;
  legal_name: string;
  status: string;
  sic_codes: string[];
  sector: string;
  entity_type: string;
  registered_address: string;
  hemera_score: number;
  confidence: string;
  critical_flag: boolean;
  created_at: string;
  updated_at: string;
  score_history: {
    hemera_score: number;
    confidence: string;
    critical_flag: boolean;
    layers_completed: number;
    domains: Record<string, number>;
    scored_at: string;
  }[];
  sources: {
    layer: number;
    source_name: string;
    tier: number;
    summary: string;
    is_verified: boolean;
    fetched_at: string;
  }[];
}
