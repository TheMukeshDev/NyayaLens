/**
 * Hermetic mock for the two external services the frontend talks to:
 *
 *   - Supabase Auth   (`/auth/v1/*`)   — email/password auth used by @supabase/ssr
 *   - NyayaLens API   (`/api/v1/*`)    — the FastAPI backend
 *
 * Playwright starts this process (see `playwright.config.ts`) and points the
 * Next.js dev server at it via `SUPABASE_URL` / `NEXT_PUBLIC_API_URL`.
 * That lets the whole signup -> report journey run end to end through the real
 * UI, deterministically, with no live Supabase project, database, or AI keys.
 *
 * It is a test double: it seeds one confirmed test user and simulates a
 * document moving through processing to READY.
 */
import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const PORT = Number(process.env.E2E_MOCK_PORT ?? 4010);
const ORIGIN = `http://localhost:${PORT}`;

/** The seeded user the E2E suite logs in as (see e2e/fixtures.ts). */
const SEEDED_USER = {
  id: "11111111-1111-4111-8111-111111111111",
  email: "e2e.user@example.com",
  password: "e2e-password-123",
};

/** How long a freshly uploaded document "processes" before it is READY. */
/**
 * How long a document stays in `PROCESSING` before the mock flips it to
 * `READY`. Long enough that a dev server's first-visit route compilation
 * cannot outrun it, which would redirect past the processing screen.
 */
const PROCESSING_MS = 10_000;

/* -------------------------------------------------------------------------- */
/* State                                                                      */
/* -------------------------------------------------------------------------- */

const usersByEmail = new Map();
const documents = new Map();
const actions = new Map();
const reports = new Map();
const comparisons = new Map();

/** Object "storage" behind the signed upload URLs handed out by /upload-intent. */
const uploadedObjects = new Map();

function seed() {
  usersByEmail.set(SEEDED_USER.email, { ...SEEDED_USER });
}

function seedReadyDocument() {
  const doc = {
    id: "22222222-2222-4222-8222-222222222222",
    filename: "prior-employment-agreement.pdf",
    display_name: "Prior employment agreement",
    mime_type: "application/pdf",
    file_size_bytes: 284_112,
    status: "READY",
    processing_error: null,
    page_count: 12,
    checksum_sha256: "a".repeat(64),
    uploaded_at: new Date(Date.now() - 86_400_000).toISOString(),
    created_at: new Date(Date.now() - 86_400_000).toISOString(),
    updated_at: new Date(Date.now() - 80_000_000).toISOString(),
  };
  documents.set(doc.id, { row: doc, createdMs: Date.now() - 86_400_000, ownerId: SEEDED_USER.id });
}

seed();
seedReadyDocument();

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "authorization, apikey, content-type, x-client-info, x-supabase-api-version, prefer, accept",
  "Access-Control-Expose-Headers": "content-length",
};

function send(res, status, body, extraHeaders = {}) {
  process.stderr.write(`[mock] -> ${status} ${res.req?.method} ${res.req?.url}\n`);
  const payload = body === undefined ? "" : JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    ...CORS_HEADERS,
    ...extraHeaders,
  });
  res.end(payload);
}

function readBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
  });
}

/** Ownership check — mirrors the backend's per-user scoping. */
function ownedDocument(id, userId) {
  const entry = documents.get(id);
  if (!entry || entry.ownerId !== userId) return null;
  return entry;
}

function currentStatus(entry) {
  if (entry.row.status === "READY" || entry.row.status === "FAILED") return entry.row.status;
  return Date.now() - entry.createdMs >= PROCESSING_MS ? "READY" : "PROCESSING";
}

function documentOut(entry) {
  return { ...entry.row, status: currentStatus(entry) };
}

function tokenFor(user) {
  return `mock.${Buffer.from(JSON.stringify({ sub: user.id, email: user.email })).toString("base64url")}.sig`;
}

function sessionFor(user) {
  const now = Math.floor(Date.now() / 1000);
  return {
    access_token: tokenFor(user),
    token_type: "bearer",
    expires_in: 3600,
    expires_at: now + 3600,
    refresh_token: `refresh-${user.id}`,
    user: { id: user.id, aud: "authenticated", role: "authenticated", email: user.email },
  };
}

function userFromRequest(req) {
  const header = req.headers.authorization ?? "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  const encoded = token.split(".")[1];
  if (!encoded) return null;
  try {
    const payload = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8"));
    return [...usersByEmail.values()].find((user) => user.id === payload.sub) ?? null;
  } catch {
    return null;
  }
}

