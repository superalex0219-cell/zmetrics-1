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
  status: string; // draft | submitted | approved | active | completed | superseded
  revision_number: number;
  blast_date_planned: string | null;
  explosive_type: string | null;
  total_explosive_kg: number | null;
  number_of_holes: number | null;
  hole_diameter_mm: number | null;
  hole_depth_m: number | null;
  burden_m: number | null;
  spacing_m: number | null;
  stemming_m: number | null;
  target_p80_mm: number | null;
  notes: string | null;
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

export interface BlastEvent {
  id: string;
  passport_id: string;
  executed_by_id: string;
  blast_datetime: string; // ISO string
  actual_explosive_kg: number | null;
  weather_conditions: string | null;
  notes: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  occurred_at: string; // ISO string
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
}

export interface Device {
  id: string;
  serial_number: string;
  model: string;
  firmware_version: string | null;
  notes: string | null;
}

export interface Calibration {
  id: string;
  device_id: string;
  baseline_mm: number;
  image_width_px: number;
  image_height_px: number;
  is_active: boolean;
  created_at: string;
}

export interface CaptureSession {
  id: string;
  blast_event_id: string;
  device_id: string;
  calibration_id: string;
  captured_by_id: string;
  capture_datetime: string;
  frame_count: number;
  notes: string | null;
}

export interface AnalysisJob {
  id: string;
  capture_session_id: string;
  model_version_id: string | null;
  status: string; // queued | running | completed | failed
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  pipeline_log: Record<string, unknown> | null;
}

export interface Artifact {
  id: string;
  capture_session_id: string;
  artifact_type: string;
  storage_bucket: string;
  storage_key: string;
  file_size_bytes: number | null;
  content_type: string | null;
  frame_index: number | null;
}

export interface CapturedFrame {
  id: string;
  blob: Blob;
  dataUrl: string;
  width: number;
  height: number;
  artifactType: 'left_frame' | 'right_frame';
  frameIndex: number;
  capturedAt: number;
}
