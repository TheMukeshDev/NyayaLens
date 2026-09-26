/**
 * Seed data for demo mode.
 *
 * Demo mode exists so the whole workspace can be explored without a Supabase
 * project, an AI provider or a deployed backend. That only works if the data
 * behind the screens is rich enough to exercise them, so this file provides a
 * small but realistic workspace: two versions of the same employment agreement
 * (which gives the comparison screen something meaningful to diff), a mutual
 * NDA, and a document that is still being processed.
 */

import type {
  ActionOut,
  AttentionItemOut,
  DocumentOut,
  RelativeImportance,
  ReportOut,
  UnderstandingSummary,
} from "@/lib/types";

/** A clause of a demo document, kept in the shape the comparison diff needs. */
export interface DemoClause {
  clause_number: string;
  section: string;
  title: string;
  original_text: string;
  explanation: string;
  page_start: number;
  page_end: number;
  /**
   * What the revision to this clause changed and why it matters. The comparison
   * screen prefers this over its generic wording, so a seeded revision reads
   * like a real diff instead of "this clause was reworded".
   */
  revision_note?: string;
  importance?: RelativeImportance;
}

export interface DemoAnalysis {
  summary: UnderstandingSummary;
  clauses: DemoClause[];
  attention: AttentionItemOut[];
}

export interface DemoState {
  documents: DocumentOut[];
  analyses: Record<string, DemoAnalysis>;
  actions: ActionOut[];
  reports: ReportOut[];
  comparisons: Record<string, ComparisonRecord>;
}

export interface ComparisonRecord {
  comparison_id: string;
  document_a_id: string;
  document_b_id: string;
  created_at: number;
}

const EMPLOYMENT_V1 = "11111111-1111-4111-8111-111111111111";
const EMPLOYMENT_V2 = "22222222-2222-4222-8222-222222222222";
const NDA = "33333333-3333-4333-8333-333333333333";
const LEASE = "44444444-4444-4444-8444-444444444444";

export const DEMO_DOCUMENT_IDS = {
  employmentV1: EMPLOYMENT_V1,
  employmentV2: EMPLOYMENT_V2,
  nda: NDA,
  lease: LEASE,
} as const;

const ANALYSIS_ID = (documentId: string, kind: string) => `analysis-${documentId}-${kind}`;

function attentionItem(
  documentId: string,
  index: number,
  title: string,
  description: string,
  level: AttentionItemOut["attention_level"],
  category: string,
  recommendation: string,
  clauseId: string | null,
): AttentionItemOut {
  return {
    id: `attention-${documentId}-${index}`,
    analysis_id: ANALYSIS_ID(documentId, "attention"),
    clause_id: clauseId,
    title,
    description,
    attention_level: level,
    category,
    recommendation,
    status: "OPEN",
    created_at: "2026-09-20T09:15:00.000Z",
  };
}

const EMPLOYMENT_PARTIES = ["Acme Analytics Private Limited", "Priya Raman"];
const EMPLOYMENT_KEY_TERMS = [
  "₹1,450,000 base salary, paid monthly in arrears",
  "40 hours per week, flexible working at the Company's discretion",
  "30 days' notice, or 3 months' pay in lieu",
  "12-month non-compete covering direct competitors in India",
  "Confidentiality obligations that survive termination",
];

function employmentSummary(
  documentId: string,
  overview: string,
  obligations: string[],
  conditions: string[],
): UnderstandingSummary {
  return {
    evidence_state: "DOCUMENT-GROUNDED",
    overview,
    document_type: "employment agreement",
    purpose:
      overview,
    parties: [...EMPLOYMENT_PARTIES],
    key_terms: [...EMPLOYMENT_KEY_TERMS],
    obligations,
    important_conditions: conditions,
    evidence: [],
  };
}

