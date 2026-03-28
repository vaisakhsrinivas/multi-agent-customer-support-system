-- Customers, orders, and support tickets for multi-agent customer support demos.
-- RLS enabled with no policies: use service_role for server-side access.

create table public.customers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  full_name text not null,
  phone text,
  created_at timestamptz not null default now()
);

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers (id) on delete cascade,
  status text not null check (status in ('pending', 'shipped', 'delivered', 'cancelled')),
  total_cents integer not null check (total_cents >= 0),
  currency text not null default 'USD',
  placed_at timestamptz not null default now()
);

create index orders_customer_id_idx on public.orders (customer_id);

create table public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references public.customers (id) on delete cascade,
  order_id uuid references public.orders (id) on delete set null,
  subject text not null,
  body text not null,
  status text not null check (status in ('open', 'in_progress', 'resolved')),
  priority text not null check (priority in ('low', 'normal', 'high')),
  created_at timestamptz not null default now()
);

create index support_tickets_customer_id_idx on public.support_tickets (customer_id);
create index support_tickets_order_id_idx on public.support_tickets (order_id);

alter table public.customers enable row level security;
alter table public.orders enable row level security;
alter table public.support_tickets enable row level security;
