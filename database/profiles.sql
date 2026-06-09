-- Supabase Dashboard → SQL Editor → New query
-- Copy everything BELOW this line (the SQL, not this file path) and click Run.

create table if not exists public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text not null,
    full_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "Users can view own profile" on public.profiles;
create policy "Users can view own profile"
    on public.profiles
    for select
    using (auth.uid() = id);

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
    on public.profiles
    for update
    using (auth.uid() = id);

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

-- Backfill profiles for users created before the trigger existed
insert into public.profiles (id, email)
select id, email from auth.users
on conflict (id) do update set email = excluded.email;