/* -------------------------------------------------------------------------- */
/* Supabase Auth                                                              */
/* -------------------------------------------------------------------------- */

async function handleAuth(req, res, url) {
  const path = url.pathname.replace(/^\/auth\/v1/, "");

  if (path === "/settings" && req.method === "GET") {
    return send(res, 200, {
      external: { email: true },
      disable_signup: false,
      mailer_autoconfirm: false,
    });
  }

  if (path === "/signup" && req.method === "POST") {
    const { email, password } = JSON.parse((await readBody(req)).toString() || "{}");
    if (!email || !password) {
      return send(res, 400, { code: 400, error_code: "validation_failed", msg: "Email and password are required" });
    }
    if (String(password).length < 6) {
      return send(res, 422, {
        code: 422,
        error_code: "weak_password",
        msg: "Password should be at least 6 characters",
      });
    }
    if (!usersByEmail.has(email)) {
      usersByEmail.set(email, { id: randomUUID(), email, password });
    }
    // Email confirmation is required, so there is no session yet.
    const user = usersByEmail.get(email);
    return send(res, 200, {
      id: user.id,
      email: user.email,
      user: { id: user.id, aud: "authenticated", role: "authenticated", email: user.email },
      session: null,
    });
  }

  if (path === "/token" && req.method === "POST") {
    const grant = url.searchParams.get("grant_type");
    const body = JSON.parse((await readBody(req)).toString() || "{}");

    if (grant === "refresh_token") {
      return send(res, 200, sessionFor(SEEDED_USER));
    }

    const user = usersByEmail.get(body.email);
    if (!user || user.password !== body.password) {
      return send(res, 400, {
        error: "invalid_grant",
        error_code: "invalid_credentials",
        error_description: "Invalid login credentials",
        msg: "Invalid login credentials",
      });
    }
    return send(res, 200, sessionFor(user));
  }

  if (path === "/user" && req.method === "GET") {
    const user = userFromRequest(req);
    if (!user) {
      return send(res, 401, { code: 401, error_code: "bad_jwt", msg: "invalid claim: missing sub claim" });
    }
    return send(res, 200, {
      id: user.id,
      aud: "authenticated",
      role: "authenticated",
      email: user.email,
      app_metadata: { provider: "email", providers: ["email"] },
      user_metadata: {},
    });
  }

  if (path === "/logout" && req.method === "POST") {
    res.writeHead(204, CORS_HEADERS);
    return res.end();
  }

  return send(res, 404, { error: "not_found", path });
}

/* -------------------------------------------------------------------------- */
/* NyayaLens API                                                              */
/* -------------------------------------------------------------------------- */

function envelope(data, message = null) {
  return { success: true, data, message };
}

function apiError(res, status, code, message) {
  return send(res, status, { success: false, error: { code, message, details: null } });
}

const SUMMARY = {
  evidence_state: "DOCUMENT-GROUNDED",
  overview:
    "This is an employment agreement between the company and the employee, covering role, compensation, confidentiality and termination.",
  document_type: "employment_agreement",
  purpose: "To set out the terms of employment between the parties.",
  parties: ["Acme Corp", "Jordan Rivera"],
  key_terms: ["Notice period of 30 days", "12 month confidentiality", "Annual salary review"],
  obligations: [
    "The employee must maintain confidentiality during and after employment.",
    "The employer must provide the agreed notice period on termination.",
  ],
  important_conditions: [
    "Either party may terminate for material breach with 14 days to remedy.",
  ],
  evidence: [
    {
      clause_id: "clause-8-2",
      clause_number: "8.2",
      title: "Termination",
      section: "8",
      page_start: 6,
      page_end: 6,
      source: "Termination — 8.2, page 6",
    },
  ],
};

const ATTENTION_ITEMS = [
  {
    id: "33333333-3333-4333-8333-333333333333",
    analysis_id: "44444444-4444-4444-8444-444444444444",
    clause_id: "clause-8-2",
    title: "Short notice period on termination",
    description:
      "The agreement allows termination with 30 days notice. Consider whether a longer period is appropriate.",
    attention_level: "HIGH",
    category: "TERMINATION",
    recommendation: "Ask a professional whether 30 days is standard for this role.",
    status: "OPEN",
    created_at: null,
  },
  {
    id: "55555555-5555-4555-8555-555555555555",
    analysis_id: "44444444-4444-4444-8444-444444444444",
    clause_id: "clause-5-1",
    title: "Confidentiality survives termination",
    description: "Confidentiality obligations continue for 12 months after employment ends.",
    attention_level: "MEDIUM",
    category: "CONFIDENTIALITY",
    recommendation: null,
    status: "OPEN",
    created_at: null,
  },
];

