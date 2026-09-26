/**
 * Demo-mode API.
 *
 * In demo mode there is no Supabase project, no access token and no reachable
 * backend, so every API call the app makes would fail authentication. This
 * module implements the same endpoints the FastAPI backend exposes, returns the
 * same `{ success, data }` envelope, and keeps the resulting workspace in
 * process memory. The browser reaches it over `app/api/demo/[...path]`, so the
 * Client Components and the Server Components read and write the same state.
 *
 * Two consequences are deliberate and worth knowing:
 *
 *   1. The workspace lives in process memory, so it resets whenever the server
 *      restarts and is per-instance on a serverless host. That is the right
 *      trade for a demo: seeded content, no persistence to leak.
 *   2. Nothing here calls an AI provider. Analysis text is authored in
 *      `seed.ts` and the Q&A endpoint matches question keywords against clause
 *      text, so answers are clearly sample output rather than generated.
 */

import { DEMO_EMAIL } from "@/lib/supabase/config";
import type {
  ActionCenterOut,
  ActionOut,
  ActionSource,
  ActionStatus,
  ActionType,
  ApiError,
  ChangeOut,
  ComparisonChangesData,
  ComparisonOut,
  CitationOut,
  DocumentOut,
  DocumentStatus,
  DocumentStatusData,
  DocumentUploadTicket,
  DocumentListData,
  EvidenceState,
  ImportantClause,
  Pagination,
  ProfessionalQuestionsOut,
  QAAnswerOut,
  RelativeImportance,
  ReportDownloadOut,
  ReportOut,
  UnderstandingSummary,
  UploadIntentData,
  UserOut,
} from "@/lib/types";

import {
  createDemoState,
  type ComparisonRecord,
  type DemoAnalysis,
  type DemoClause,
  type DemoState,
} from "./seed";

export interface DemoHttpResponse {
  status: number;
  body: unknown;
  contentType?: string;
  /** When true the body is written verbatim instead of as a JSON envelope. */
  raw?: boolean;
}

let workspace: DemoState | null = null;

function store(): DemoState {
  if (!workspace) workspace = createDemoState();
  return workspace;
}

/** Test seam: drops the in-memory workspace so the next read re-seeds it. */
export function resetDemoWorkspace(): void {
  workspace = null;
}

/* ---------- envelopes ---------- */

function ok<T>(data: T, message: string | null = null): DemoHttpResponse {
  return { status: 200, body: { success: true, data, message } };
}

function created<T>(data: T, message: string | null = null): DemoHttpResponse {
  return { status: 201, body: { success: true, data, message } };
}

function fail(status: number, code: string, message: string): DemoHttpResponse {
  const error: ApiError = { code, message, details: null };
  return { status, body: { success: false, error } };
}

const NOT_FOUND = (what: string) =>
  fail(404, "DOCUMENT_NOT_FOUND", `The ${what} could not be found.`);
const REPORT_NOT_FOUND = () =>
  fail(404, "REPORT_NOT_FOUND", "The report could not be found.");
const COMPARISON_NOT_FOUND = () =>
  fail(404, "COMPARISON_NOT_FOUND", "The comparison could not be found.");
const ACTION_NOT_FOUND = () => fail(404, "ACTION_NOT_FOUND", "The action could not be found.");

/* ---------- processing ---------- */

/** The stages a document walks through, and how long each one takes. */
const STAGES: DocumentStatus[] = ["VALIDATING", "PROCESSING", "EXTRACTING", "ANALYZING"];
const STAGE_MS = 4_000;

/**
 * Demo processing is time-driven rather than queued: a document that is not yet
 * `READY` walks the stages as the clock advances, so the processing screen polls
 * and genuinely progresses instead of hanging on a screen that never resolves.
 */
