-- Crop Yield Explorer: database schema and Row Level Security policies.
-- Run once in the Supabase dashboard: SQL Editor > New query > paste > Run.

create table if not exists public.datasets (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name        text not null check (char_length(name) between 1 and 60),
  rows        integer not null check (rows >= 0),
  cols        integer not null check (cols >= 0),
  size_bytes  integer not null check (size_bytes between 0 and 5242880),
  content     text not null,
  created_at  timestamptz not null default now()
);
create index if not exists datasets_user_idx on public.datasets (user_id, created_at desc);

create table if not exists public.user_settings (
  user_id     uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  prefs       jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

alter table public.datasets      enable row level security;
alter table public.user_settings enable row level security;
alter table public.datasets      force row level security;
alter table public.user_settings force row level security;

-- A signed-in user can see and change ONLY rows that belong to them. Anonymous visitors get nothing.
drop policy if exists "datasets_select_own" on public.datasets;
drop policy if exists "datasets_insert_own" on public.datasets;
drop policy if exists "datasets_update_own" on public.datasets;
drop policy if exists "datasets_delete_own" on public.datasets;
create policy "datasets_select_own" on public.datasets for select to authenticated using (auth.uid() = user_id);
create policy "datasets_insert_own" on public.datasets for insert to authenticated with check (auth.uid() = user_id);
create policy "datasets_update_own" on public.datasets for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "datasets_delete_own" on public.datasets for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "settings_select_own" on public.user_settings;
drop policy if exists "settings_insert_own" on public.user_settings;
drop policy if exists "settings_update_own" on public.user_settings;
drop policy if exists "settings_delete_own" on public.user_settings;
create policy "settings_select_own" on public.user_settings for select to authenticated using (auth.uid() = user_id);
create policy "settings_insert_own" on public.user_settings for insert to authenticated with check (auth.uid() = user_id);
create policy "settings_update_own" on public.user_settings for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "settings_delete_own" on public.user_settings for delete to authenticated using (auth.uid() = user_id);

revoke all on public.datasets, public.user_settings from anon;
grant select, insert, update, delete on public.datasets, public.user_settings to authenticated;