const CLAUSES = [
  {
    clause_id: "clause-8-2",
    clause_number: "8.2",
    title: "Termination",
    clause_type: "TERMINATION",
    original_text:
      "The Employment may be terminated by either party by giving the other party not less than thirty (30) days written notice.",
    explanation:
      "Either side can end the agreement with at least 30 days written notice. This is the main exit route from the contract.",
    section: "8",
    page_start: 6,
    page_end: 6,
    source: "Termination — 8.2, page 6",
  },
  {
    clause_id: "clause-5-1",
    clause_number: "5.1",
    title: "Confidentiality",
    clause_type: "CONFIDENTIALITY",
    original_text:
      "The Employee shall not disclose any Confidential Information during employment or for twelve (12) months thereafter.",
    explanation:
      "You must keep company secrets private while employed and for a year afterwards.",
    section: "5",
    page_start: 3,
    page_end: 3,
    source: "Confidentiality — 5.1, page 3",
  },
];

const QA_ANSWER = {
  document_id: null,
  answer:
    "Either party may terminate the agreement by giving at least 30 days written notice.",
  evidence_state: "DOCUMENT-GROUNDED",
  citations: [
    {
      id: "cite-1",
      chunk_id: "chunk-8-2",
      document_id: null,
      section_id: "section-8",
      clause_id: "clause-8-2",
      section: "8",
      clause: "8.2",
      page_start: 6,
      page_end: 6,
      source_text:
        "The Employment may be terminated by either party by giving the other party not less than thirty (30) days written notice.",
    },
  ],
  related_sections: [{ label: "Termination", section_id: "section-8", page_start: 6, page_end: 6 }],
  abstention_reason: null,
  model_name: "mock-model",
  prompt_version: "v1",
};

const ACTION_OUT = {
  id: "66666666-6666-4666-8666-666666666666",
  document_id: null,
  attention_item_id: null,
  action_type: "ASK_PROFESSIONAL",
  title: "Ask a professional about the 30 day notice period",
  description: "Confirm whether 30 days notice is standard for this role.",
  priority: "HIGH",
  status: "TODO",
  due_date: null,
  source: { section: "8", clause: "8.2", page_start: 6, page_end: 6 },
  created_at: null,
};

const ACTION_OUT_2 = {
  ...ACTION_OUT,
  id: "77777777-7777-4777-8777-777777777777",
  action_type: "REVIEW_CLAUSE",
  title: "Review the confidentiality clause",
  description: "Check the 12 month post-employment confidentiality period.",
  priority: "MEDIUM",
  source: { section: "5", clause: "5.1", page_start: 3, page_end: 3 },
};

const CHANGES = [
  {
    type: "MODIFIED",
    section: "8",
    clause: "8.2",
    before: "Either party may terminate by giving thirty (30) days written notice.",
    after: "Either party may terminate by giving sixty (60) days written notice.",
    explanation: "The notice period increased from 30 to 60 days.",
    importance: "HIGH",
    citation_a: {
      document_id: null,
      section_id: "section-8",
      clause_id: "clause-8-2",
      section: "8",
      clause: "8.2",
      page_start: 6,
      page_end: 6,
      source_text: "...thirty (30) days written notice...",
    },
    citation_b: {
      document_id: null,
      section_id: "section-8",
      clause_id: "clause-8-2",
      section: "8",
      clause: "8.2",
      page_start: 7,
      page_end: 7,
      source_text: "...sixty (60) days written notice...",
    },
  },
];

