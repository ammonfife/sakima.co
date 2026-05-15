# /test-extensions — developer README

End-to-end test runner for every lkup.info browser extension. Run via `/test-extensions`; this README is for editing the skill itself.

## Layout

```
~/.claude/skills/test-extensions/
  SKILL.md           # user-facing procedure (invoked via /test-extensions)
  README.md          # this file
  lib/
    bump-versions.sh   # +0.0.1 patch on every extension's manifest.json, appends CHANGELOG
    rotate-certs.sh    # picks N fresh known-good certs per grader from Supabase
    rotate-queries.sh  # picks N fresh queries from query-seed.json
    query-seed.json    # 35 coin-ish searches for price-overlay tests
    known-shows.json   # Whatnot live-show URLs for hot-label tests
```

Driver script (owned by lkup.info repo, not this skill):
`~/github/ammonfife/lkup.info/scripts/test-extensions.py`

## Why version bump + commit before every run

Chrome caches extension JS aggressively. Same-version reloads frequently keep stale code (even after Developer-mode "reload button" clicks). Bumping the manifest patch version + committing forces Chromium to treat the extension as new on next `--load-extension=` load, guaranteeing fresh code under test.

This is Ben's hard rule 2026-04-20. `/test-extensions --no-commit` is available but breaks the cache-bust invariant and must be loud in the log.

## Why rotation history

Running the same cert twice in a row can't catch cert-number-normalization drift — a passing run with the same cert each time proves nothing new. Rotation history files at `~/clawd/data/test-extensions-{cert,query}-rotation.json` keep the last 20 runs' inputs so each run picks unused inputs.

## Dependencies

- `jq` (optional — python3 does the JSON work, jq only for ad-hoc inspection)
- `python3` (stdlib only — json, random, os)
- `/opt/homebrew/opt/libpq/bin/psql` for Supabase verification
- `security` (macOS keychain — for `supabase_lkup_db_password` + `E2B_API_KEY`)
- `curl` (E2B pool claim)
- `sbx` (E2B CLI, fallback when pool is empty)
- `~/bin/captains-log` (summary entry)
- Turso `bigmac-ammonfife` access for todo filing

## Extending

- Add a new extension: append to `TARGETS` in `bump-versions.sh`, add its path, then add a test matrix row in the driver (`scripts/test-extensions.py`).
- Add new query types: append to `lib/query-seed.json`. Rotation auto-picks from the larger pool.
- Add a new grader for cert tests: extend `GRADERS` array in `rotate-certs.sh` and add a test routine in the driver.

## Related

- `/update-extension` — single-extension bump (this skill multi-bumps)
- `/lovable-deploy` — deploy pattern this skill mirrors (driver in repo + skill wrapper)
- `/use-e2b` — underlying sandbox primitives
- `/test-lkup` — complementary full-site E2E (not a replacement)
