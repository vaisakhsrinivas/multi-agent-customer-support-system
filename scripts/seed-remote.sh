#!/usr/bin/env bash
# Load supabase/seed.sql into the linked Supabase Postgres (cloud).
# Requires: psql (e.g. brew install libpq && brew link --force libpq)
# Set SUPABASE_DB_URL to the URI from Project Settings → Database → Connection string.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "Set SUPABASE_DB_URL to your Postgres connection URI (with password), then re-run." >&2
  exit 1
fi
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$ROOT/supabase/seed.sql"
echo "Seed finished."
