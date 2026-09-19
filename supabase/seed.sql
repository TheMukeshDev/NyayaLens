-- NyayaLens — Seed (demo / local development data)
-- ============================================================
-- RUNS AS THE POSTGRES ROLE during `supabase db reset` or when executed
-- directly by an administrator. It creates demo identities + a single
-- document lifecycle (sections, clauses, chunks, analysis, attention,
-- conversation + messages + citations, comparison, actions, report).
--
-- NOTE on embedding: no embeddings rows are seeded because the embedding
-- model/dimension is not configured yet (see initial migration note).
--
-- NOTE on auth.users: rows here only provide stable UUID identities so RLS
-- policies keyed on auth.uid() can be verified against these users. Do NOT
-- treat these as production accounts.

begin;

-- ------------------------------------------------------------
-- Demo identities (must exist in auth.users to satisfy the FK)
-- ------------------------------------------------------------
insert into auth.users
  (id, instance_id, aud, role, email, encrypted_password,
   email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
   created_at, updated_at, confirmation_token, recovery_token,
   email_change_token_new, email_change)
values
  -- demo user A — the primary demo account
  ('00000000-0000-0000-0000-00000000000a',
   '00000000-0000-0000-0000-000000000000',
   'authenticated', 'authenticated',
   'demo.a@nyayalens.test',
   '$2a$10$0dHmy3hI5kRqX8zQ0Y9d7e9F1mJgDIsKMa5v6cWXO2yU5n8wYtGHy', -- bcrypt("password")
   now(),
   '{"provider":"email","providers":["email"]}',
   '{"display_name":"Demo User A"}',
   now(), now(), '', '', '', '')
on conflict (id) do nothing;

insert into auth.users
  (id, instance_id, aud, role, email, encrypted_password,
   email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
   created_at, updated_at, confirmation_token, recovery_token,
   email_change_token_new, email_change)
values
  -- demo user B — used to prove cross-user isolation
  ('00000000-0000-0000-0000-00000000000b',
   '00000000-0000-0000-0000-000000000000',
   'authenticated', 'authenticated',
   'demo.b@nyayalens.test',
   '$2a$10$0dHmy3hI5kRqX8zQ0Y9d7e9F1mJgDIsKMa5v6cWXO2yU5n8wYtGHy',
   now(),
   '{"provider":"email","providers":["email"]}',
   '{"display_name":"Demo User B"}',
   now(), now(), '', '', '', '')
on conflict (id) do nothing;

-- ------------------------------------------------------------
-- Public profile mirrors
-- ------------------------------------------------------------
insert into public.users (id, email, full_name, is_active, created_at, updated_at)
values
  ('00000000-0000-0000-0000-00000000000a', 'demo.a@nyayalens.test', 'Demo User A', true, now(), now()),
  ('00000000-0000-0000-0000-00000000000b', 'demo.b@nyayalens.test', 'Demo User B', true, now(), now())
on conflict (id) do nothing;

insert into public.user_preferences (user_id, language, theme, email_notifications)
values
  ('00000000-0000-0000-0000-00000000000a', 'en', 'system', true),
  ('00000000-0000-0000-0000-00000000000b', 'en', 'system', true)
on conflict (user_id) do nothing;

-- ------------------------------------------------------------
-- Demo document (user A)
-- ------------------------------------------------------------
insert into public.documents
  (id, user_id, original_filename, display_name, mime_type, file_size_bytes,
   storage_key, document_type, language, processing_status, page_count,
   checksum_sha256, uploaded_at, created_at, updated_at)
values
  ('10000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000a',
   'employment-agreement.pdf', 'Employment Agreement', 'application/pdf', 245760,
   'users/00000000-0000-0000-0000-00000000000a/documents/10000000-0000-0000-0000-00000000000a/employment-agreement.pdf',
   'EMPLOYMENT_AGREEMENT', 'en', 'READY', 8,
   'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
   now(), now(), now())
on conflict (id) do nothing;

-- ------------------------------------------------------------
-- Sections
-- ------------------------------------------------------------
insert into public.sections
  (id, document_id, section_number, title, content, page_start, page_end,
   parent_section_id, sequence_number)
values
  ('11000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-00000000000a',
   '1', 'Employment', 'This section defines the employment relationship.', 1, 1, null, 1),
  ('11000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-00000000000a',
   '2', 'Compensation', 'This section defines compensation and benefits.', 2, 3, null, 2),
  ('11000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-00000000000a',
   '3', 'Termination', 'This section defines termination conditions.', 5, 6, null, 3);

-- ------------------------------------------------------------
-- Clauses
-- ------------------------------------------------------------
insert into public.clauses
  (id, document_id, section_id, clause_number, clause_type, title, content,
   page_start, page_end, sequence_number, extraction_confidence)
values
  ('12000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000001', '1.1', 'EMPLOYMENT', 'Position',
   'The employee will serve in the role of Senior Engineer.', 1, 1, 1, 0.9900),
  ('12000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000002', '2.1', 'COMPENSATION', 'Base Salary',
   'The employee will receive an annual base salary of 120,000.', 2, 2, 2, 0.9850),
  ('12000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000003', '3.1', 'TERMINATION', 'Notice Period',
   'Either party may terminate with a 90-day notice period.', 5, 5, 3, 0.9750);

-- ------------------------------------------------------------
-- Chunks (no embedding column yet — model not configured)
-- ------------------------------------------------------------
insert into public.document_chunks
  (id, document_id, section_id, clause_id, chunk_index, content,
   page_start, page_end, token_count, metadata)