const EMPLOYMENT_V1_CLAUSES: DemoClause[] = [
  {
    clause_number: "1",
    section: "Section 1",
    title: "Appointment",
    original_text:
      "The Company appoints the Employee as Senior Data Analyst with effect from 1 April 2026. The role is permanent and full-time.",
    explanation:
      "Confirms the role, its start date and that the employment is permanent rather than fixed term.",
    page_start: 1,
    page_end: 1,
  },
  {
    clause_number: "2",
    section: "Section 2",
    title: "Compensation",
    original_text:
      "The Employee's base salary is ₹1,450,000 per annum, paid monthly in arrears on the 5th business day. The Company may alter the Employee's compensation on 14 days' written notice.",
    explanation:
      "Sets the base salary and payroll date, but also lets the Company change compensation on 14 days' notice, which is unusually short.",
    page_start: 1,
    page_end: 2,
  },
  {
    clause_number: "3",
    section: "Section 3",
    title: "Working Hours",
    original_text:
      "The Employee shall work 40 hours per week, exclusive of breaks. Flexible working may be approved at the Company's discretion.",
    explanation:
      "Fixes the standard week and makes any flexible arrangement discretionary rather than an entitlement.",
    page_start: 2,
    page_end: 2,
  },
  {
    clause_number: "4",
    section: "Section 4",
    title: "Confidentiality",
    original_text:
      "The Employee shall keep confidential all Confidential Information of the Company and shall not use it other than for the purposes of the role, both during and after employment.",
    explanation:
      "Broad confidentiality duty that outlives the employment. The original draft has no carve-out for legally protected disclosures.",
    page_start: 2,
    page_end: 3,
  },
  {
    clause_number: "5",
    section: "Section 5",
    title: "Termination",
    original_text:
      "Either party may terminate the employment by giving 30 days' written notice, or 3 months' pay in lieu. The Company may terminate for cause without notice.",
    explanation:
      "Standard 30-day notice for either side, with a wider 'for cause' exception reserved to the Company.",
    page_start: 3,
    page_end: 3,
  },
  {
    clause_number: "6",
    section: "Section 6",
    title: "Restrictive Covenants",
    original_text:
      "For 12 months after termination the Employee shall not work for any direct competitor of the Company within India, without the Company's prior written consent.",
    explanation:
      "A 12-month non-compete across all of India, defined by reference to undefined 'direct competitors'.",
    page_start: 3,
    page_end: 4,
    revision_note:
      "The whole clause was deleted in the revised draft, so the 12-month India-wide non-compete no longer applies. This is the single largest change between the two versions.",
    importance: "HIGH",
  },
];

const EMPLOYMENT_V2_CLAUSES: DemoClause[] = [
  EMPLOYMENT_V1_CLAUSES[0],
  EMPLOYMENT_V1_CLAUSES[2],
  {
    clause_number: "2",
    section: "Section 2",
    title: "Compensation",
    original_text:
      "The Employee's base salary is ₹1,580,000 per annum, paid monthly in arrears on the 5th business day. The Company may alter the Employee's compensation only with the Employee's written consent, and in any event on 60 days' written notice.",
    explanation:
      "Raises the base salary and replaces the unilateral 14-day notice with a consent requirement and 60 days' notice.",
    page_start: 1,
    page_end: 2,
    revision_note:
      "Your pay goes up by ₹1,300,000 a year, and the Company can no longer change it on its own. A unilateral change now needs your written consent and 60 days' notice, up from 14.",
    importance: "HIGH",
  },
  {
    clause_number: "4",
    section: "Section 4",
    title: "Confidentiality",
    original_text:
      "The Employee shall keep confidential all Confidential Information of the Company and shall not use it other than for the purposes of the role, both during and after employment. Nothing in this clause prevents the Employee from making a protected disclosure to a regulator or from exercising rights under applicable whistleblower legislation.",
    explanation:
      "Same confidentiality duty, now with an express carve-out for protected disclosures and statutory whistleblower rights.",
    page_start: 2,
    page_end: 3,
    revision_note:
      "The duty itself is unchanged, but the revised draft adds an express carve-out. You can now make a protected disclosure to a regulator and exercise statutory whistleblower rights without breaching this clause.",
    importance: "MEDIUM",
  },
  {
    clause_number: "5",
    section: "Section 5",
    title: "Termination",
    original_text:
      "Either party may terminate the employment by giving 60 days' written notice, or salary in lieu of notice. The Company may terminate for cause without notice, and the parties may agree to end the employment at any time by written consent.",
    explanation:
      "Extends notice to 60 days, removes the fixed 3-month pay-in-lieu formula, and adds a mutual written-consent exit.",
    page_start: 3,
    page_end: 3,
    revision_note:
      "Notice doubles from 30 days to 60 days on both sides, and a mutual written-consent exit is added. The fixed 3-months-pay-in-lieu formula is replaced by 'salary in lieu of notice', which leaves the amount open to agree rather than fixed.",
    importance: "MEDIUM",
  },
  {
    clause_number: "7",
    section: "Section 7",
    title: "Post-termination Assistance",
    original_text:
      "For 30 days after termination the Employee shall provide reasonable assistance with the handover of their work, at the Company's cost.",
    explanation:
      "Adds a bounded, paid handover obligation after the employment ends.",
    page_start: 4,
    page_end: 4,
    revision_note:
      "A new obligation: 30 days of reasonable handover help after you leave. It is bounded and the Company pays for it, but it is a duty that did not exist in the original draft.",
    importance: "LOW",
  },
];

