/** Domain types mirroring the NyayaLens backend schemas (backend/app/schemas/*). */

export type EvidenceState =
  | "DOCUMENT-GROUNDED"
  | "GENERAL-INFORMATION"
  | "INSUFFICIENT-EVIDENCE";

export type DocumentStatus =
  | "UPLOADED"
  | "VALIDATING"
  | "PROCESSING"
  | "EXTRACTING"
  | "ANALYZING"
  | "READY"
  | "FAILED";

export type DocumentType =
  | "employment_agreement"
  | "lease"
  | "loan_agreement"
  | "nda"
  | "partnership"
  | "other";

export type ActionType =
  | "REVIEW_CLAUSE"
  | "ASK_PROFESSIONAL"
  | "COLLECT_DOCUMENT"
  | "VERIFY_INFORMATION"
  | "NEGOTIATE_TERM"
  | "FOLLOW_UP";

export type ActionStatus = "TODO" | "IN_PROGRESS" | "COMPLETED" | "DISMISSED";

export type Priority = "LOW" | "MEDIUM" | "HIGH";

export type AttentionLevel = "LOW" | "MEDIUM" | "HIGH";

export const PROCESSING_STATUSES: DocumentStatus[] = [
  "UPLOADED",
  "VALIDATING",
  "PROCESSING",
  "EXTRACTING",
  "ANALYZING",
];

/* ---------- Envelope ---------- */

export interface SuccessResponse<T> {
  success: boolean;
  data: T | null;
  message: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  details: string[] | null;
}

export interface ApiErrorResponse {
  success: false;
  error: ApiError;
}

/* ---------- Auth ---------- */

export interface UserOut {
  id: string;
  email: string | null;
  role: string;
}

/* ---------- Documents ---------- */

export interface DocumentOut {
  id: string;
  filename: string;
  display_name: string | null;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  processing_error: string | null;
  page_count: number | null;
  checksum_sha256: string | null;
  uploaded_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DocumentStatusData {
  id: string;
  status: DocumentStatus;
  message: string | null;
  progress: number | null;
}

/** Short-lived ticket the browser PUTs the file bytes to. */
export interface DocumentUploadTicket {
  path: string;
  token: string;
  signed_url: string;
  expires_in_seconds: number;
}

export interface UploadIntentData {
  document: DocumentOut;
  upload: DocumentUploadTicket;
}

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface DocumentListData {
  items: DocumentOut[];
  pagination: Pagination;
}

/* ---------- Q&A ---------- */

export interface CitationOut {
  id: string;
  chunk_id: string;
  document_id: string;
  section_id: string | null;
  clause_id: string | null;
  section: string;
  clause: string | null;
  page_start: number;
  page_end: number | null;
  source_text: string;
}

export interface RelatedSectionOut {
  label: string;
  section_id: string | null;
  page_start: number | null;
  page_end: number | null;
}

export interface QAAnswerOut {
  document_id: string;
  answer: string | null;
  evidence_state: EvidenceState;
  citations: CitationOut[];
  related_sections: RelatedSectionOut[];
  abstention_reason: string | null;
  model_name: string | null;
  prompt_version: string | null;
}

/* ---------- Understanding (backed by backend/app/schemas/analysis.py) ---------- */

export interface EvidenceReference {
  clause_id: string | null;
  clause_number: string | null;
  title: string | null;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  source: string | null;
}

export interface AttentionItemOut {
  id: string;
  analysis_id: string;
  clause_id: string | null;
  title: string;
  description: string;
  attention_level: AttentionLevel;
  category: string | null;
  recommendation: string | null;
  status: string;
  created_at: string | null;
}

export interface EntityReference {
  type: string;
  value: string;
  normalized: string | null;
  clause_id: string | null;
  page_start: number | null;
  page_end: number | null;
}

export interface UnderstandingSummary {
  evidence_state: EvidenceState;
  overview: string | null;
  document_type: string | null;
  purpose: string | null;
  parties: string[];
  key_terms: string[];
  obligations: string[];
  important_conditions: string[];
  evidence: EvidenceReference[];
}

export interface ImportantClause {
  clause_id: string | null;
  clause_number: string | null;
  title: string | null;
  clause_type: string | null;
  original_text: string;
  explanation: string;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  source: string | null;
}

export interface DocumentUnderstandingOut {
  document_id: string;
  evidence_state: EvidenceState;
  summary: UnderstandingSummary | null;
  parties: string[];
  obligations: string[];
  important_dates: EntityReference[];
  monetary_terms: EntityReference[];
  termination: ImportantClause[];
  confidentiality: ImportantClause[];
  important_clauses: ImportantClause[];
  attention_items: AttentionItemOut[];
  abstention_reason: string | null;
  analysis_unavailable: string | null;
}

/* ---------- Comparison ---------- */

export interface ChangeCitationOut {
  document_id: string;
  section_id: string | null;
  clause_id: string | null;
  section: string;
  clause: string | null;
  page_start: number | null;
  page_end: number | null;
  source_text: string;
}

export type ChangeType = "ADDED" | "REMOVED" | "MODIFIED" | "UNCHANGED";

export type RelativeImportance = "LOW" | "MEDIUM" | "HIGH";

export interface ChangeOut {
  type: ChangeType;
  section: string;
  clause: string | null;
  before: string | null;
  after: string | null;
  explanation: string;
  importance: RelativeImportance | null;
  citation_a: ChangeCitationOut | null;
  citation_b: ChangeCitationOut | null;
}

export interface ComparisonOut {
  comparison_id: string;
  document_a_id: string;
  document_b_id: string;
  status: string;
  summary: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ComparisonChangesData {
  comparison_id: string;
  changes: ChangeOut[];
}

/* ---------- Action Center ---------- */

export interface ActionSource {
  section: string | null;
  clause: string | null;
  page_start: number | null;
  page_end: number | null;
}

export interface ActionOut {
  id: string;
  document_id: string;
  attention_item_id: string | null;
  action_type: ActionType;
  title: string;
  description: string | null;
  priority: Priority;
  status: ActionStatus;
  due_date: string | null;
  source: ActionSource;
  created_at: string | null;
}

export interface ImportantDate {
  value: string;
  normalized: string | null;
  label: string | null;
  source: ActionSource;
}

export interface ProfessionalQuestion {
  question: string;
  source: ActionSource;
}

export interface ProfessionalQuestionsOut {
  evidence_state: EvidenceState;
  questions: ProfessionalQuestion[];
  abstention_reason: string | null;
}

export interface ActionCenterOut {
  document_id: string;
  checklist: ActionOut[];
  follow_ups: ActionOut[];
  important_dates: ImportantDate[];
  evidence_state: EvidenceState;
  abstention_reason: string | null;
}

export interface ReportOut {
  report_id: string;
  document_id: string;
  report_type: string;
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

export interface ReportDownloadOut {
  report_id: string;
  download_url: string;
}