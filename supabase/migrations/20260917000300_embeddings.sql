-- NyayaLens — Embeddings (pgvector) + retrieval functions
-- ============================================================
-- Adds the vector search layer for document_chunks:
--   chunk -> embedding -> vector storage -> similarity search
-- (docs/04_AI/RAG-Architecture.md §6-§7, docs/04_AI/AI-Architecture.md §16).
--
-- Design decisions:
--   * The `embedding` column is created WITHOUT a fixed dimension
--     (`vector` not `vector(n)`) so the dimension is never hardcoded before
--     the embedding model is configured. `public.ensure_embedding_index(dim)`
--     is the single place that pins the dimension and builds the HNSW index
--     once the model's dimension is known.
--   * `user_id` is denormalized onto document_chunks so every retrieval can be
--     filtered by ownership directly (`WHERE user_id = auth.uid() AND
--     document_id = :document_id`), enforced in SQL, not after retrieval.
--   * Retrieval runs through `public.match_documents(...)` (security invoker)
--     so RLS still applies; the server additionally passes an explicit
--     user_id so the service-role path filters the same way.

begin;

-- ============================================================
-- Ownership + embedding columns on document_chunks
-- ============================================================
alter table public.document_chunks
  add column if not exists user_id uuid
    references public.users(id) on delete cascade;

update public.document_chunks dc
set user_id = d.user_id
from public.documents d
where d.id = dc.document_id
  and dc.user_id is null;

alter table public.document_chunks
  alter column user_id set not null;

-- Dimensionless vector so no dimension is pinned before model configuration.
alter table public.document_chunks
  add column if not exists embedding vector;
alter table public.document_chunks
  add column if not exists embedding_model varchar(150);
alter table public.document_chunks
  add column if not exists embedding_dimension integer;

-- The vector index is intentionally NOT created here: the dimension is not
-- known until the embedding model is configured. Run
--   select public.ensure_embedding_index(:dimension);
-- once the model/dimension is confirmed (see function below).

create index idx_chunks_user_document on public.document_chunks (user_id, document_id);

-- ============================================================
-- Similarity search (retrieval entry point)
-- ============================================================
-- Returns the top matching chunks for an authenticated user, optionally
-- restricted to a single document. Cosine similarity is returned as `similarity`
-- (1 - cosine_distance). SECURITY INVOKER: RLS still applies on top of the
-- explicit `user_id` filter, so a client call could never see another user's
-- chunks even if the function were reached.
create or replace function public.match_documents(
  query_embedding vector,
  match_count int default 10,
  p_user_id uuid default auth.uid(),
  p_document_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  user_id uuid,
  section_id uuid,
  clause_id uuid,
  chunk_index int,
  content text,
  page_start int,
  page_end int,
  token_count int,
  metadata jsonb,
  similarity float,
  embedding_model varchar,
  embedding_dimension int
)
language sql
stable
security invoker
set search_path = public
as $$
  select
    dc.id,
    dc.document_id,
    dc.user_id,
    dc.section_id,
    dc.clause_id,
    dc.chunk_index,
    dc.content,
    dc.page_start,
    dc.page_end,
    dc.token_count,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity,
    dc.embedding_model,
    dc.embedding_dimension
  from public.document_chunks dc
  where dc.user_id = p_user_id
    and dc.embedding is not null
    and (p_document_id is null or dc.document_id = p_document_id)
  order by dc.embedding <=> query_embedding asc
  limit match_count;
$$;

-- ============================================================
-- Vector index reconciliation (dimension confirmed at runtime)
-- ============================================================
-- Pins the embedding column to the configured model's dimension and creates an
-- HNSW index for cosine similarity. Idempotent. Only callable by the service
-- role / database owner (no client grant below). This is where the dimension
-- becomes fixed — never in a migration, and never before model configuration.
create or replace function public.ensure_embedding_index(dim integer)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if dim is null or dim <= 0 then
    raise exception 'embedding dimension must be a positive integer';
  end if;
  if to_regclass('public.document_chunks') is null then
    raise exception 'public.document_chunks does not exist';
  end if;
  execute format(
    'alter table public.document_chunks alter column embedding type vector(%s)',
    dim
  );
  execute
    'create index if not exists idx_chunks_embedding_hnsw on public.document_chunks '
    'using hnsw (embedding vector_cosine_ops)';
end;
$$;

-- ============================================================
-- RLS: document_chunks now require direct user ownership too
-- ============================================================
drop policy if exists chunks_select_own on public.document_chunks;
drop policy if exists chunks_insert_own on public.document_chunks;
drop policy if exists chunks_update_own on public.document_chunks;
drop policy if exists chunks_delete_own on public.document_chunks;

create policy chunks_select_own on public.document_chunks
  for select to authenticated
  using (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy chunks_insert_own on public.document_chunks
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy chunks_update_own on public.document_chunks
  for update to authenticated
  using (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  )
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy chunks_delete_own on public.document_chunks
  for delete to authenticated
  using (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

-- ============================================================
-- Grants
-- ============================================================
-- match_documents is the retrieval surface for authenticated clients.
grant execute on function public.match_documents(vector, int, uuid, uuid) to authenticated;

-- ensure_embedding_index is DDL + security definer: service role / DB owner only.
revoke all on function public.ensure_embedding_index(integer) from public;
revoke all on function public.ensure_embedding_index(integer) from authenticated;

commit;