values
  ('13000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000001', '12000000-0000-0000-0000-000000000001',
   0, 'The employee will serve in the role of Senior Engineer.', 1, 1, 12,
   '{"heading":"Employment","page":1,"section":"1","language":"en"}'),
  ('13000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000002', '12000000-0000-0000-0000-000000000002',
   1, 'The employee will receive an annual base salary of 120,000.', 2, 2, 10,
   '{"heading":"Compensation","page":2,"section":"2","language":"en"}'),
  ('13000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-00000000000a',
   '11000000-0000-0000-0000-000000000003', '12000000-0000-0000-0000-000000000003',
   2, 'Either party may terminate with a 90-day notice period.', 5, 5, 9,
   '{"heading":"Termination","page":5,"section":"3","language":"en"}');

-- ------------------------------------------------------------
-- Analysis + attention items
-- ------------------------------------------------------------
insert into public.analyses
  (id, document_id, analysis_type, model_name, prompt_version, status, result,
   created_at, completed_at)
values
  ('14000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-00000000000a',
   'ATTENTION_ANALYSIS', 'demo-model', 'attention-v3', 'COMPLETED',
   '{"findings_count":1}', now(), now());

insert into public.attention_items
  (id, analysis_id, document_id, clause_id, title, description,
   attention_level, category, recommendation, status)
values
  ('15000000-0000-0000-0000-000000000001', '14000000-0000-0000-0000-000000000001',
   '10000000-0000-0000-0000-00000000000a', '12000000-0000-0000-0000-000000000003',
   'Termination notice period', 'A 90-day notice period is required.',
   'HIGH', 'TERMINATION',
   'Confirm how the notice period interacts with the probation period.', 'OPEN');

-- ------------------------------------------------------------
-- Conversation + messages + citations
-- ------------------------------------------------------------
insert into public.conversations (id, user_id, document_id, title, created_at, updated_at)
values
  ('16000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a',
   '10000000-0000-0000-0000-00000000000a', 'Termination question', now(), now());

insert into public.messages (id, conversation_id, role, content, response_type, model_name)
values
  ('17000000-0000-0000-0000-000000000001', '16000000-0000-0000-0000-000000000001',
   'USER', 'What happens if I resign?', null, null),
  ('17000000-0000-0000-0000-000000000002', '16000000-0000-0000-0000-000000000001',
   'ASSISTANT', 'The agreement requires a 90-day notice period for termination.',
   'DOCUMENT_GROUNDED', 'demo-model');

insert into public.citations
  (id, message_id, chunk_id, section_id, clause_id, page_start, page_end,
   citation_text, citation_order)
values
  ('18000000-0000-0000-0000-000000000001', '17000000-0000-0000-0000-000000000002',
   '13000000-0000-0000-0000-000000000003', '11000000-0000-0000-0000-000000000003',
   '12000000-0000-0000-0000-000000000003', 5, 5,
   'Either party may terminate with a 90-day notice period.', 1);

-- ------------------------------------------------------------
-- Comparison (user A, two documents; second doc created here)
-- ------------------------------------------------------------
insert into public.documents
  (id, user_id, original_filename, display_name, mime_type, file_size_bytes,
   storage_key, document_type, language, processing_status, page_count,
   checksum_sha256, uploaded_at, created_at, updated_at)
values
  ('10000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-00000000000a',
   'employment-agreement-v2.pdf', 'Employment Agreement v2', 'application/pdf', 251000,
   'users/00000000-0000-0000-0000-00000000000a/documents/10000000-0000-0000-0000-00000000000b/employment-agreement-v2.pdf',
   'EMPLOYMENT_AGREEMENT', 'en', 'READY', 8,
   'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
   now(), now(), now())
on conflict (id) do nothing;

insert into public.comparisons
  (id, user_id, document_a_id, document_b_id, status, summary, created_at, completed_at)
values
  ('19000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a',
   '10000000-0000-0000-0000-00000000000a', '10000000-0000-0000-0000-00000000000b',
   'COMPLETED', 'Notice period changed from 30 to 90 days.', now(), now());

insert into public.comparison_changes
  (id, comparison_id, change_type, category, old_text, new_text, explanation,
   importance, old_clause_id, new_clause_id)
values
  ('1a000000-0000-0000-0000-000000000001', '19000000-0000-0000-0000-000000000001',
   'MODIFIED', 'TERMINATION', 'Either party may terminate with a 30-day notice period.',
   'Either party may terminate with a 90-day notice period.',
   'Notice period increased from 30 to 90 days.', 'HIGH',
   '12000000-0000-0000-0000-000000000003', '12000000-0000-0000-0000-000000000003');

-- ------------------------------------------------------------
-- Actions
-- ------------------------------------------------------------
insert into public.actions
  (id, user_id, document_id, attention_item_id, action_type, title, description,
   priority, status, due_date)
values
  ('1b000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a',
   '10000000-0000-0000-0000-00000000000a', '15000000-0000-0000-0000-000000000001',
   'REVIEW_CLAUSE', 'Review termination clause',
   'Confirm how the 90-day notice period interacts with probation.',
   'HIGH', 'TODO', '2026-10-01');

-- ------------------------------------------------------------
-- Report
-- ------------------------------------------------------------
insert into public.reports
  (id, user_id, document_id, report_type, storage_key, status, created_at, completed_at)
values
  ('1c000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a',
   '10000000-0000-0000-0000-00000000000a', 'DOCUMENT_REVIEW',
   'users/00000000-0000-0000-0000-00000000000a/reports/1c000000-0000-0000-0000-000000000001.pdf',
   'READY', now(), now());

-- ------------------------------------------------------------
-- Demo audit event
-- ------------------------------------------------------------
insert into public.audit_logs
  (id, user_id, action, resource_type, resource_id, metadata, created_at)
values
  ('1d000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-00000000000a',
   'DOCUMENT_UPLOAD', 'document', '10000000-0000-0000-0000-00000000000a',
   '{"demo":true}', now());

commit;