const NDA_CLAUSES: DemoClause[] = [
  {
    clause_number: "1",
    section: "Section 1",
    title: "Purpose",
    original_text:
      "The parties wish to explore a commercial partnership and may disclose Confidential Information to each other solely for that purpose.",
    explanation:
      "Defines the permitted purpose, which every later obligation is measured against.",
    page_start: 1,
    page_end: 1,
  },
  {
    clause_number: "2",
    section: "Section 2",
    title: "Confidential Information",
    original_text:
      "Confidential Information means all non-public information disclosed in any form that is marked confidential or that a reasonable person would understand to be confidential.",
    explanation:
      "A purpose-based definition rather than an exhaustive list, so unmarked disclosures can still be covered.",
    page_start: 1,
    page_end: 2,
  },
  {
    clause_number: "3",
    section: "Section 3",
    title: "Term and Survival",
    original_text:
      "This Agreement continues for 2 years. The confidentiality obligations survive for 3 years after the Agreement ends.",
    explanation:
      "Two-year term with a three-year tail on confidentiality, which outlasts the agreement itself.",
    page_start: 2,
    page_end: 2,
  },
];

const LEASE_CLAUSES: DemoClause[] = [
  {
    clause_number: "1",
    section: "Section 1",
    title: "The Property",
    original_text:
      "The Landlord lets the Tenant the residential flat at 12B Riverside Apartments, together with one parking bay.",
    explanation: "Identifies the let property and what comes with it.",
    page_start: 1,
    page_end: 1,
  },
  {
    clause_number: "2",
    section: "Section 2",
    title: "Rent and Deposit",
    original_text:
      "The monthly rent is ₹48,000, payable in advance on the 1st of each month. The Tenant shall pay a security deposit equal to two months' rent.",
    explanation: "Rent is due in advance, and the deposit is two months rather than the more common one or three.",
    page_start: 1,
    page_end: 2,
  },
  {
    clause_number: "3",
    section: "Section 3",
    title: "Rent Review",
    original_text:
      "The Landlord may increase the rent on each anniversary of the commencement date by giving 60 days' written notice, with no cap on the increase.",
    explanation:
      "Uncapped annual rent review at the Landlord's sole discretion, which is the main risk in this draft.",
    page_start: 2,
    page_end: 2,
  },
];

const EMPLOYMENT_V1_SUMMARY = employmentSummary(
  EMPLOYMENT_V1,
  "This is the original version of a permanent employment agreement for a Senior Data Analyst role at Acme Analytics. It pays ₹1,450,000 per annum and can be ended on 30 days' notice by either side. The two provisions worth pushing back on are the Company's right to change your compensation on 14 days' notice, and a 12-month non-compete covering every direct competitor in India.",
  [
    "Work 40 hours per week, exclusive of breaks.",
    "Keep all Company Confidential Information confidential, during and after employment.",
    "Give 30 days' written notice to end the employment, or forgo 3 months' pay in lieu.",
    "Do not work for a direct competitor of the Company in India for 12 months after leaving.",
  ],
  [
    "The Company may alter compensation on 14 days' written notice.",
    "The non-compete applies to any 'direct competitor' without a defined list.",
  ],
);

