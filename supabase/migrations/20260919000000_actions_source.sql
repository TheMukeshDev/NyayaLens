-- ============================================================
-- Actions: evidence source
-- ============================================================

-- The Action Center (docs/02_UX/Screen-Specification.md §45) shows which
-- document evidence each action is grounded on. We persist that reference
-- (section / clause / page range) here rather than reconstructing it, so
-- the UI card and exported report stay traceable even after regeneration.
alter table public.actions
  add column source jsonb;