function advance(document: DocumentOut): DocumentOut {
  if (document.status === "READY" || document.status === "FAILED") return document;

  const startedAt = new Date(document.updated_at ?? document.created_at ?? 0).getTime();
  const elapsed = Date.now() - startedAt;
  const index = Math.min(STAGES.length, Math.floor(elapsed / STAGE_MS));
  const next = STAGES[index];

  if (!next) {
    document.status = "READY";
  } else if (next !== document.status) {
    document.status = next;
    document.updated_at = new Date(startedAt + index * STAGE_MS).toISOString();
  }
  return document;
}

const STATUS_MESSAGES: Record<string, string> = {
  UPLOADED: "Waiting to start processing.",
  VALIDATING: "Checking the file type and contents.",
  PROCESSING: "Reading the text of your document.",
  EXTRACTING: "Pulling out sections and clauses.",
  ANALYZING: "Generating the summary and attention items.",
};

function statusPayload(document: DocumentOut): DocumentStatusData {
  const resolved = advance(document);
  const index = STAGES.indexOf(resolved.status);
  const progress =
    resolved.status === "READY"
      ? 100
      : resolved.status === "FAILED"
        ? null
        : Math.round(((index + 1) / (STAGES.length + 1)) * 100);
  return {
    id: resolved.id,
    status: resolved.status,
    message: resolved.status === "READY" ? "Analysis complete." : (STATUS_MESSAGES[resolved.status] ?? null),
    progress,
  };
}

/* ---------- lookups ---------- */

function analysis(documentId: string): DemoAnalysis | null {
  return store().analyses[documentId] ?? null;
}

function findDocument(documentId: string): DocumentOut | null {
  const found = store().documents.find((item) => item.id === documentId);
  return found ? advance(found) : null;
}

function requireDocument(documentId: string): DocumentOut | DemoHttpResponse {
  const found = findDocument(documentId);
  return found ?? NOT_FOUND("document");
}

function isResponse(value: unknown): value is DemoHttpResponse {
  return typeof value === "object" && value !== null && "status" in value && "body" in value;
}

function toImportantClause(documentId: string, clause: DemoClause): ImportantClause {
  return {
    clause_id: clauseKey(documentId, clause),
    clause_number: clause.clause_number,
    title: clause.title,
    clause_type: "OBLIGATION",
    original_text: clause.original_text,
    explanation: clause.explanation,
    section: clause.section,
    page_start: clause.page_start,
    page_end: clause.page_end,
    source: clause.title,
  };
}

function clauseKey(documentId: string, clause: DemoClause): string {
  return `clause-${documentId.slice(0, 8)}-${clause.clause_number}`;
}

function clauseSource(clause: DemoClause): ActionSource {
  return {
    section: clause.section,
    clause: `Clause ${clause.clause_number}`,
    page_start: clause.page_start,
    page_end: clause.page_end,
  };
}

/* ---------- comparison ---------- */