const EMPLOYMENT_V2_SUMMARY = employmentSummary(
  EMPLOYMENT_V2,
  "This is the revised version of the same employment agreement. The changes are favourable overall: the salary rises to ₹1,580,000, compensation can no longer be changed unilaterally, notice periods lengthen to 60 days, the non-compete is gone, and confidentiality gains a protected-disclosure carve-out. The trade-off is a new 30-day post-termination handover obligation, which is paid by the Company.",
  [
    "Work 40 hours per week, exclusive of breaks.",
    "Keep all Company Confidential Information confidential, during and after employment, subject to the protected-disclosure carve-out.",
    "Give 60 days' written notice to end the employment.",
    "Provide 30 days of reasonable handover assistance after leaving, at the Company's cost.",
  ],
  [
    "Compensation changes now require the Employee's written consent and 60 days' notice.",
    "The 12-month non-compete has been removed in full.",
  ],
);

const NDA_SUMMARY: UnderstandingSummary = {
  evidence_state: "DOCUMENT-GROUNDED",
  overview:
    "A mutual non-disclosure agreement for an exploratory commercial partnership. It runs for two years and its confidentiality obligations survive a further three years, so the tail on those obligations is longer than the agreement itself.",
  document_type: "nda",
  purpose:
    "A mutual non-disclosure agreement for an exploratory commercial partnership. It runs for two years and its confidentiality obligations survive a further three years.",
  parties: ["Northwind Ventures Limited", "Acme Analytics Private Limited"],
  key_terms: [
    "2-year term, 3-year confidentiality tail",
    "Purpose-based definition of Confidential Information",
    "Mutual obligations — neither party is favoured",
  ],
  obligations: [
    "Use the other party's Confidential Information only for the stated purpose.",
    "Protect Confidential Information for 3 years after the agreement ends.",
  ],
  important_conditions: [
    "Obligations survive the agreement, so termination does not release you.",
    "No carve-out for information already public or independently developed.",
  ],
  evidence: [],
};

const LEASE_SUMMARY: UnderstandingSummary = {
  evidence_state: "DOCUMENT-GROUNDED",
  overview:
    "A residential tenancy for a two-bedroom flat at 12B Riverside with one parking bay, at ₹48,000 per month on a two-month deposit. The provision to watch is the uncapped annual rent review at the Landlord's sole discretion.",
  document_type: "lease",
  purpose:
    "A residential tenancy for a two-bedroom flat at 12B Riverside with one parking bay, at ₹48,000 per month on a two-month deposit.",
  parties: ["Riverside Holdings LLP", "Aarav Menon"],
  key_terms: [
    "₹48,000 monthly rent, payable in advance",
    "Two months' rent as security deposit",
    "Uncapped annual rent review at the Landlord's discretion",
  ],
  obligations: [
    "Pay rent in advance on the 1st of each month.",
    "Return the flat in the condition it was let in.",
  ],
  important_conditions: [
    "The Landlord may raise the rent on each anniversary with 60 days' notice, with no cap.",
    "The deposit is two months' rent, which is higher than a one-month deposit.",
  ],
  evidence: [],
};

