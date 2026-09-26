-- NyayaLens — Row-Level Security, policies and grants
-- ============================================================
-- RLS is mandatory on every exposed application table.
-- Authorization is derived ONLY from the authenticated identity
-- (auth.uid()) — never from a browser-supplied user_id.
--
-- Ownership model:
--   * users              -> id = auth.uid()
--   * user_preferences   -> user_id = auth.uid()
--   * documents          -> user_id = auth.uid()
--   * sections/clauses/chunks/analyses/attention_items
--                         -> their document belongs to auth.uid()
--   * conversations      -> user_id = auth.uid() AND (document owned or NULL)
--   * messages           -> conversation belongs to auth.uid()
--   * citations          -> message's conversation belongs to auth.uid()
--   * comparisons        -> user_id = auth.uid() AND both docs owned
--   * comparison_changes -> comparison belongs to auth.uid()
--   * actions            -> user_id = auth.uid() AND document owned (if any)
--   * reports            -> user_id = auth.uid() AND document owned
--   * audit_logs         -> NO client policies (server/service-role only)
--
-- Subqueries in policies do NOT trigger RLS on the referenced table, so
-- checking ownership through `documents` here is safe and non-recursive.

begin;

-- ============================================================
-- Ownership helper functions
-- ============================================================

-- True when the document exists and belongs to the authenticated user.
create or replace function public.is_document_owner(doc uuid)
returns boolean
language sql
stable
security invoker
as $$
  select exists (
    select 1
    from public.documents d
    where d.id = doc
      and d.user_id = auth.uid()
      and d.deleted_at is null
  );
$$;

-- True when the conversation belongs to the authenticated user.
create or replace function public.is_conversation_owner(conv uuid)
returns boolean
language sql
stable
security invoker
as $$
  select exists (
    select 1
    from public.conversations c
    where c.id = conv
      and c.user_id = auth.uid()
  );
$$;

-- True when the message's conversation belongs to the authenticated user.
create or replace function public.is_message_owner(msg uuid)
returns boolean
language sql
stable
security invoker
as $$
  select exists (
    select 1
    from public.messages m
    join public.conversations c on c.id = m.conversation_id
    where m.id = msg
      and c.user_id = auth.uid()
  );
$$;

-- True when the comparison belongs to the authenticated user.
create or replace function public.is_comparison_owner(cmp uuid)
returns boolean
language sql
stable
security invoker
as $$
  select exists (
    select 1
    from public.comparisons cp
    where cp.id = cmp
      and cp.user_id = auth.uid()
  );
$$;

-- ============================================================
-- users
-- ============================================================
alter table public.users enable row level security;

create policy users_select_own on public.users
  for select to authenticated
  using (id = auth.uid());

create policy users_insert_own on public.users
  for insert to authenticated
  with check (id = auth.uid());

create policy users_update_own on public.users
  for update to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

-- Delete is intentionally not exposed to clients;
-- account deletion requires the service role / admin flow.

-- ============================================================
-- user_preferences
-- ============================================================
alter table public.user_preferences enable row level security;

create policy preferences_select_own on public.user_preferences
  for select to authenticated
  using (user_id = auth.uid());

create policy preferences_insert_own on public.user_preferences
  for insert to authenticated
  with check (user_id = auth.uid());

create policy preferences_update_own on public.user_preferences
  for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy preferences_delete_own on public.user_preferences
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- documents
-- ============================================================
alter table public.documents enable row level security;

create policy documents_select_own on public.documents
  for select to authenticated
  using (user_id = auth.uid() and deleted_at is null);

create policy documents_insert_own on public.documents
  for insert to authenticated
  with check (user_id = auth.uid());

create policy documents_update_own on public.documents
  for update to authenticated
  using (user_id = auth.uid() and deleted_at is null)
  with check (user_id = auth.uid());

create policy documents_delete_own on public.documents
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- sections
-- ============================================================
alter table public.sections enable row level security;

create policy sections_select_own on public.sections
  for select to authenticated
  using (public.is_document_owner(document_id));

create policy sections_insert_own on public.sections
  for insert to authenticated
  with check (public.is_document_owner(document_id));

create policy sections_update_own on public.sections
  for update to authenticated
  using (public.is_document_owner(document_id))
  with check (public.is_document_owner(document_id));