async function handleApi(req, res, url) {
  const path = url.pathname.replace(/^\/api\/v1/, "");
  const user = userFromRequest(req);
  if (!user) return apiError(res, 401, "AUTH_REQUIRED", "Authentication required.");

  const segments = path.split("/").filter(Boolean);

  if (path === "/auth/me") {
    return send(res, 200, envelope({ id: user.id, email: user.email, role: "user" }));
  }

  /* ----- Documents ----- */
  if (path === "/documents/upload-intent" && req.method === "POST") {
    const { filename, size_bytes } = JSON.parse((await readBody(req)).toString() || "{}");
    if (typeof size_bytes !== "number" || size_bytes <= 0) {
      return apiError(res, 400, "INVALID_FILE", "A file is required.");
    }
    if (!/\.(pdf|docx|jpe?g|png)$/i.test(String(filename ?? ""))) {
      return apiError(res, 415, "UNSUPPORTED_FILE_TYPE", "Unsupported file type.");
    }
    const id = randomUUID();
    const storageKey = `users/${user.id}/documents/${id}/original`;
    const now = new Date().toISOString();
    const row = {
      id,
      filename,
      display_name: null,
      mime_type: "application/pdf",
      // The declared size until /complete verifies the stored bytes.
      file_size_bytes: size_bytes,
      status: "UPLOADED",
      processing_error: null,
      page_count: null,
      checksum_sha256: null,
      uploaded_at: now,
      created_at: now,
      updated_at: now,
    };
    const entry = { row, createdMs: Date.now(), ownerId: user.id, storageKey };
    documents.set(id, entry);
    return send(
      res,
      201,
      envelope({
        document: documentOut(entry),
        upload: {
          path: storageKey,
          token: "mock-upload-token",
          signed_url: `${ORIGIN}/object/upload/sign/${storageKey}?token=mock-upload-token`,
          expires_in_seconds: 900,
        },
      }),
    );
  }

  if (segments[0] === "documents" && segments.length === 1 && req.method === "GET") {
    const items = [...documents.values()]
      .filter((entry) => entry.ownerId === user.id)
      .map(documentOut);
    return send(
      res,
      200,
      envelope({
        items,
        pagination: { page: 1, limit: 20, total: items.length, pages: 1 },
      }),
    );
  }

  if (segments[0] === "documents" && segments.length >= 2) {
    const entry = ownedDocument(segments[1], user.id);
    if (!entry) return apiError(res, 404, "DOCUMENT_NOT_FOUND", "The document could not be found.");

    const sub = segments[2];

    if (!sub && req.method === "GET") {
      return send(res, 200, envelope(documentOut(entry)));
    }

    /* Complete the direct-to-storage upload: verify the bytes really landed. */
    if (sub === "complete" && req.method === "POST") {
      const stored = uploadedObjects.get(entry.storageKey);
      if (!stored) {
        entry.row.status = "FAILED";
        entry.row.processing_error = "The uploaded file was not received.";
        return apiError(res, 400, "INVALID_FILE", "The uploaded file was not received.");
      }
      entry.row.file_size_bytes = stored.length;
      entry.row.checksum_sha256 = "b".repeat(64);
      return send(res, 200, envelope(documentOut(entry)));
    }

    /* Start processing now (serverless hosts have no polling worker). */
    if (sub === "process" && req.method === "POST") {
      if (entry.row.status === "UPLOADED") {
        entry.row.status = "PROCESSING";
        entry.createdMs = Date.now();
      }
      return send(res, 200, envelope(documentOut(entry)));
    }

    if (sub === "status" && req.method === "GET") {
      const status = currentStatus(entry);
      return send(
        res,
        200,
        envelope({
          id: entry.row.id,
          status,
          message: status === "READY" ? "Your document is ready to review." : "Extracting text.",
          progress: status === "READY" ? 100 : 40,
        }),
      );
    }

    if (sub === "summary" && req.method === "GET") {
      return send(res, 200, envelope(SUMMARY));
    }

    if (sub === "attention" && req.method === "GET") {
      return send(res, 200, envelope({ items: ATTENTION_ITEMS }));
    }

    if (sub === "clauses" && req.method === "GET") {
      return send(res, 200, envelope({ clauses: CLAUSES }));
    }

    if (sub === "ask" && req.method === "POST") {
      const { question } = JSON.parse((await readBody(req)).toString() || "{}");
      return send(res, 200, envelope({ ...QA_ANSWER, document_id: entry.row.id, question }));
    }

    if (sub === "action-center" && req.method === "POST") {
      const items = [ACTION_OUT, ACTION_OUT_2].map((item) => ({ ...item, document_id: entry.row.id }));
      items.forEach((item) => actions.set(item.id, item));
      return send(
        res,
        200,
        envelope({
          document_id: entry.row.id,
          checklist: [items[1]],
          follow_ups: [items[0]],
          important_dates: [
            {
              value: "30 days written notice",
              normalized: null,
              label: "Termination notice period",
              source: { section: "8", clause: "8.2", page_start: 6, page_end: 6 },
            },
          ],
          evidence_state: "DOCUMENT-GROUNDED",
          abstention_reason: null,
        }),
      );
    }

    if (sub === "questions" && segments[3] === "generate" && req.method === "POST") {
      return send(
        res,
        200,
        envelope({
          evidence_state: "DOCUMENT-GROUNDED",
          questions: [
            {
              question: "Is a 30 day notice period standard for this type of role?",
              source: { section: "8", clause: "8.2", page_start: 6, page_end: 6 },
            },
          ],
          abstention_reason: null,
        }),
      );
    }

    if (sub === "reports" && req.method === "POST") {
      const report = {
        report_id: randomUUID(),
        document_id: entry.row.id,
        report_type: "review",
        status: "READY",
        created_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      };
      reports.set(report.report_id, report);
      return send(res, 201, envelope(report));
    }

    if (sub === "retry" && req.method === "POST") {
      entry.createdMs = Date.now();
      entry.row.status = "PROCESSING";
      return send(res, 200, envelope(documentOut(entry)));
    }
  }

  /* ----- Actions ----- */
  if (segments[0] === "actions") {
    if (segments.length === 1 && req.method === "GET") {
      const items = [...actions.values()];
      return send(res, 200, envelope({ items }));
    }
    if (segments.length === 2 && req.method === "PATCH") {
      const { status } = JSON.parse((await readBody(req)).toString() || "{}");
      const current = actions.get(segments[1]) ?? { ...ACTION_OUT, id: segments[1] };
      const updated = { ...current, status };
      actions.set(segments[1], updated);
      return send(res, 200, envelope(updated));
    }
  }

  /* ----- Comparisons ----- */
  if (segments[0] === "comparisons") {
    if (segments.length === 1 && req.method === "POST") {
      const body = JSON.parse((await readBody(req)).toString() || "{}");
      const comparison_id = randomUUID();
      comparisons.set(comparison_id, body);
      return send(res, 201, envelope({ comparison_id }));
    }
    if (segments.length === 3 && segments[2] === "changes" && req.method === "GET") {
      return send(
        res,
        200,
        envelope({
          comparison_id: segments[1],
          changes: CHANGES,
        }),
      );
    }
  }

  /* ----- Reports ----- */
  if (segments[0] === "reports") {
    if (segments.length === 1 && req.method === "GET") {
      return send(res, 200, envelope({ items: [...reports.values()] }));
    }
    if (segments.length === 3 && segments[2] === "download" && req.method === "GET") {
      return send(
        res,
        200,
        envelope({
          report_id: segments[1],
          download_url: `${ORIGIN}/mock-report.pdf`,
        }),
      );
    }
  }

  if (path === "/mock-report.pdf") {
    res.writeHead(200, { "Content-Type": "application/pdf", ...CORS_HEADERS });
    return res.end("%PDF-1.4 mock report");
  }

  return apiError(res, 404, "NOT_FOUND", `No mock route for ${req.method} ${path}`);
}