const EMPLOYMENT_V1_ATTENTION: AttentionItemOut[] = [
  attentionItem(
    EMPLOYMENT_V1,
    1,
    "Compensation can change on 14 days' notice",
    "Section 2 lets the Company alter your compensation on 14 days' written notice, with no requirement that you agree and no cap on the change.",
    "HIGH",
    "Compensation",
    "Ask for a minimum notice period of 60 days and an annual cap tied to a published index.",
    "clause-2",
  ),
  attentionItem(
    EMPLOYMENT_V1,
    2,
    "Uncapped 12-month non-compete",
    "Section 6 bars work for any 'direct competitor' anywhere in India for 12 months after leaving, without defining who counts as a competitor.",
    "HIGH",
    "Restrictive covenants",
    "Try to narrow the list to named competitors, limit it to roles you actually do, and shorten it to 6 months.",
    "clause-6",
  ),
  attentionItem(
    EMPLOYMENT_V1,
    3,
    "No protected-disclosure carve-out",
    "Section 4 makes confidentiality obligations absolute, with nothing reserved for whistleblowing to a regulator.",
    "MEDIUM",
    "Confidentiality",
    "Add an express carve-out for protected disclosures and for exercising rights under whistleblower legislation.",
    "clause-4",
  ),
];

const EMPLOYMENT_V2_ATTENTION: AttentionItemOut[] = [
  attentionItem(
    EMPLOYMENT_V2,
    1,
    "New post-termination handover duty",
    "Section 7 adds 30 days of reasonable handover assistance after the employment ends. It is paid by the Company, but it is a new obligation that did not exist in the original draft.",
    "LOW",
    "Post-termination",
    "No change needed, but confirm the Company's cost obligation covers your time and expenses.",
    "clause-7",
  ),
];

const NDA_ATTENTION: AttentionItemOut[] = [
  attentionItem(
    NDA,
    1,
    "Confidentiality tail outlasts the agreement",
    "The agreement runs for 2 years but the confidentiality obligations survive a further 3 years, so the obligations last 5 years in total.",
    "MEDIUM",
    "Term",
    "Check you can meet the 5-year tail, and ask for standard exclusions for public or independently developed information.",
    "clause-3",
  ),
];

function iso(daysAgo: number, hours = 9): string {
  const value = new Date();
  value.setDate(value.getDate() - daysAgo);
  value.setHours(hours, 24, 0, 0);
  return value.toISOString();
}

function document(
  id: string,
  filename: string,
  displayName: string,
  status: DocumentOut["status"],
  pageCount: number | null,
  uploadedDaysAgo: number,
): DocumentOut {
  return {
    id,
    filename,
    display_name: displayName,
    mime_type: "application/pdf",
    file_size_bytes: pageCount ? pageCount * 48_000 + 12_345 : 214_000,
    status,
    processing_error: null,
    page_count: pageCount,
    checksum_sha256: null,
    uploaded_at: iso(uploadedDaysAgo),
    created_at: iso(uploadedDaysAgo),
    updated_at: iso(uploadedDaysAgo),
  };
}

const SEED_ACTIONS: ActionOut[] = [
  {
    id: "action-employ-v1-1",
    document_id: EMPLOYMENT_V1,
    attention_item_id: "attention-11111111-1111-4111-8111-111111111111-1",
    action_type: "NEGOTIATE_TERM",
    title: "Negotiate the 14-day compensation notice",
    description:
      "Section 2 allows a unilateral pay change on 14 days' notice. Ask for 60 days and a written-consent requirement.",
    priority: "HIGH",
    status: "TODO",
    due_date: null,
    source: { section: "Section 2", clause: "Clause 2", page_start: 1, page_end: 2 },
    created_at: iso(6),
  },
  {
    id: "action-employ-v1-2",
    document_id: EMPLOYMENT_V1,
    attention_item_id: "attention-11111111-1111-4111-8111-111111111111-2",
    action_type: "ASK_PROFESSIONAL",
    title: "Get a view on the non-compete's enforceability",
    description:
      "A 12-month India-wide non-compete is likely wider than necessary. A local lawyer can advise on narrowing it.",
    priority: "HIGH",
    status: "IN_PROGRESS",
    due_date: null,
    source: { section: "Section 6", clause: "Clause 6", page_start: 3, page_end: 4 },
    created_at: iso(6),
  },
  {
    id: "action-employ-v1-3",
    document_id: EMPLOYMENT_V1,
    attention_item_id: "attention-11111111-1111-4111-8111-111111111111-3",
    action_type: "REVIEW_CLAUSE",
    title: "Add a protected-disclosure carve-out to Section 4",
    description:
      "Reserve rights to make protected disclosures and to report wrongdoing to a regulator.",
    priority: "MEDIUM",
    status: "TODO",
    due_date: null,
    source: { section: "Section 4", clause: "Clause 4", page_start: 2, page_end: 3 },
    created_at: iso(6),
  },
  {
    id: "action-nda-1",
    document_id: NDA,
    attention_item_id: "attention-33333333-3333-4333-8333-333333333333-1",
    action_type: "VERIFY_INFORMATION",
    title: "Confirm you can meet the 3-year confidentiality tail",
    description:
      "Obligations run to 5 years in total. Confirm nothing in your information handling conflicts with that.",
    priority: "MEDIUM",
    status: "COMPLETED",
    due_date: null,
    source: { section: "Section 3", clause: "Clause 3", page_start: 2, page_end: 2 },
    created_at: iso(4),
  },
  {
    id: "action-nda-2",
    document_id: NDA,
    attention_item_id: null,
    action_type: "COLLECT_DOCUMENT",
    title: "Collect the signed NDA counterpart",
    description: "Ask Northwind Ventures for the fully signed copy for your records.",
    priority: "LOW",
    status: "TODO",
    due_date: null,
    source: { section: null, clause: null, page_start: null, page_end: null },
    created_at: iso(4),
  },
];

