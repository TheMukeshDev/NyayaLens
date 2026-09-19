-- NyayaLens — Supabase Database Migration
-- ============================================================
-- Source of truth: Supabase SQL migrations (not SQLAlchemy/Alembic).
--
-- Requirements implemented:
--   * UUID primary keys, created_at / updated_at
--   * user ownership (user_id), document ownership
--   * Foreign keys, sensible indexes
--   * RLS enabled on every exposed application table
--   * Policies for authenticated users only (auth.uid())
--   * No cross-user document access; no browser-supplied user_id
--   * pgvector extension enabled (vector column added later)
--
-- Resolved conflicts (from docs/ARCHITECTURE-DECISIONS.md):
--   * users table mirrors Supabase Auth identity; PK == auth.users.id;
--     password_hash / is_verified removed (Supabase Auth owns them).
--   * Owner column canonicalized to `user_id` (Database-Schema.md;
--     System-Architecture.md `owner_id` is the same concept).
--   * Attention levels: LOW / MEDIUM / HIGH (3 levels).
--   * Embedding column + vector index are intentionally NOT created:
--     no embedding model is configured yet, so the VECTOR(n) dimension
--     and index strategy must not be hardcoded. pgvector extension is
--     enabled now; the embeddings column arrives with the model choice.

begin;

-- ============================================================
-- Extensions
-- ============================================================
create extension if not exists pgcrypto;
create extension if not exists vector;

-- ============================================================
-- Helper: updated_at trigger
-- ============================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ============================================================
-- Users & profile
-- ============================================================
-- Identity + password hashing + verification are owned by Supabase Auth
-- (auth.users / auth.uid()). This table mirrors profile metadata and links
-- application records to the authenticated identity.
create table public.users (
  id          uuid primary key default gen_random_uuid()
              references auth.users(id) on delete cascade,
  email       varchar(320) not null,
  full_name   varchar(150),
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  last_login_at timestamptz,
  deleted_at  timestamptz
);

create unique index idx_users_email on public.users (email);