/* -------------------------------------------------------------------------- */
/* Server                                                                     */
/* -------------------------------------------------------------------------- */

const server = createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", ORIGIN);
  process.stderr.write(
    `[mock] ${req.method} ${url.pathname} auth=${req.headers.authorization ? "yes" : "NO"}\n`,
  );

  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    return res.end();
  }
  if (url.pathname === "/__health") {
    return send(res, 200, { ok: true });
  }

  try {
    // Stand-in for Supabase Storage's single-use signed upload target: the
    // browser PUTs the file bytes here instead of through the API. Kept outside
    // the auth mock because the signed URL is itself the credential.
    if (req.method === "PUT" && url.pathname.startsWith("/object/upload/sign/")) {
      const bytes = await readBody(req);
      uploadedObjects.set(decodeURIComponent(url.pathname.split("/object/upload/sign/")[1]), bytes);
      res.writeHead(200, { ...CORS_HEADERS, "x-upsert": "false" });
      return res.end();
    }
    if (url.pathname.startsWith("/auth/v1")) return await handleAuth(req, res, url);
    if (url.pathname.startsWith("/api/v1")) return await handleApi(req, res, url);
    return send(res, 404, { error: "not_found", path: url.pathname });
  } catch (error) {
    return send(res, 500, { error: "mock_server_error", message: String(error) });
  }
});

server.listen(PORT, () => {
  process.stdout.write(`[e2e mock] listening on ${ORIGIN}\n`);
});
