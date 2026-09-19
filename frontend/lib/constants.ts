import type {
  ActionStatus,
  ActionType,
  AttentionLevel,
  DocumentStatus,
  EvidenceState,
  Priority,
} from "@/lib/types";

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: "Uploaded",
  VALIDATING: "Validating",
  PROCESSING: "Processing",
  EXTRACTING: "Extracting text",
  ANALYZING: "Analyzing",
  READY: "Ready",
  FAILED: "Failed",
};

export const PROCESSING_LABELS: Record<DocumentStatus, string> = {
  UPLOADED: "Your document has been uploaded securely.",
  VALIDATING: "Checking the file and scanning for issues.",
  PROCESSING: "Preparing the document for review.",
  EXTRACTING: "Extracting text and structure.",
  ANALYZING: "Reviewing clauses and building your summary.",
  READY: "Your document is ready to review.",
  FAILED: "Processing could not be completed.",
};

export const ACTION_STATUS_LABELS: Record<ActionStatus, string> = {
  TODO: "To do",
  IN_PROGRESS: "In progress",
  COMPLETED: "Completed",
  DISMISSED: "Dismissed",
};

export const ACTION_TYPE_LABELS: Record<ActionType, string> = {
  REVIEW_CLAUSE: "Review a clause",
  ASK_PROFESSIONAL: "Ask a professional",
  COLLECT_DOCUMENT: "Collect a document",
  VERIFY_INFORMATION: "Verify information",
  NEGOTIATE_TERM: "Negotiate a term",
  FOLLOW_UP: "Follow up",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  LOW: "Low priority",
  MEDIUM: "Medium priority",
  HIGH: "High priority",
};

export const ATTENTION_LEVEL_LABELS: Record<AttentionLevel, string> = {
  LOW: "Low attention",
  MEDIUM: "Medium attention",
  HIGH: "High attention",
};

export const EVIDENCE_LABELS: Record<EvidenceState, string> = {
  "DOCUMENT-GROUNDED": "Document-grounded",
  "GENERAL-INFORMATION": "General information",
  "INSUFFICIENT-EVIDENCE": "Insufficient evidence",
};

export function documentStatusLabel(status: string): string {
  return DOCUMENT_STATUS_LABELS[status as DocumentStatus] ?? status;
}

/** Maps backend error codes to calm, readable copy (API-Specification.md §24). */
export const ERROR_MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: "Your session has expired. Please log in again.",
  INVALID_CREDENTIALS: "Your credentials could not be verified. Please log in again.",
  FORBIDDEN: "You do not have access to this resource.",
  USER_NOT_FOUND: "We could not find that account.",
  DOCUMENT_NOT_FOUND: "The document could not be found.",
  DOCUMENT_ACCESS_DENIED: "You do not have access to this document.",
  INVALID_FILE:
    "The file content does not match its file name. Choose a valid PDF, DOCX, JPG, or PNG.",
  FILE_TOO_LARGE: "The file exceeds the maximum allowed size of 20 MB.",
  UNSUPPORTED_FILE_TYPE:
    "Unsupported file type. Supported types are PDF, DOCX, JPG, and PNG.",
  MALWARE_DETECTED: "The file did not pass our security checks and was rejected.",
  PROCESSING_FAILED: "Processing could not be completed. Please try again.",
  ANALYSIS_FAILED: "The analysis could not be completed. Please try again.",
  INSUFFICIENT_EVIDENCE:
    "There is not enough evidence in the document to answer this.",
  INVALID_CITATION: "The citation could not be verified.",
  COMPARISON_FAILED: "The comparison could not be completed. Please try again.",
  RATE_LIMITED: "Too many requests. Please wait a moment and try again.",
  VALIDATION_ERROR: "The request could not be validated. Please check and try again.",
  STORAGE_ERROR: "Storage is temporarily unavailable. Please try again in a moment.",
  INTERNAL_ERROR: "Something went wrong. Please try again in a moment.",
};