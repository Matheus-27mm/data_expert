alter table public.import_mappings add column if not exists options jsonb not null default '{}'::jsonb;
