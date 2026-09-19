# NyayaLens — Supabase Setup

This guide prepares NyayaLens to use **Supabase** as the hosted backend platform. It covers one-time project setup, key handling, and environment configuration. It does not create tables or run SQL migrations.

## What Supabase Provides

- **Authentication** — Supabase Auth (GoTrue): registration, login, logout, sessions, JWT.
- **PostgreSQL database** — a managed Postgres instance with SQLAlchemy/Alembic support.
- **Row Level Security (RLS)** — per-user row isolation on top of application-level authorization.
- **Storage** — object storage with private buckets and signed URLs.
- **pgvector** — vector search extension on the same Postgres database, so embeddings live in `Supabase Database (PostgreSQL)`.

## What We Do NOT Use

- Local PostgreSQL
- Docker PostgreSQL
- Any manual local database server
- MongoDB
- Firebase Database

## Toolchain Status (verified)

| Tool | Version | Status |
| --- | --- | --- |
| Node.js | v24.19.0 | OK |
| npm | 11.17.0 | OK |
| Python | 3.14.7 | OK |
| Git | 2.55.0.windows.3 | OK |
| Supabase CLI | 2.117.0 | OK (installed to `%LOCALAPPDATA%\supabase\bin`, on user PATH) |
| Docker | not installed | **Missing** (not required — no local/Docker PostgreSQL by design) |

> Supabase CLI is installed (v2.117.0) from the official GitHub release
> (`supabase_<version>_windows_amd64.zip`), extracted to `%LOCALAPPDATA%\supabase\bin\supabase.exe`, and added to the user PATH. `supabase init` already created `supabase/config.toml`.
>
> Note: `supabase start` (local dev stack) requires Docker Desktop/Podman, which is intentionally not used here because NyayaLens targets hosted Supabase and excludes Docker/local PostgreSQL. For cloud workflows, use `supabase login`, `supabase link`, and `supabase db push` (after creating the project in the Dashboard).

---

# 1. Prerequisites

