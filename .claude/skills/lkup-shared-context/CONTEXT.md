# lkup.info Shared Context — Auto-loaded for all lkup skills

## How to get lkup knowledge

All lkup domain knowledge is in Turso facts with `explicitly_applies_to = 'project:lkup.info'`:

```bash
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)

# Sync groups (which files must stay in sync)
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, fact FROM facts WHERE category LIKE 'lkup-sync%' AND status='active';"

# Known divergences
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, fact FROM facts WHERE category LIKE 'lkup-divergence%' AND status='active';"

# Architecture notes
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, fact FROM facts WHERE category LIKE 'lkup-arch%' AND status='active';"

# All lkup facts
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, fact FROM facts WHERE explicitly_applies_to LIKE '%lkup%' AND status='active' ORDER BY id DESC LIMIT 30;"

# All lkup policies
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, policy FROM policies WHERE policy LIKE '%lkup%' AND superseded_by IS NULL ORDER BY id DESC LIMIT 20;"

# Open lkup todos
turso db shell "$TURSO_URL?authToken=$TOK" \
  "SELECT id, task, priority FROM todos WHERE status='pending' AND task LIKE '%lkup%' ORDER BY id DESC LIMIT 15;"
```

## Quick reference (may be stale — verify against Turso)

**Canonical repo:** `~/github/ammonfife/lkup.info`
**DB:** Supabase Pro, 3 schemas (public, raw, reference)
**EF base:** `https://vsotvatntzlrzrhemayh.supabase.co/functions/v1`

**Sync groups:** barcode-constants (5 files), barcode-parser (3 files), pricing (2 files), barcode-urls (2 files). Details in facts #843-#846.

**Critical rules:** raw.* append-only, coins.id never text slugs, no new api-python code (policy #738), all scraping via E2B (policy #749), screenshot = done.

**When editing a file, check sync group membership.** The PostToolUse hook `check-sync-siblings.sh` will warn, but verify manually too.