create policy sections_delete_own on public.sections
  for delete to authenticated
  using (public.is_document_owner(document_id));

-- ============================================================
-- clauses
-- ============================================================
alter table public.clauses enable row level security;

create policy clauses_select_own on public.clauses
  for select to authenticated
  using (public.is_document_owner(document_id));

create policy clauses_insert_own on public.clauses
  for insert to authenticated
  with check (public.is_document_owner(document_id));

create policy clauses_update_own on public.clauses
  for update to authenticated
  using (public.is_document_owner(document_id))
  with check (public.is_document_owner(document_id));

create policy clauses_delete_own on public.clauses
  for delete to authenticated
  using (public.is_document_owner(document_id));

-- ============================================================
-- document_chunks
-- ============================================================
alter table public.document_chunks enable row level security;

create policy chunks_select_own on public.document_chunks
  for select to authenticated
  using (public.is_document_owner(document_id));

create policy chunks_insert_own on public.document_chunks
  for insert to authenticated
  with check (public.is_document_owner(document_id));

create policy chunks_update_own on public.document_chunks
  for update to authenticated
  using (public.is_document_owner(document_id))
  with check (public.is_document_owner(document_id));

create policy chunks_delete_own on public.document_chunks
  for delete to authenticated
  using (public.is_document_owner(document_id));

-- ============================================================
-- analyses
-- ============================================================
alter table public.analyses enable row level security;

create policy analyses_select_own on public.analyses
  for select to authenticated
  using (public.is_document_owner(document_id));

create policy analyses_insert_own on public.analyses
  for insert to authenticated
  with check (public.is_document_owner(document_id));

create policy analyses_update_own on public.analyses
  for update to authenticated
  using (public.is_document_owner(document_id))
  with check (public.is_document_owner(document_id));

create policy analyses_delete_own on public.analyses
  for delete to authenticated
  using (public.is_document_owner(document_id));

-- ============================================================
-- attention_items
-- ============================================================
alter table public.attention_items enable row level security;

create policy attention_select_own on public.attention_items
  for select to authenticated
  using (public.is_document_owner(document_id));

create policy attention_insert_own on public.attention_items
  for insert to authenticated
  with check (public.is_document_owner(document_id));

create policy attention_update_own on public.attention_items
  for update to authenticated
  using (public.is_document_owner(document_id))
  with check (public.is_document_owner(document_id));

create policy attention_delete_own on public.attention_items
  for delete to authenticated
  using (public.is_document_owner(document_id));

-- ============================================================
-- conversations
-- ============================================================
alter table public.conversations enable row level security;

-- A conversation belongs to its owner; when document-scoped, the
-- document must also belong to the same user (or be a global/empty scope).
create policy conversations_select_own on public.conversations
  for select to authenticated
  using (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy conversations_insert_own on public.conversations
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy conversations_update_own on public.conversations
  for update to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy conversations_delete_own on public.conversations
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- messages
-- ============================================================
alter table public.messages enable row level security;

create policy messages_select_own on public.messages
  for select to authenticated
  using (public.is_conversation_owner(conversation_id));

create policy messages_insert_own on public.messages
  for insert to authenticated
  with check (public.is_conversation_owner(conversation_id));

create policy messages_update_own on public.messages
  for update to authenticated
  using (public.is_conversation_owner(conversation_id))
  with check (public.is_conversation_owner(conversation_id));

create policy messages_delete_own on public.messages
  for delete to authenticated
  using (public.is_conversation_owner(conversation_id));

-- ============================================================
-- citations
-- ============================================================
alter table public.citations enable row level security;

create policy citations_select_own on public.citations
  for select to authenticated
  using (public.is_message_owner(message_id));

create policy citations_insert_own on public.citations
  for insert to authenticated
  with check (public.is_message_owner(message_id));

create policy citations_update_own on public.citations
  for update to authenticated
  using (public.is_message_owner(message_id))
  with check (public.is_message_owner(message_id));

create policy citations_delete_own on public.citations
  for delete to authenticated
  using (public.is_message_owner(message_id));

-- ============================================================
-- comparisons
-- ============================================================
alter table public.comparisons enable row level security;

-- Both documents must belong to the authenticated user.
create policy comparisons_select_own on public.comparisons
  for select to authenticated
  using (
    user_id = auth.uid()
    and public.is_document_owner(document_a_id)
    and public.is_document_owner(document_b_id)
  );

create policy comparisons_insert_own on public.comparisons
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_a_id)
    and public.is_document_owner(document_b_id)
  );

