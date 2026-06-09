-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor)

-- Example profiles table linked to Supabase Auth users
create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text not null,
    full_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can view own profile"
    on public.profiles
    for select
    using (auth.uid() = id);

create policy "Users can update own profile"
    on public.profiles
    for update
    using (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
    insert into public.profiles (id, email)
    values (new.id, new.email);
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();

-- Documents table for TipTap JSON content
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

create policy "Users can view own documents"
    on public.documents
    for select
    using (auth.uid() = owner_id);

create policy "Users can insert own documents"
    on public.documents
    for insert
    with check (auth.uid() = owner_id);

create policy "Users can update own documents"
    on public.documents
    for update
    using (auth.uid() = owner_id);

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

-- Document shares (see also backend/database/document_shares.sql)
create table if not exists public.document_shares (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references public.documents (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    created_at timestamptz not null default now(),
    unique (document_id, user_id)
);

create index if not exists document_shares_user_id_idx on public.document_shares (user_id);
create index if not exists document_shares_document_id_idx on public.document_shares (document_id);

alter table public.document_shares enable row level security;

drop policy if exists "Owners can view shares for own documents" on public.document_shares;
create policy "Owners can view shares for own documents"
    on public.document_shares
    for select
    using (
        exists (
            select 1 from public.documents d
            where d.id = document_id and d.owner_id = auth.uid()
        )
    );

drop policy if exists "Users can view shares granted to them" on public.document_shares;
create policy "Users can view shares granted to them"
    on public.document_shares
    for select
    using (auth.uid() = user_id);

drop policy if exists "Owners can create shares for own documents" on public.document_shares;
create policy "Owners can create shares for own documents"
    on public.document_shares
    for insert
    with check (
        exists (
            select 1 from public.documents d
            where d.id = document_id and d.owner_id = auth.uid()
        )
    );