- A [Supabase](https://supabase.com) account.
- A browser (Dashboard workflow).
- Existing repo layout: `frontend/` (Next.js) and `backend/` (FastAPI).

---

# 2. Creating a Supabase Project

1. Go to https://supabase.com and sign in.
2. Open the Dashboard: https://supabase.com/dashboard/projects.
3. Click **New project**.
4. Choose:
   - **Organization** — your account/team.
   - **Project name** — e.g. `nyayalens`.
   - **Database password** — strong, random, stored in your password manager (used for `SUPABASE_DB_URL`).
   - **Region** — closest to your deployment target.
5. Click **Create new project**. Wait for provisioning (a few minutes).

Optional (CLI path, if you install the CLI later):

```bash
supabase login
supabase projects list
```

---

# 3. Obtaining the Project URL

Every Supabase project has a URL:

```
https://<project-ref>.supabase.co
```

Where `<project-ref>` is the unique 20-character project reference.

To find it:

1. Dashboard → **Project Settings** → **API**.
2. Copy the **Project URL**.
3. Use this value for:
   - `NEXT_PUBLIC_SUPABASE_URL` (frontend)
   - `SUPABASE_URL` (backend)

---

# 4. Obtaining the Publishable Key (frontend)

Supabase exposes two client-safe keys (legacy naming "anon" / "publishable"). The **publishable key** is designed to be shipped to the browser.

To find it:

1. Dashboard → **Project Settings** → **API**.
2. Under **Project API keys**, copy the **publishable** key (labeled `anon` in older docs; the new name is the same safe-to-expose key).
3. Use this value for `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

Security notes:

- This key is safe in the browser but is still scoped by RLS — it can only read rows the authenticated user is allowed to read.
- It must NOT be treated as a secret, but keep it out of git history anyway (public repos are scraped).

---

# 5. Obtaining the Service-Role Key (backend ONLY)

The **service-role key** bypasses RLS and grants full access to the project. It is a secret.

To find it:

1. Dashboard → **Project Settings** → **API**.
2. Under **Project API keys**, copy the **service_role** key.
3. Use this value for `SUPABASE_SERVICE_ROLE_KEY`.

MANDATORY RULES:

- Store the service-role key ONLY in the backend/trusted server environment.
- NEVER put it in the frontend, NEVER as a `NEXT_PUBLIC_*` variable, NEVER in `package.json`, NEVER in committed files.
- If it leaks, rotate it in Dashboard → Project Settings → API → rotate key.

> Only the frontend publishable key and the backend service-role key are used. Do not mix them up.

---

# 6. Obtaining the Database Connection String

Used by the backend (SQLAlchemy + Alembic).

1. Dashboard → **Project Settings** → **Database**.
2. Under **Connection string**, copy the **URI** (pooled recommended for server-side use).
3. Substitute the password you set in step 2. Result format:

```
postgresql+psycopg://postgres.<project-ref>:YOUR_DB_PASSWORD@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Use this value for `SUPABASE_DB_URL`.

---

# 7. Enabling pgvector

`pgvector` is available in Supabase Database; enabling it installs the extension in your database schema so `VECTOR(N)` columns can be created later.

Using the **SQL Editor**:

1. Dashboard → **SQL Editor** → **New query**.
2. Run:

```sql
create extension if not exists vector with schema extensions;
```

SQLAlchemy will target the `public` schema. To make `vector` usable there, also ensure the extension is available to `public` search path (the steps above suffice for a fresh project; migration review happens later when tables are designed).

> This guide does not create tables. Table and index creation (including `VECTOR(1536)` columns and HNSW/IVFFlat indexes) is deferred to the schema implementation phase.

Reference dimension: `EMBEDDING_DIMENSION=1536` must match the deployed embedding model.

---

# 8. Creating a Storage Bucket

Documents, processed files, and generated reports go into **private** buckets.

1. Dashboard → **Storage** → **New bucket**.
2. Name: `documents` (or your chosen name).
3. **Public bucket**: OFF (must be private — legal documents).
4. Save.

Access model:

- Browsers never read bucket files directly with the publishable key unless RLS policies allow it.
- Signed URLs are issued server-side for direct browser access when necessary.

---

# 9. Configuring Row Level Security (RLS)

RLS restricts row access at the database level. Enforce it on every user-owned table.

General pattern (applied when tables exist):

1. Dashboard → **SQL Editor** → **New query**.
2. For each user-owned table (e.g. `documents`):

```sql
alter table public.documents enable row level security;

create policy "users can manage their own documents"
on public.documents
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
```

Storage buckets get similar policies (usually done via the Storage UI → Policies, or SQL on `storage.objects`).

> No tables exist yet, so no RLS policies are applied in this step. This policy template is applied during the schema implementation phase, alongside application-level `owner_id` checks.

---

# 10. Local Environment Variables

Never create a real `.env` with secrets that gets committed. Use placeholders locally via `.env.example` (already present) or export in your shell.

### Frontend (`frontend/.env.local`, git-ignored)

```env
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<publishable-key>
```

### Backend (`backend/.env`, git-ignored)

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_DB_URL=postgresql+psycopg://postgres.<project-ref>:<db-password>@aws-0-<region>.pooler.supabase.com:5432/postgres
EMBEDDING_DIMENSION=1536
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### AI provider keys (backend only)

```env
LLM_API_KEY=<llm-provider-key>
EMBEDDING_API_KEY=<embedding-provider-key>
```

Rules:

- The repo contains only `.env.example`.
- `.gitignore` already excludes `.env` and `.env.*` while allowing `.env.example` and `.env.local`.
- Never commit any file containing real keys.

---

# 11. Deployment Environment Variables

Set these in your hosting provider's secret manager (never in the repo).

### Frontend host (e.g., Vercel)

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | publishable key |

> `NEXT_PUBLIC_*` values are inlined at build time. There is no way to safely embed the service-role key here — do not try.

### Backend host (e.g., Fly.io / Render / Railway / ECS)

| Variable | Value |
| --- | --- |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | service-role key (server-only secret) |
| `SUPABASE_DB_URL` | database connection URI (server-only secret) |
| `LLM_API_KEY` | LLM provider key |
| `EMBEDDING_API_KEY` | embedding provider key |
| `CORS_ORIGINS` | allowed browser origins |

---

# 12. Security Checklist

- [ ] Project URL stored as `SUPABASE_URL` (backend) and `NEXT_PUBLIC_SUPABASE_URL` (frontend)
- [ ] Publishable key only in frontend
- [ ] Service-role key only in backend/server environment
- [ ] No secrets in committed files; only `.env.example` committed
- [ ] Storage bucket is private
- [ ] pgvector extension enabled
- [ ] RLS to be enabled on all user-owned tables (during schema phase)
- [ ] Supabase CLI not required (Dashboard workflow documented)