function normalise(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function citationFor(
  documentId: string,
  clause: DemoClause,
): ChangeOut["citation_a"] {
  return {
    document_id: documentId,
    section_id: null,
    clause_id: clauseKey(documentId, clause),
    section: clause.section,
    clause: `Clause ${clause.clause_number} — ${clause.title}`,
    page_start: clause.page_start,
    page_end: clause.page_end,
    source_text: clause.original_text,
  };
}

const REMOVED_EXPLANATION =
  "This clause is present in version A and no longer appears in version B, so it was deleted rather than reworded.";

const ADDED_EXPLANATION =
  "This clause does not appear in version A and is new in version B.";

const MODIFIED_EXPLANATION =
  "This clause was reworded in version B. The wording above has changed, which is the substantive difference between the two drafts.";

const UNCHANGED_EXPLANATION = "This clause is worded identically in both versions.";

const IMPORTANCE: Record<ChangeOut["type"], RelativeImportance> = {
  ADDED: "MEDIUM",
  REMOVED: "HIGH",
  MODIFIED: "MEDIUM",
  UNCHANGED: "LOW",
};

/**
 * Deterministic structural diff: clauses are matched on their number, then on
 * whether the text is byte-identical. Authored notes on the seeded clauses take
 * precedence over the generic explanation so the seeded revision reads the way
 * a real comparison would.
 */
function buildChanges(aId: string, bId: string): ChangeOut[] {
  const a = analysis(aId);
  const b = analysis(bId);
  if (!a || !b) return [];

  const aByNumber = new Map(a.clauses.map((clause) => [clause.clause_number, clause]));
  const bByNumber = new Map(b.clauses.map((clause) => [clause.clause_number, clause]));
  const numbers = [...new Set([...aByNumber.keys(), ...bByNumber.keys()])].sort(
    (x, y) => Number(x) - Number(y),
  );

  const changes: ChangeOut[] = [];

  for (const number of numbers) {
    const before = aByNumber.get(number) ?? null;
    const after = bByNumber.get(number) ?? null;
    const section = after?.section ?? before?.section ?? "Document";

    let type: ChangeOut["type"];
    if (before && !after) type = "REMOVED";
    else if (!before && after) type = "ADDED";
    else if (normalise(before!.original_text) === normalise(after!.original_text)) type = "UNCHANGED";
    else type = "MODIFIED";

    const note = after?.revision_note ?? before?.revision_note ?? null;
    const explanation =
      note ??
      {
        ADDED: ADDED_EXPLANATION,
        REMOVED: REMOVED_EXPLANATION,
        MODIFIED: MODIFIED_EXPLANATION,
        UNCHANGED: UNCHANGED_EXPLANATION,
      }[type];

    changes.push({
      type,
      section,
      clause: `${after?.title ?? before?.title ?? `Clause ${number}`} (clause ${number})`,
      before: before ? before.original_text : null,
      after: after ? after.original_text : null,
      explanation,
      importance: type === "UNCHANGED" ? "LOW" : (after?.importance ?? before?.importance ?? IMPORTANCE[type]),
      citation_a: before ? citationFor(aId, before) : null,
      citation_b: after ? citationFor(bId, after) : null,
    });
  }

  return changes;
}

/* ---------- questions ---------- */

const STOP_WORDS = new Set([
  "a", "about", "does", "do", "i", "if", "in", "is", "it", "me", "my", "of", "on", "or",
  "the", "this", "to", "what", "when", "which", "who", "will", "with", "document",
  "agreement", "contract", "please", "tell", "any", "am", "are", "was", "were", "be",
  "and", "for", "from", "has", "have", "had", "can", "could", "would", "should", "my",
]);

function tokenise(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9₹]+/)
    .filter((token) => token.length > 2 && !STOP_WORDS.has(token));
}

/**
 * Keyword retrieval over the document's own clauses. A question that shares no
 * meaningful term with the document abstains rather than inventing an answer.
 */