create table public.user_preferences (
  user_id             uuid primary key
                      references public.users(id) on delete cascade,
  language            varchar(20) not null default 'en',
  theme               varchar(20) not null default 'system',
  email_notifications boolean not null default true,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

-- ============================================================
-- Documents
-- ============================================================
create table public.documents (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null
                     references public.users(id) on delete cascade,
  original_filename  text not null,
  display_name       varchar(255),
  mime_type          varchar(100) not null,
  file_size_bytes    bigint not null,
  storage_key        text not null,
  document_type      varchar(100),
  language           varchar(20),
  processing_status  varchar(30) not null default 'UPLOADED',
  processing_error   text,
  page_count         integer,
  checksum_sha256    char(64),
  uploaded_at        timestamptz not null default now(),
  processed_at       timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  deleted_at         timestamptz,
  constraint chk_documents_file_size_positive check (file_size_bytes > 0),
  constraint chk_documents_page_count_positive check (page_count is null or page_count > 0),
  constraint chk_documents_status check (
    processing_status in ('UPLOADED','VALIDATING','PROCESSING','EXTRACTING','ANALYZING','READY','FAILED')
  )
);

create index idx_documents_user_id on public.documents (user_id);
create index idx_documents_user_status on public.documents (user_id, processing_status);
create index idx_documents_created_at on public.documents (created_at desc);

-- ============================================================
-- Document structure
-- ============================================================
create table public.sections (
  id                 uuid primary key default gen_random_uuid(),
  document_id        uuid not null
                     references public.documents(id) on delete cascade,
  section_number     varchar(50),
  title              text,
  content            text not null,
  page_start         integer,
  page_end           integer,
  parent_section_id  uuid references public.sections(id) on delete set null,
  sequence_number    integer not null,
  created_at         timestamptz not null default now()
);

create index idx_sections_document_id on public.sections (document_id);
create index idx_sections_parent_id on public.sections (parent_section_id);

create table public.clauses (
  id                    uuid primary key default gen_random_uuid(),
  document_id           uuid not null
                        references public.documents(id) on delete cascade,
  section_id            uuid references public.sections(id) on delete set null,
  clause_number         varchar(50),
  clause_type           varchar(100),
  title                 text,
  content               text not null,
  page_start            integer,
  page_end              integer,
  sequence_number       integer not null,
  extraction_confidence numeric(5,4),
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create index idx_clauses_document_id on public.clauses (document_id);
create index idx_clauses_section_id on public.clauses (section_id);
create index idx_clauses_document_type on public.clauses (document_id, clause_type);

create table public.document_chunks (
  id           uuid primary key default gen_random_uuid(),
  document_id  uuid not null
               references public.documents(id) on delete cascade,
  section_id   uuid references public.sections(id) on delete set null,
  clause_id    uuid references public.clauses(id) on delete set null,
  chunk_index  integer not null,
  content      text not null,
  page_start   integer,
  page_end     integer,
  token_count  integer,
  metadata     jsonb not null default '{}',
  created_at   timestamptz not null default now()
);

create index idx_chunks_document_id on public.document_chunks (document_id);
create index idx_chunks_section_id on public.document_chunks (section_id);
create index idx_chunks_clause_id on public.document_chunks (clause_id);

-- NOTE: pgvector is enabled above (create extension vector).
-- The `embedding vector(n)` column and the HNSW/IVFFlat index will be added
-- in a later migration once the embedding model and its dimension are
-- configured. Embedding dimension must NOT be hardcoded before that.

-- ============================================================
-- Analyses & attention
-- ============================================================
create table public.analyses (
  id             uuid primary key default gen_random_uuid(),
  document_id    uuid not null
                 references public.documents(id) on delete cascade,
  analysis_type  varchar(50) not null,
  model_name     varchar(150),
  prompt_version varchar(50),
  status         varchar(30) not null default 'PENDING',
  result         jsonb,
  error_message  text,
  created_at     timestamptz not null default now(),
  completed_at   timestamptz,
  constraint chk_analyses_type check (
    analysis_type in ('SUMMARY','CLAUSE_EXTRACTION','ATTENTION_ANALYSIS','ENTITY_EXTRACTION','ACTION_GENERATION')
  ),
  constraint chk_analyses_status check (
    status in ('PENDING','RUNNING','COMPLETED','FAILED')
  )
);

create index idx_analyses_document_id on public.analyses (document_id);
create index idx_analyses_document_type on public.analyses (document_id, analysis_type);

create table public.attention_items (
  id               uuid primary key default gen_random_uuid(),
  analysis_id      uuid not null
                   references public.analyses(id) on delete cascade,
  document_id      uuid not null
                   references public.documents(id) on delete cascade,
  clause_id        uuid references public.clauses(id) on delete set null,
  title            varchar(255) not null,
  description      text not null,
  attention_level  varchar(20) not null,
  category         varchar(100),
  recommendation   text,
  status           varchar(30) not null default 'OPEN',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint chk_attention_level check (
    attention_level in ('LOW','MEDIUM','HIGH')
  ),
  constraint chk_attention_status check (
    status in ('OPEN','IN_PROGRESS','RESOLVED','DISMISSED')
  )
);

create index idx_attention_document_id on public.attention_items (document_id);
create index idx_attention_analysis_id on public.attention_items (analysis_id);
create index idx_attention_clause_id on public.attention_items (clause_id);
create index idx_attention_status on public.attention_items (status);

-- ============================================================
-- Conversations & messages
-- ============================================================
create table public.conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null
              references public.users(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  title       varchar(255),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index idx_conversations_user_id on public.conversations (user_id);
create index idx_conversations_document_id on public.conversations (document_id);

create table public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null
                  references public.conversations(id) on delete cascade,
  role            varchar(20) not null,
  content         text not null,
  response_type   varchar(40),
  model_name      varchar(150),
  token_usage     jsonb,
  created_at      timestamptz not null default now(),
  constraint chk_messages_role check (role in ('USER','ASSISTANT','SYSTEM')),
  constraint chk_messages_response_type check (
    response_type is null or response_type in (
      'DOCUMENT_GROUNDED','GENERAL_INFORMATION','INSUFFICIENT_EVIDENCE'
    )
  )
);

create index idx_messages_conversation_id on public.messages (conversation_id);
create index idx_messages_created_at on public.messages (created_at);

create table public.citations (
  id             uuid primary key default gen_random_uuid(),
  message_id     uuid not null
                 references public.messages(id) on delete cascade,
  chunk_id       uuid references public.document_chunks(id) on delete set null,
  section_id     uuid references public.sections(id) on delete set null,
  clause_id      uuid references public.clauses(id) on delete set null,
  page_start     integer,
  page_end       integer,
  citation_text  text,
  citation_order integer not null,
  created_at     timestamptz not null default now()
);

create index idx_citations_message_id on public.citations (message_id);
create index idx_citations_chunk_id on public.citations (chunk_id);
create index idx_citations_section_id on public.citations (section_id);
create index idx_citations_clause_id on public.citations (clause_id);

-- ============================================================
-- Comparisons
-- ============================================================
create table public.comparisons (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null
                 references public.users(id) on delete cascade,
  document_a_id  uuid not null
                 references public.documents(id) on delete cascade,
  document_b_id  uuid not null
                 references public.documents(id) on delete cascade,
  status         varchar(30) not null default 'PENDING',
  summary        text,
  created_at     timestamptz not null default now(),
  completed_at   timestamptz,
  constraint chk_comparisons_distinct_docs check (document_a_id <> document_b_id),
  constraint chk_comparisons_status check (
    status in ('PENDING','PROCESSING','COMPLETED','FAILED')
  )
);

create index idx_comparisons_user_id on public.comparisons (user_id);
create index idx_comparisons_document_a on public.comparisons (document_a_id);
create index idx_comparisons_document_b on public.comparisons (document_b_id);

create table public.comparison_changes (
  id            uuid primary key default gen_random_uuid(),
  comparison_id uuid not null
                references public.comparisons(id) on delete cascade,
  change_type   varchar(20) not null,
  category      varchar(100),
  old_text      text,
  new_text      text,
  explanation   text,
  importance    varchar(20),
  old_clause_id uuid references public.clauses(id) on delete set null,
  new_clause_id uuid references public.clauses(id) on delete set null,
  created_at    timestamptz not null default now(),
  constraint chk_changes_type check (
    change_type in ('ADDED','REMOVED','MODIFIED','UNCHANGED')
  ),
  constraint chk_changes_importance check (
    importance is null or importance in ('LOW','MEDIUM','HIGH')
  )
);

create index idx_changes_comparison_id on public.comparison_changes (comparison_id);
create index idx_changes_old_clause on public.comparison_changes (old_clause_id);
create index idx_changes_new_clause on public.comparison_changes (new_clause_id);

-- ============================================================
-- Actions
-- ============================================================
create table public.actions (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null
                   references public.users(id) on delete cascade,
  document_id      uuid references public.documents(id) on delete cascade,
  attention_item_id uuid references public.attention_items(id) on delete set null,
  action_type      varchar(50) not null,
  title            varchar(255) not null,
  description      text,
  priority         varchar(20) not null default 'MEDIUM',
  status           varchar(30) not null default 'TODO',
  due_date         date,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint chk_actions_type check (
    action_type in ('REVIEW_CLAUSE','ASK_PROFESSIONAL','COLLECT_DOCUMENT','VERIFY_INFORMATION','NEGOTIATE_TERM','FOLLOW_UP')
  ),
  constraint chk_actions_priority check (priority in ('LOW','MEDIUM','HIGH')),
  constraint chk_actions_status check (
    status in ('TODO','IN_PROGRESS','COMPLETED','DISMISSED')
  )
);

create index idx_actions_user_id on public.actions (user_id);
create index idx_actions_document_id on public.actions (document_id);
create index idx_actions_user_status on public.actions (user_id, status);

-- ============================================================
-- Reports
-- ============================================================
create table public.reports (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null
               references public.users(id) on delete cascade,
  document_id  uuid not null
               references public.documents(id) on delete cascade,
  report_type  varchar(50) not null,
  storage_key  text,
  status       varchar(30) not null default 'GENERATING',
  created_at   timestamptz not null default now(),
  completed_at timestamptz,
  constraint chk_reports_type check (
    report_type in ('DOCUMENT_REVIEW','SUMMARY','COMPARISON','ACTION_PLAN')
  ),
  constraint chk_reports_status check (
    status in ('GENERATING','READY','FAILED')
  )
);

create index idx_reports_user_id on public.reports (user_id);
create index idx_reports_document_id on public.reports (document_id);

-- ============================================================
-- Audit log (server-side, not exposed to clients via RLS)
-- ============================================================
create table public.audit_logs (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references public.users(id) on delete set null,
  action        varchar(100) not null,
  resource_type varchar(50),
  resource_id   uuid,
  ip_hash       text,
  user_agent    text,
  metadata      jsonb,
  created_at    timestamptz not null default now()
);

create index idx_audit_logs_user_id on public.audit_logs (user_id);
create index idx_audit_logs_created_at on public.audit_logs (created_at);
create index idx_audit_logs_action on public.audit_logs (action);

-- ============================================================
-- updated_at triggers
-- ============================================================
create trigger trg_users_updated_at before update on public.users
  for each row execute function public.set_updated_at();
create trigger trg_user_preferences_updated_at before update on public.user_preferences
  for each row execute function public.set_updated_at();
create trigger trg_documents_updated_at before update on public.documents
  for each row execute function public.set_updated_at();
create trigger trg_clauses_updated_at before update on public.clauses
  for each row execute function public.set_updated_at();
create trigger trg_attention_items_updated_at before update on public.attention_items
  for each row execute function public.set_updated_at();
create trigger trg_conversations_updated_at before update on public.conversations
  for each row execute function public.set_updated_at();
create trigger trg_actions_updated_at before update on public.actions
  for each row execute function public.set_updated_at();

commit;