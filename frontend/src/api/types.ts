// Tipe ditulis tangan mengikuti backend/app/schemas/*.py (sumber kebenaran) dan Swagger /docs.
// Tidak ada enum (tsconfig: erasableSyntaxOnly); semua union string literal.

export type Role = 'admin' | 'analyst' | 'viewer'

export interface UserOut {
  id: number
  username: string
  role: Role
  can_send_misp: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  db: 'ok' | 'error'
  misp_mode: 'mock' | 'live'
  time: string
}

export type Indication =
  | 'RENDAH'
  | 'PERLU_PEMERIKSAAN'
  | 'TINGGI'
  | 'SANGAT_TINGGI'

export type AssessmentStatus = 'COMPLETE' | 'DATA_TERBATAS' | 'TIDAK_TERSEDIA'

export type SourceStatus =
  | 'OK_SIGNAL'
  | 'OK_NO_SIGNAL'
  | 'NO_RECORD'
  | 'INSUFFICIENT_DATA'
  | 'ERROR'
  | 'SKIPPED'

export type SourceReason =
  | 'AUTH'
  | 'RATE_LIMIT'
  | 'TIMEOUT'
  | 'UPSTREAM'
  | 'INVALID_RESPONSE'
  | 'INTERNAL_ERROR'
  | 'ADAPTER_NOT_IMPLEMENTED'
  | 'QUOTA_INTERNAL'

export type SourceTimeType = 'last_report' | 'last_analysis'

export type Flag =
  | 'HASIL_BERBEDA'
  | 'NO_VENDOR_OPINION'
  | 'WHITELISTED'
  | 'SUMBER_SIMULASI'

export interface SourceResult {
  source: string
  status: SourceStatus
  reason: SourceReason | null
  normalized_score: number | null
  evidence_summary: Record<string, unknown>
  source_time: string | null
  source_time_type: SourceTimeType | null
  retrieved_at: string | null
  expires_at: string | null
  from_cache: boolean
  http_status: number | null
  duration_ms: number | null
  flags: Flag[]
  retry_after_seconds: number | null
}

export interface CheckOut {
  id: number
  ip: string
  assessment_status: AssessmentStatus
  risk_score: number | null
  scoring_version: string
  coverage: string
  flags: Flag[]
  sources: SourceResult[]
  checked_by: string
  checked_at: string
  indication: Indication | null
}

export type RejectReasonCode =
  | 'INVALID_FORMAT'
  | 'IPV6_NOT_SUPPORTED'
  | 'LOOPBACK'
  | 'LINK_LOCAL'
  | 'MULTICAST'
  | 'UNSPECIFIED'
  | 'DOCUMENTATION'
  | 'RESERVED'
  | 'PRIVATE'
  | 'NOT_GLOBAL'

export interface CheckRejected {
  assessment_status: 'INPUT_DITOLAK'
  risk_score: null
  reason_code: RejectReasonCode
  message: string
}

export interface CheckPage {
  items: CheckOut[]
  total: number
  limit: number
  offset: number
}

export type IocStatus = 'pending' | 'mock_sent' | 'sent' | 'failed'

export interface IocOut {
  id: number
  check_id: number
  ip: string
  reason: string
  tags: string[]
  status: IocStatus
  misp_event_uuid: string | null
  error_message: string | null
  submitted_by: string
  submitted_at: string
}

export interface IocPage {
  items: IocOut[]
  total: number
  limit: number
  offset: number
}

export interface IocDuplicate {
  detail: string
  submission_id: number
}
