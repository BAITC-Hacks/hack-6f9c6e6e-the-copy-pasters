create table if not exists public.personal_contractors (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users (id) on delete cascade,
    name text not null check (char_length(name) between 1 and 160),
    categories text[] not null check (cardinality(categories) between 1 and 10),
    city text not null check (char_length(city) between 1 and 100),
    price_from_kzt integer not null check (price_from_kzt between 0 and 100000000),
    event_formats text[] not null check (cardinality(event_formats) between 1 and 10),
    languages text[] not null default '{}',
    max_hours numeric check (max_hours between 1 and 24),
    busy_dates date[] not null default '{}',
    description text not null default '',
    phone text,
    website text,
    social_link text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists personal_contractors_owner_created_idx
    on public.personal_contractors (owner_id, created_at desc);

create or replace function public.set_personal_contractor_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists personal_contractors_updated_at on public.personal_contractors;
create trigger personal_contractors_updated_at
    before update on public.personal_contractors
    for each row execute function public.set_personal_contractor_updated_at();

alter table public.personal_contractors enable row level security;

drop policy if exists "Users manage their own contractors" on public.personal_contractors;
create policy "Users manage their own contractors"
    on public.personal_contractors
    for all
    to authenticated
    using ((select auth.uid()) = owner_id)
    with check ((select auth.uid()) = owner_id);

grant select, insert, update, delete on public.personal_contractors to authenticated;
revoke all on public.personal_contractors from anon;
