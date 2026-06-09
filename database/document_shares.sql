-- Supabase Dashboard → SQL Editor → New query
-- Copy everything BELOW this line (the SQL, not this file path) and click Run.

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

drop policy if exists "Owners can delete shares for own documents" on public.document_shares;
create policy "Owners can delete shares for own documents"
    on public.document_shares
    for delete
    using (
        exists (
            select 1 from public.documents d
            where d.id = document_id and d.owner_id = auth.uid()
        )
    );
