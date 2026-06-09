-- Supabase Dashboard → SQL Editor → New query
-- Copy everything BELOW this line (the SQL, not this file path) and click Run.

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    title text not null default 'Untitled',
    content_json jsonb not null default '{"type":"doc","content":[{"type":"paragraph"}]}'::jsonb,
    owner_id uuid not null references auth.users (id) on delete cascade,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists documents_owner_id_idx on public.documents (owner_id);
create index if not exists documents_updated_at_idx on public.documents (updated_at desc);

alter table public.documents enable row level security;

drop policy if exists "Users can view own documents" on public.documents;
create policy "Users can view own documents"
    on public.documents
    for select
    using (auth.uid() = owner_id);

drop policy if exists "Users can insert own documents" on public.documents;
create policy "Users can insert own documents"
    on public.documents
    for insert
    with check (auth.uid() = owner_id);

drop policy if exists "Users can update own documents" on public.documents;
create policy "Users can update own documents"
    on public.documents
    for update
    using (auth.uid() = owner_id);

drop policy if exists "Users can delete own documents" on public.documents;
create policy "Users can delete own documents"
    on public.documents
    for delete
    using (auth.uid() = owner_id);

create or replace function public.set_documents_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists documents_updated_at on public.documents;

create trigger documents_updated_at
    before update on public.documents
    for each row execute procedure public.set_documents_updated_at();