const SEED_REPORTS: ReportOut[] = [
  {
    report_id: "report-employ-v1",
    document_id: EMPLOYMENT_V1,
    report_type: "review_summary",
    status: "READY",
    created_at: iso(5),
    completed_at: iso(5),
  },
  {
    report_id: "report-nda",
    document_id: NDA,
    report_type: "review_summary",
    status: "READY",
    created_at: iso(3),
    completed_at: iso(3),
  },
];

/** Builds a fresh demo workspace. Called once per process. */
export function createDemoState(): DemoState {
  // The lease sits mid-pipeline so the processing screen has something to poll.
  // Its clock has to start when the workspace is created, not on a fixed
  // calendar date, otherwise it would arrive at READY the moment it is seeded.
  const now = new Date().toISOString();

  return {
    documents: [
      document(
        EMPLOYMENT_V2,
        "acme-employment-agreement-revised.pdf",
        "Employment Agreement — Acme Analytics (revised)",
        "READY",
        4,
        1,
      ),
      document(
        EMPLOYMENT_V1,
        "acme-employment-agreement-original.pdf",
        "Employment Agreement — Acme Analytics (original)",
        "READY",
        4,
        6,
      ),
      document(NDA, "northwind-mutual-nda-draft.pdf", "Mutual NDA — Northwind (draft)", "READY", 2, 4),
      document(
        LEASE,
        "riverside-tenancy-agreement.pdf",
        "Tenancy Agreement — 12B Riverside",
        "UPLOADED",
        null,
        0,
      ),
    ].map((item) =>
      item.id === LEASE
        ? { ...item, uploaded_at: now, created_at: now, updated_at: now }
        : item,
    ),
    analyses: {
      [EMPLOYMENT_V1]: {
        summary: EMPLOYMENT_V1_SUMMARY,
        clauses: EMPLOYMENT_V1_CLAUSES,
        attention: EMPLOYMENT_V1_ATTENTION,
      },
      [EMPLOYMENT_V2]: {
        summary: EMPLOYMENT_V2_SUMMARY,
        clauses: EMPLOYMENT_V2_CLAUSES,
        attention: EMPLOYMENT_V2_ATTENTION,
      },
      [NDA]: { summary: NDA_SUMMARY, clauses: NDA_CLAUSES, attention: NDA_ATTENTION },
      [LEASE]: { summary: LEASE_SUMMARY, clauses: LEASE_CLAUSES, attention: [] },
    },
    actions: SEED_ACTIONS.map((action) => ({ ...action })),
    reports: SEED_REPORTS.map((report) => ({ ...report })),
    comparisons: {},
  };
}
