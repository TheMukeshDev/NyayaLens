-- NyayaLens — Supabase Storage: private bucket + RLS storage policies
-- ============================================================
-- Creates the private `legal-documents` bucket and enforces per-user access
-- on storage.objects for that bucket.
--
-- The storage.* internal schema is NOT modified: no ALTER TABLE, no new
-- tables/functions/columns on the storage schema. Only a bucket row and RLS
-- policies are created (both are the documented, supported way to configure
-- buckets and access control).
--
-- Ownership model: object keys follow
--
--     users/{user_id}/documents/{document_id}/original
--
-- so storage.foldername(name)[2] equals the owning user id. Path-derived
-- ownership works even though objects are uploaded with the service-role key
-- (owner_id is unset for service-role uploads).
--
-- No anon policies exist for this bucket: RLS denies anonymous access, and
-- the backend never issues permanent public URLs — only server-side
-- short-lived signed URLs after owner verification.

begin;

-- 1) Ensure the `legal-documents` bucket exists and is PRIVATE (20 MiB limit,
--    only the supported document MIME types).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'legal-documents',
  'legal-documents',
  false,
  20971520,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/png'
  ]
)
on conflict (id) do nothing;

-- Safety net: if the bucket already exists and is public, force it private.
-- This is a data-row update, not a schema change to the storage schema.
update storage.buckets
   set public = false
 where id = 'legal-documents'
   and public = true;

-- 2) Per-owner RLS policies on storage.objects for this bucket only.
--    storage.objects already has RLS enabled by default in Supabase; these
--    policies are additive and scoped to the legal-documents bucket.
create policy legal_documents_select_own on storage.objects
  for select to authenticated
  using (
    bucket_id = 'legal-documents'
    and (storage.foldername(name))[2] = auth.uid()::text
  );

create policy legal_documents_insert_own on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'legal-documents'
    and (storage.foldername(name))[2] = auth.uid()::text
  );

create policy legal_documents_update_own on storage.objects
  for update to authenticated
  using (
    bucket_id = 'legal-documents'
    and (storage.foldername(name))[2] = auth.uid()::text
  )
  with check (
    bucket_id = 'legal-documents'
    and (storage.foldername(name))[2] = auth.uid()::text
  );

create policy legal_documents_delete_own on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'legal-documents'
    and (storage.foldername(name))[2] = auth.uid()::text
  );

commit;