-- Integration metadata contains no passwords or provider tokens.
create table public.integration_sources (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 name text not null, provider text not null default 'spreadsheet',
 mode text not null check(mode in ('file','api')), created_at timestamptz not null default now(),
 unique(company_id,id), unique(company_id,name)
);
create table public.import_mappings (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 source_id uuid not null, kind text not null check(kind in ('products','sales','expenses')),
 name text not null, mapping jsonb not null, created_at timestamptz not null default now(),
 foreign key(company_id,source_id) references public.integration_sources(company_id,id),
 unique(company_id,source_id,kind,name)
);
create table public.import_jobs (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 source_id uuid, kind text not null check(kind in ('products','sales','expenses')),
 filename text not null, fingerprint text not null, status text not null check(status in ('imported','rejected')),
 imported integer not null default 0, rejected integer not null default 0, detail text not null default '',
 created_at timestamptz not null default now(), unique(company_id,id),
 foreign key(company_id,source_id) references public.integration_sources(company_id,id)
);
create table public.source_records (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 source_id uuid not null, job_id uuid not null, kind text not null, external_id text not null, record_id uuid not null,
 unique(company_id,source_id,kind,external_id),
 foreign key(company_id,source_id) references public.integration_sources(company_id,id),
 foreign key(company_id,job_id) references public.import_jobs(company_id,id)
);
create table public.company_backups (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references public.companies(id),
 created_at timestamptz not null default now(), record_count integer not null,
 checksum text not null, destination text not null check(destination in ('download','scheduled')),
 filename text not null
);
do $$ declare t text; begin
 foreach t in array array['integration_sources','import_mappings','import_jobs','source_records','company_backups'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('create policy owner_read on public.%I for select to lucra_app using (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('create policy owner_insert on public.%I for insert to lucra_app with check (exists(select 1 from public.companies c where c.id=company_id and c.owner_id=(select lucra_private.user_id())))',t);
  execute format('grant select,insert on public.%I to lucra_app',t);
  execute format('create index on public.%I(company_id)',t);
 end loop;
end $$;