function answerQuestion(documentId: string, question: string): QAAnswerOut {
  const analysis = store().analyses[documentId];
  const base = {
    document_id: documentId,
    related_sections: [],
    abstention_reason: null,
    model_name: "nyayalens-demo",
    prompt_version: "demo-v1",
  };

  if (!analysis) {
    return {
      ...base,
      answer: null,
      evidence_state: "INSUFFICIENT-EVIDENCE" as EvidenceState,
      citations: [],
      abstention_reason:
        "This document has no analysis yet, so there is no text to search.",
    };
  }

  const terms = tokenise(question);
  const scored = analysis.clauses
    .map((clause) => {
      const haystack = tokenise(`${clause.title} ${clause.section} ${clause.original_text}`);
      const score = terms.filter((term) => haystack.includes(term)).length;
      return { clause, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((x, y) => y.score - x.score)
    .slice(0, 2);

  if (scored.length === 0) {
    return {
      ...base,
      answer: null,
      evidence_state: "INSUFFICIENT-EVIDENCE" as EvidenceState,
      citations: [],
      abstention_reason:
        "There is not enough evidence in this document to answer that. Try asking about a specific clause, period, or obligation.",
    };
  }

  const citations: CitationOut[] = scored.map(({ clause }) => ({
    id: `citation-${documentId.slice(0, 8)}-${clause.clause_number}`,
    chunk_id: `chunk-${documentId.slice(0, 8)}-${clause.clause_number}`,
    document_id: documentId,
    section_id: null,
    clause_id: clauseKey(documentId, clause),
    section: clause.section,
    clause: `Clause ${clause.clause_number} — ${clause.title}`,
    page_start: clause.page_start,
    page_end: clause.page_end,
    source_text: clause.original_text,
  }));

  const lead = scored[0].clause;
  const answer = [
    `This document deals with ${lead.title.toLowerCase()}. ${lead.explanation}`,
    scored[1]
      ? `It also covers ${scored[1].clause.title.toLowerCase()}: ${scored[1].clause.explanation}`
      : null,
    "The cited sources below are the relevant wording, so you can check the original text yourself.",
  ]
    .filter(Boolean)
    .join(" ");

  return {
    ...base,
    answer,
    evidence_state: "DOCUMENT-GROUNDED" as EvidenceState,
    citations,
    related_sections: scored.map(({ clause }) => ({
      label: clause.title,
      section_id: null,
      page_start: clause.page_start,
      page_end: clause.page_end,
    })),
  };
}

/* ---------- action centre ---------- */

const ACTION_FOR_CATEGORY: Record<string, ActionType> = {
  Compensation: "NEGOTIATE_TERM",
  "Restrictive covenants": "ASK_PROFESSIONAL",
  Confidentiality: "REVIEW_CLAUSE",
  Term: "VERIFY_INFORMATION",
};

const FOLLOW_UP_QUESTIONS = [
  "Which of these provisions would I want a lawyer to review before signing?",
  "What would I change if I could negotiate only one clause?",
  "Are there any obligations here I would struggle to meet?",
];

function buildActionPlan(documentId: string): ActionCenterOut {
  const state = store();
  const analysis = state.analyses[documentId];
  const clauses = analysis?.clauses ?? [];
  const document = findDocument(documentId);
  const now = new Date().toISOString();

  const checklist: ActionOut[] = (analysis?.attention ?? []).map((item, index) => ({
    id: `action-${documentId.slice(0, 8)}-${index}`,
    document_id: documentId,
    attention_item_id: item.id,
    action_type: ACTION_FOR_CATEGORY[item.category ?? ""] ?? "REVIEW_CLAUSE",
    title: item.title,
    description: item.recommendation,
    priority: item.attention_level === "HIGH" ? "HIGH" : item.attention_level === "LOW" ? "LOW" : "MEDIUM",
    status: "TODO",
    due_date: null,
    source: clauseSource(clauses[index % Math.max(clauses.length, 1)] ?? clauses[0]),
    created_at: now,
  }));

  const follow_ups: ActionOut[] = FOLLOW_UP_QUESTIONS.map((title, index) => ({
    id: `action-${documentId.slice(0, 8)}-followup-${index}`,
    document_id: documentId,
    attention_item_id: null,
    action_type: index === 0 ? "ASK_PROFESSIONAL" : "FOLLOW_UP",
    title,
    description: document ? `Raised while reviewing ${document.display_name ?? document.filename}.` : null,
    priority: index === 0 ? "HIGH" : "MEDIUM",
    status: "TODO",
    due_date: null,
    source: { section: null, clause: null, page_start: null, page_end: null },
    created_at: now,
  }));

  // Replacing the plan keeps "Generate" idempotent, matching the backend, which
  // rebuilds the checklist from the latest analysis.
  state.actions = [
    ...state.actions.filter((action) => action.document_id !== documentId),
    ...checklist,
    ...follow_ups,
  ];

  return {
    document_id: documentId,
    checklist,
    follow_ups,
    important_dates: [],
    evidence_state: "DOCUMENT-GROUNDED",
    abstention_reason: null,
  };
}

function professionalQuestions(documentId: string, userContext: string | null): ProfessionalQuestionsOut {
  const analysis = store().analyses[documentId];
  const items = analysis?.attention ?? [];
  const clauses = analysis?.clauses ?? [];

  const questions = items.slice(0, 3).map((item, index) => ({
    question: userContext
      ? `Given that you mentioned "${userContext}", how should I raise ${item.title.toLowerCase()}?`
      : item.title.endsWith("?")
        ? item.title
        : `How should I raise ${item.title.toLowerCase()} with the other side?`,
    source: clauseSource(clauses[index % Math.max(clauses.length, 1)] ?? clauses[0]),
  }));

  if (questions.length === 0 && clauses.length > 0) {
    clauses.slice(0, 3).forEach((clause) => {
      questions.push({
        question: `What should I check about ${clause.title.toLowerCase()} before agreeing to it?`,
        source: clauseSource(clause),
      });
    });
  }

  return {
    evidence_state: questions.length > 0 ? "DOCUMENT-GROUNDED" : "INSUFFICIENT-EVIDENCE",
    questions,
    abstention_reason:
      questions.length > 0 ? null : "There is not enough evidence in this document to draft questions.",
  };
}

/* ---------- reports ---------- */

function reportText(report: ReportOut): string {
  const state = store();
  const document = state.documents.find((item) => item.id === report.document_id);
  const analysis = state.analyses[report.document_id];
  const actions = state.actions.filter((action) => action.document_id === report.document_id);
  const lines: string[] = [
    "NyayaLens review report",
    "=======================",
    "",
    `Document: ${document?.display_name ?? document?.filename ?? report.document_id}`,
    `Report type: ${report.report_type}`,
    `Generated: ${report.completed_at ?? report.created_at ?? ""}`,
    "",
  ];

  if (analysis) {
    lines.push("Summary", "-------", analysis.summary.purpose ?? analysis.summary.overview ?? "", "");
    if (analysis.summary.parties.length > 0) {
      lines.push("Parties", "------", ...analysis.summary.parties.map((party) => `- ${party}`), "");
    }
    lines.push("Attention items", "---------------");
    if (analysis.attention.length === 0) {
      lines.push("None were detected.", "");
    } else {
      analysis.attention.forEach((item) => {
        lines.push(`- [${item.attention_level}] ${item.title}`, `  ${item.description}`);
        if (item.recommendation) lines.push(`  Recommendation: ${item.recommendation}`);
      });
      lines.push("");
    }
  }

  if (actions.length > 0) {
    lines.push("Action plan", "----------");
    actions.forEach((action) => {
      lines.push(`- [${action.status}] [${action.priority}] ${action.title}`);
      if (action.description) lines.push(`  ${action.description}`);
    });
    lines.push("");
  }

  lines.push(
    "This report is an informational first-pass review, not legal advice. Confirm important decisions with a qualified professional.",
  );
  return lines.join("\n");
}

/* ---------- request handling ---------- */

interface ParsedPath {
  segments: string[];
  query: URLSearchParams;
}

function parsePath(path: string): ParsedPath {
  const [pathname, search = ""] = path.split("?");
  return {
    segments: pathname.split("/").filter(Boolean),
    query: new URLSearchParams(search),
  };
}

function paginate<T>(items: T[], query: URLSearchParams) {
  const page = Math.max(1, Number(query.get("page") ?? "1") || 1);
  const limit = Math.max(1, Math.min(100, Number(query.get("limit") ?? "50") || 50));
  const start = (page - 1) * limit;
  const body: Pagination = {
    page,
    limit,
    total: items.length,
    pages: Math.max(1, Math.ceil(items.length / limit)),
  };
  return { items: items.slice(start, start + limit), pagination: body };
}

/**
 * Single entry point for every demo API call. `path` is the `/api/v1`-relative
 * path (including any query string) that the real backend would have received.
 */
export function handleDemoRequest(
  method: string,
  path: string,
  body?: unknown,
): DemoHttpResponse {
  const state = store();
  const { segments, query } = parsePath(path);
  const [resource, id, sub] = segments;
  const payload = (body ?? {}) as Record<string, unknown>;

  /* --- auth --- */
  if (resource === "auth" && id === "me" && method === "GET") {
    const user: UserOut = { id: `demo-${DEMO_EMAIL}`, email: DEMO_EMAIL, role: "authenticated" };
    return ok(user);
  }

  /* --- documents --- */
  if (resource === "documents" && id === "upload-intent" && method === "POST") {
    return uploadIntent(payload);
  }

  if (resource === "documents" && !id && method === "GET") {
    const list: DocumentListData = paginate([...state.documents], query);
    for (const item of list.items) advance(item);
    return ok(list);
  }

  if (resource === "documents" && id) {
    const document = requireDocument(id);
    if (isResponse(document)) return document;

    if (!sub && method === "GET") return ok(document);

    if (sub === "status" && method === "GET") return ok(statusPayload(document));

    if (sub === "complete" && method === "POST") {
      document.status = "VALIDATING";
      document.updated_at = new Date().toISOString();
      return ok(document);
    }

    if ((sub === "process" || sub === "retry") && method === "POST") {
      document.status = "VALIDATING";
      document.processing_error = null;
      document.updated_at = new Date().toISOString();
      return ok(document);
    }

    if (sub === "summary" && method === "GET") {
      const summary = analysis(id)?.summary;
      if (!summary) {
        return fail(
          409,
          "ANALYSIS_NOT_READY",
          "The analysis for this document has not been generated yet.",
        );
      }
      return ok<UnderstandingSummary>(summary);
    }

    if (sub === "clauses" && method === "GET") {
      return ok({
        clauses: (analysis(id)?.clauses ?? []).map((clause) => toImportantClause(id, clause)),
      });
    }

    if (sub === "attention" && method === "GET") {
      return ok({ items: analysis(id)?.attention ?? [] });
    }

    if (sub === "ask" && method === "POST") {
      const question = String(payload.question ?? "").trim();
      if (!question) {
        return fail(422, "VALIDATION_ERROR", "A question is required.");
      }
      return ok(answerQuestion(id, question));
    }

    if (sub === "action-center" && method === "POST") return ok(buildActionPlan(id));

    if (sub === "questions" && segments[3] === "generate" && method === "POST") {
      return ok(professionalQuestions(id, query.get("user_context")));
    }

    if (sub === "reports" && method === "POST") {
      const report: ReportOut = {
        report_id: `report-${Date.now().toString(36)}`,
        document_id: id,
        report_type: "review_summary",
        status: "READY",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };
      state.reports = [report, ...state.reports];
      return created(report);
    }
  }

  /* --- actions --- */
  if (resource === "actions" && method === "GET" && !id) {
    const documentId = query.get("document_id");
    const matching = documentId
      ? state.actions.filter((action) => action.document_id === documentId)
      : state.actions;
    return ok(matching);
  }

  if (resource === "actions" && id && method === "PATCH") {
    const action = state.actions.find((item) => item.id === id);
    if (!action) return ACTION_NOT_FOUND();
    const status = payload.status as ActionStatus | undefined;
    if (!status) return fail(422, "VALIDATION_ERROR", "A status is required.");
    action.status = status;
    return ok(action);
  }

  /* --- reports --- */
  if (resource === "reports" && method === "GET" && !id) return ok(state.reports);

  if (resource === "reports" && id && sub === "download" && method === "GET") {
    const report = state.reports.find((item) => item.report_id === id);
    if (!report) return REPORT_NOT_FOUND();
    const download: ReportDownloadOut = {
      report_id: report.report_id,
      download_url: `/api/demo/reports/${report.report_id}/file`,
    };
    return ok(download);
  }

  if (resource === "reports" && id && sub === "file" && method === "GET") {
    const report = state.reports.find((item) => item.report_id === id);
    if (!report) return REPORT_NOT_FOUND();
    return {
      status: 200,
      body: reportText(report),
      contentType: "text/plain; charset=utf-8",
      raw: true,
    };
  }

  /* --- comparisons --- */
  if (resource === "comparisons" && method === "POST" && !id) {
    const a = String(payload.document_a_id ?? "");
    const b = String(payload.document_b_id ?? "");
    if (!a || !b) {
      return fail(422, "VALIDATION_ERROR", "Two documents are required for a comparison.");
    }
    if (a === b) {
      return fail(422, "VALIDATION_ERROR", "Choose two different documents to compare.");
    }
    if (!findDocument(a) || !findDocument(b)) return NOT_FOUND("document");

    const comparison: ComparisonRecord = {
      comparison_id: `comparison-${Date.now().toString(36)}`,
      document_a_id: a,
      document_b_id: b,
      created_at: Date.now(),
    };
    state.comparisons[comparison.comparison_id] = comparison;
    return created(comparisonOut(comparison));
  }

  if (resource === "comparisons" && id && method === "GET") {
    const comparison = state.comparisons[id];
    if (!comparison) return COMPARISON_NOT_FOUND();
    if (sub === "changes") {
      const changes: ComparisonChangesData = {
        comparison_id: comparison.comparison_id,
        changes: buildChanges(comparison.document_a_id, comparison.document_b_id),
      };
      return ok(changes);
    }
    return ok(comparisonOut(comparison));
  }

  return fail(404, "NOT_FOUND", `No demo endpoint matches ${method} ${path}.`);
}

function comparisonOut(comparison: ComparisonRecord): ComparisonOut {
  const changes = buildChanges(comparison.document_a_id, comparison.document_b_id);
  const material = changes.filter((change) => change.type !== "UNCHANGED");
  return {
    comparison_id: comparison.comparison_id,
    document_a_id: comparison.document_a_id,
    document_b_id: comparison.document_b_id,
    status: "COMPLETED",
    summary:
      material.length === 0
        ? "The two documents are identical in the sections that were compared."
        : `${material.length} of ${changes.length} clauses differ between the two versions: ` +
          material
            .map((change) => `${change.type.toLowerCase()} — ${change.clause?.split(" (")[0]}`)
            .join(", ") +
          ".",
    created_at: new Date(comparison.created_at).toISOString(),
    completed_at: new Date(comparison.created_at).toISOString(),
  };
}

function uploadIntent(payload: Record<string, unknown>): DemoHttpResponse {
  const state = store();
  const filename = String(payload.filename ?? "document.pdf");
  const now = new Date().toISOString();
  const id = `demo-${crypto.randomUUID()}`;

  const document: DocumentOut = {
    id,
    filename,
    display_name: filename.replace(/\.[^.]+$/, ""),
    mime_type: "application/pdf",
    file_size_bytes: Number(payload.size_bytes ?? 0),
    status: "UPLOADED",
    processing_error: null,
    page_count: null,
    checksum_sha256: null,
    uploaded_at: now,
    created_at: now,
    updated_at: now,
  };
  state.documents = [document, ...state.documents];

  // No Supabase Storage in demo mode, so the ticket is a placeholder the upload
  // helper never has to use: demo uploads skip the PUT and go straight to
  // `complete`.
  const upload: DocumentUploadTicket = {
    path: `demo/${id}/original`,
    token: "demo",
    signed_url: "",
    expires_in_seconds: 900,
  };

  return created({ document, upload } satisfies UploadIntentData);
}
