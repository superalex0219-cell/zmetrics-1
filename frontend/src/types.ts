import type { LucideIcon } from "lucide-react";

export type NavKey =
  | "auth"
  | "dashboard"
  | "quarries"
  | "sites"
  | "passports"
  | "analyses"
  | "reports"
  | "recommendations"
  | "admin";

export interface NavItem {
  key: NavKey;
  label: string;
  icon: LucideIcon;
}

// UI display type for histogram bars
export interface Fraction {
  label: string;
  percent: number;
}

// ---- ZMetrics API response types (matching backend Pydantic schemas) ----

export interface Quarry {
  id: string;
  name: string;
  location_description: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface SiteSection {
  id: string;
  quarry_id: string;
  name: string;
  block_number: string | null;
  description: string | null;
}

export interface BlastPassport {
  id: string;
  site_section_id: string;
  status: string; // DRAFT | SUBMITTED | APPROVED | ACTIVE | COMPLETED | SUPERSEDED
  revision_number: number;
  explosive_type: string | null;
  total_explosive_kg: number | null;
  number_of_holes: number | null;
  hole_diameter_mm: number | null;
  hole_depth_m: number | null;
  burden_m: number | null;
  spacing_m: number | null;
  target_p80_mm: number | null;
  created_at: string;
  updated_at: string;
}

export interface SizeBin {
  size_mm: number;
  cumulative_passing_pct: number;
}

export interface AnalysisResult {
  id: string;
  p10_mm: number | null;
  p50_mm: number | null;
  p80_mm: number | null;
  rosin_rammler_n: number | null;
  rosin_rammler_xc: number | null;
  oversize_percent: number | null;
  fines_percent: number | null;
  confidence_score: number | null;
  confidence_notes: string | null;
  size_distribution: SizeBin[] | null;
}

export interface Report {
  id: string;
  title: string;
  report_type: string;
  analysis_method: string; // "mock" | "real"
  analysis_result_id: string;
  confidence_score: number | null;
  model_version_tag: string | null;
  created_at: string;
}

export interface Recommendation {
  id: string;
  report_id: string;
  status: string; // requires_human_review | reviewed | accepted | rejected
  recommendation_text: string;
  parameter_suggestions: Record<string, unknown> | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuthUser {
  sub: string;
  preferred_username?: string;
  name?: string;
  email?: string;
}
