# Supabase

Multi-agent customer support demo. This folder holds **Supabase** schema and seed data for `customers`, `orders`, and `support_tickets`.

## Deploy schema and seed to your existing Supabase project (cloud)

Use this when you already have a project in the [Supabase Dashboard](https://supabase.com/dashboard) and want this repo’s tables and demo rows there—not on local Docker.

### 1. Tokens and IDs (do not confuse these)

| Value | Where to get it | Used for |
|--------|-----------------|----------|
| **Personal Access Token** | [Account → Access Tokens](https://supabase.com/dashboard/account/tokens) (often `sbp_...`) | Supabase CLI (`link`, `db push`) |
| **Project ref** | Dashboard URL: `.../project/<project_ref>` | `supabase link --project-ref` |
| **Database password** | Set when the project was created; reset under **Settings → Database** if needed | CLI connects to Postgres for migrations |
| **Service role key** | **Settings → API** | App/agents only; not for linking the CLI |

The **anon** and **service_role** keys are JWTs for the REST API. They are **not** a substitute for a Personal Access Token when using the CLI.

### 2. Install the CLI

See [Supabase CLI](https://supabase.com/docs/guides/cli).

### 3. Link and push migrations

From the repository root:

```bash
export SUPABASE_ACCESS_TOKEN='your-personal-access-token'
export SUPABASE_DB_PASSWORD='your-database-password'

supabase link --project-ref YOUR_PROJECT_REF
supabase db push --linked
```

That applies everything under [`migrations/`](migrations/) to the hosted database.

### 4. Load seed data on the cloud database

`supabase db push --include-seed` is **not** dependable on remote projects (see [CLI issue #4670](https://github.com/supabase/cli/issues/4670)). Use one of these instead:

**Option A — SQL Editor (simplest)**  
Open **SQL Editor** in the dashboard, paste the contents of [`seed.sql`](seed.sql), and run it once.

**Option B — `psql`**

1. Copy the **URI** connection string from **Settings → Database** (insert your DB password).
2. From the repository root, run:

   ```bash
   export SUPABASE_DB_URL='postgresql://postgres.[ref]:[PASSWORD]@aws-0-....pooler.supabase.com:6543/postgres'
   chmod +x scripts/seed-remote.sh
   ./scripts/seed-remote.sh
   ```

   Or: `psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/seed.sql`

The seed uses fixed primary keys. If you run it again after data exists, inserts will conflict—truncate the three tables first only on a throwaway/demo database.

### 5. Environment template

See [`.env.example`](../.env.example) in the repository root for variable names. Copy to `.env` (gitignored); never commit secrets.

### Verify on the cloud project

In the SQL Editor:

```sql
select count(*) from customers;
select count(*) from orders;
select count(*) from support_tickets;
```

Each count should be at least **10** (this repo’s seed has **12** per table).

**Eval and tests:** Order UUIDs such as `bbbbbbbb-0001-4000-8000-000000000001` and seed emails (e.g. `ava.chen@example.com`) match prompts in [`eval/scenarios.yaml`](../eval/scenarios.yaml) and in [`tests/test_support_scenarios.py`](../tests/test_support_scenarios.py). Keep those in sync if you change seed data.

---

## Schema overview

- **`customers`**: `id`, `email`, `full_name`, `phone`, `created_at`
- **`orders`**: `id`, `customer_id`, `status`, `total_cents`, `currency`, `placed_at`
- **`support_tickets`**: `id`, `customer_id`, optional `order_id`, `subject`, `body`, `status`, `priority`, `created_at`

Row Level Security is **enabled** on all three tables with **no policies**, so the anon key cannot read/write these tables. Use the **`service_role`** key only on trusted servers (e.g. agents or MCP tools), never in client-side code.

## Local Postgres (optional)

Only if you want Docker-based local Supabase (from the repository root):

```bash
supabase start
supabase db reset
```

`db reset` applies migrations and runs [`seed.sql`](seed.sql) per [`config.toml`](config.toml). This is **not** required for the cloud-only workflow above.