create policy comparisons_update_own on public.comparisons
  for update to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_a_id)
    and public.is_document_owner(document_b_id)
  );

create policy comparisons_delete_own on public.comparisons
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- comparison_changes
-- ============================================================
alter table public.comparison_changes enable row level security;

create policy changes_select_own on public.comparison_changes
  for select to authenticated
  using (public.is_comparison_owner(comparison_id));

create policy changes_insert_own on public.comparison_changes
  for insert to authenticated
  with check (public.is_comparison_owner(comparison_id));

create policy changes_update_own on public.comparison_changes
  for update to authenticated
  using (public.is_comparison_owner(comparison_id))
  with check (public.is_comparison_owner(comparison_id));

create policy changes_delete_own on public.comparison_changes
  for delete to authenticated
  using (public.is_comparison_owner(comparison_id));

-- ============================================================
-- actions
-- ============================================================
alter table public.actions enable row level security;

create policy actions_select_own on public.actions
  for select to authenticated
  using (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy actions_insert_own on public.actions
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy actions_update_own on public.actions
  for update to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and (document_id is null or public.is_document_owner(document_id))
  );

create policy actions_delete_own on public.actions
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- reports
-- ============================================================
alter table public.reports enable row level security;

create policy reports_select_own on public.reports
  for select to authenticated
  using (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy reports_insert_own on public.reports
  for insert to authenticated
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy reports_update_own on public.reports
  for update to authenticated
  using (user_id = auth.uid())
  with check (
    user_id = auth.uid()
    and public.is_document_owner(document_id)
  );

create policy reports_delete_own on public.reports
  for delete to authenticated
  using (user_id = auth.uid());

-- ============================================================
-- audit_logs (server-side only; no client policies)
-- ============================================================
-- RLS is enabled so that even if SELECT were granted, every row is
-- invisible to anon/authenticated roles. Only the service role (which
-- bypasses RLS) or a database owner can read/write audit logs.
alter table public.audit_logs enable row level security;

-- ============================================================
-- Grants
-- ============================================================
-- Table-level grants keep the frontend/browser Supabase client functional for
-- user-scoped operations. RLS policies restrict every access to the owner's
-- own rows, so privacy-sensitive columns are only ever visible on rows the
-- client already owns. `audit_logs` gets no grants at all (service role only).
-- Note: `storage_key` is NOT column-restricted; a client can read it only on
-- rows the RLS policies permit it to access. Files stay protected because the
-- storage bucket is private and downloads go through short-lived signed URLs.
grant usage on schema public to authenticated;

grant select, insert, update, delete on public.users to authenticated;
grant select, insert, update, delete on public.user_preferences to authenticated;
grant select, insert, update, delete on public.documents to authenticated;
grant select, insert, update, delete on public.sections to authenticated;
grant select, insert, update, delete on public.clauses to authenticated;
grant select, insert, update, delete on public.document_chunks to authenticated;
grant select, insert, update, delete on public.analyses to authenticated;
grant select, insert, update, delete on public.attention_items to authenticated;
grant select, insert, update, delete on public.conversations to authenticated;
grant select, insert, update, delete on public.messages to authenticated;
grant select, insert, update, delete on public.citations to authenticated;
grant select, insert, update, delete on public.comparisons to authenticated;
grant select, insert, update, delete on public.comparison_changes to authenticated;
grant select, insert, update, delete on public.actions to authenticated;
grant select, insert, update, delete on public.reports to authenticated;

-- audit_logs: no grants to authenticated/anon (service role only).
revoke all on public.audit_logs from authenticated, anon;

-- Helper functions: authenticated may call them inside policies/queries.
grant execute on function public.is_document_owner(uuid) to authenticated;
grant execute on function public.is_conversation_owner(uuid) to authenticated;
grant execute on function public.is_message_owner(uuid) to authenticated;
grant execute on function public.is_comparison_owner(uuid) to authenticated;

commit;