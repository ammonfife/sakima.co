---
name: lift-and-constrain
description: Standing workflow for ANY rewrite-prone domain. Walks the implementation graph (current files + git history + sibling repos + browser extensions), harvests every unique rule/nuance, builds a comprehensive test fixture from the union, then designs a canonical implementation + invariant constraints that satisfies all fixture rows. Stops the whack-a-mole regression cycle by making every prior nuance explicit and test-locked.
user-invocable: true
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.


# /lift-and-constrain

Apply this skill before designing or rewriting anything in a domain that already has multiple implementations scattered across the codebase (and probably git history). This is the meta-pattern Ben articulated on 2026-04-09 after watching Claude almost rewrite a consensus pricing engine from scratch when the existing `price_fetcher.py` + `ai_price_analyzer.py` + `item_valuator.py` already had hard-won nuance.

## Hard rules (NEVER violate)

1. **No new code until the inventory exists.** Before writing a single line of canonical implementation, you must have a written inventory of every prior implementation across all repos + git history.
2. **Harvest nuances from REMOVED code, not just current code.** Use `git log --all -p -- <file>` to find rules that were "simplified out" — those removals are usually the regressions you're fighting.
3. **Test fixture first.** The fixture is the anti-regression guard. The fixture comes BEFORE the canonical implementation, not after.
4. **One canonical location.** When done, there is exactly ONE file/module that is the source of truth. All other implementations either delegate to it or are archived (never deleted per the no-delete rule).
5. **Invariants are runtime-checked, not just unit-tested.** Hard floors / ceilings / format constraints must run at the boundary on every call, not only in the test suite.
6. **Lineage doc is mandatory.** Each non-obvious rule in the canonical impl must have a comment naming its origin (which repo, which commit, what bug/incident drove it). Future devs need to know what NOT to remove.
7. **No big-bang migrations.** Migrate callers one at a time. Each commit migrates one caller and verifies the fixture still passes.

## Inputs

The skill takes one argument: the domain name. Examples:
- `/lift-and-constrain barcode_parser`
- `/lift-and-constrain consensus_pricing`
- `/lift-and-constrain margin_calculation`
- `/lift-and-constrain cert_scraping`
- `/lift-and-constrain label_printing`

## Step 0 — Pre-flight

Confirm the domain is rewrite-prone before invoking. Signs:
- Multiple implementations of the same logic exist across files/repos
- Git log shows repeated "fix barcode parser" / "another edge case" commits
- Bugs in the domain have been fixed → re-emerged → fixed → re-emerged
- A team member has said "we have N versions of X scattered around"

If only ONE implementation exists and it works, this skill is over-engineering. Use a regular refactor instead.

## Step 1 — Walk the implementation graph

```bash
DOMAIN="$1"  # e.g. "barcode_parser"

# 1a. Current implementations across all coin-related repos
find ~/github/ammonfife ~/clawd \
  -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.go" -o -name "*.rs" \) \
  ! -path '*/node_modules/*' ! -path '*/dist/*' ! -path '*/.venv/*' ! -path '*/__pycache__/*' \
  2>/dev/null \
  | xargs grep -lE "(${DOMAIN}|barcode_parse|parse_barcode|extract_cert)" 2>/dev/null \
  > /tmp/${DOMAIN}_inventory_current.txt

# 1b. Git history per repo: log all commits that touched anything matching the domain
for repo in ~/github/ammonfife/auction_tools ~/github/ammonfife/lkup.info ~/github/ammonfife/BIGMAC; do
  cd "$repo" 2>/dev/null || continue
  echo "=== $repo ==="
  git log --all --oneline --since="1 year ago" -- "**${DOMAIN}*" 2>/dev/null | head -50
done > /tmp/${DOMAIN}_git_history.txt

# 1c. Reverted commits — search log for "revert" / "rollback" / "regress" + domain
for repo in ~/github/ammonfife/auction_tools ~/github/ammonfife/lkup.info; do
  cd "$repo" 2>/dev/null || continue
  echo "=== $repo reverts ==="
  git log --all --oneline --since="1 year ago" --grep="revert\|rollback\|regress" 2>/dev/null \
    | xargs -I{} sh -c 'git show --stat {} 2>/dev/null | head -20' | grep -i "${DOMAIN}" -A 2 -B 2
done > /tmp/${DOMAIN}_reverts.txt

# 1d. Browser extensions — separate audit (they often have client-side variants)
find ~/github/ammonfife -type d \( -name "*extension*" -o -name "*scraper*" \) 2>/dev/null \
  | xargs -I{} grep -lr "${DOMAIN}\|barcode\|parse_cert" {} 2>/dev/null \
  > /tmp/${DOMAIN}_extension_inventory.txt

# 1e. Test fixtures + edge case docs
find ~/github/ammonfife \
  -type f \( -name "*${DOMAIN}*test*" -o -name "*test*${DOMAIN}*" -o -name "*${DOMAIN}*case*" -o -name "*${DOMAIN}*edge*" \) \
  ! -path '*/node_modules/*' \
  > /tmp/${DOMAIN}_fixtures.txt

# 1f. Knowledge search — semantic + temporal (finds related facts, policies, session discussions, skills)
knowledge-search "${DOMAIN}" --multi --limit 20 --json 2>/dev/null \
  > /tmp/${DOMAIN}_knowledge_search.json
# Also search with expanded terms
knowledge-search "${DOMAIN} implementation architecture canonical" --multi --limit 10 --json 2>/dev/null \
  >> /tmp/${DOMAIN}_knowledge_search.json
```

Output of Step 1: a written `/tmp/${DOMAIN}_inventory.md` summarizing:
- Every current file, with line count and last modified
- Every prior file from git history (reverted, deleted, refactored away)
- Every test fixture / edge case doc
- Browser extension variants
- Authoritative vs UI-hint vs server-side classification
- Knowledge search results (facts, policies, session discussions mentioning this domain, temporally correlated topics)

## Step 2 — Harvest the union of nuances

For each implementation in the inventory, read it and extract:
- Every distinct input pattern it handles (regex, format, length, prefix)
- Every distinct output mapping (input X → output Y)
- Every special case / brute override (look for `if ... :` blocks at the top of parse functions)
- Every comment that mentions "edge case", "regression", "incident", "broke when"
- Every test case / fixture row

Cross-reference: build a matrix of `implementation × rule`. Rules present in some implementations but not others are candidate nuances that need preservation.

For git history: use `git log --all -p -- <file>` and look for `+` lines that were later removed by a `-`. Those are nuances that got "simplified out" and need to be re-added.

Output of Step 2: `/tmp/${DOMAIN}_nuances.csv` with columns:
- `nuance_id`, `description`, `input_example`, `expected_output`, `source_repo`, `source_file`, `source_commit_sha`, `removed_in_commit_sha (if known)`, `incident_origin_note`

## Step 3 — Build the comprehensive test fixture

From the nuances CSV, generate a runnable test fixture:
- **JSON format** for portability (works with Python pytest, vitest, deno, jest)
- **Each row** = `{input, expected, source, lineage_note}`
- **Group by category**: format variations, edge cases, error cases, regressions
- **Include negative cases**: inputs that should ERROR or return NULL

Save to `<canonical_repo>/test/fixtures/${DOMAIN}_cases.json`

## Step 4 — Design the canonical implementation

Pick the canonical home (usually the most-actively-developed repo for the domain). For coin domains, this is `lkup.info/api-python/libs/${DOMAIN}/` for server-side or `lkup.info/shared/${DOMAIN}/` for cross-surface.

Build the canonical implementation:
- ONE file or one focused module
- Satisfies EVERY row in the fixture
- Inline comments on every non-obvious rule, naming its origin (`# from auction_tools/barcode_lookup.py:147 — handles 17-digit overflow case from incident 2026-02-XX`)
- Boundary invariants (assertions on input + output shape)
- Pure function shape where possible (input → output, no hidden state)

## Step 5 — Build the test runner + invariant checker

```python
# test_${DOMAIN}_canonical.py
import json
from canonical_${DOMAIN} import parse  # or whatever the canonical entry point is

def test_all_fixture_rows():
    fixture = json.load(open('fixtures/${DOMAIN}_cases.json'))
    failures = []
    for row in fixture:
        try:
            actual = parse(row['input'])
            if actual != row['expected']:
                failures.append({
                    'input': row['input'],
                    'expected': row['expected'],
                    'actual': actual,
                    'lineage': row.get('lineage_note', '?'),
                })
        except Exception as e:
            failures.append({
                'input': row['input'],
                'error': str(e),
                'lineage': row.get('lineage_note', '?'),
            })
    if failures:
        for f in failures:
            print(f"FAIL: {f['input']} — {f.get('lineage','?')}")
            print(f"  expected: {f.get('expected')}")
            print(f"  actual:   {f.get('actual', f.get('error'))}")
        raise AssertionError(f"{len(failures)} fixture rows failed")
```

Run on every commit. If any row fails, the build fails. This is the whack-a-mole stopper.

## Step 6 — Migrate callers one at a time

For each caller of an old scattered implementation:
1. Add an import of the canonical impl
2. Replace the call site
3. Run the fixture suite
4. Commit
5. Move to next caller

Old impls stay on disk with a `# DEPRECATED 2026-04-09: use shared/canonical_${DOMAIN}` comment + a `raise DeprecationWarning("...")` if called. Never delete (no-delete rule).

## Step 7 — Lock the regression door

1. Add the test runner to CI (or local pre-commit if no CI)
2. Add a memory entry naming the canonical location: `canonical_${DOMAIN}.md` in `~/.claude/projects/-Users-benfife/memory/`
3. Add a Turso fact tagged for all 12 agents so future sessions know not to re-implement
4. Optional: add a PreToolUse hook that fails any Edit to deprecated impl files unless the edit also updates the canonical

## Output

The skill produces:
- `/tmp/${DOMAIN}_inventory.md` — implementation graph
- `/tmp/${DOMAIN}_nuances.csv` — harvested nuances
- `<canonical_repo>/test/fixtures/${DOMAIN}_cases.json` — test fixture
- `<canonical_repo>/<canonical_path>/index.{py,ts}` — canonical implementation
- `<canonical_repo>/test/test_${DOMAIN}_canonical.{py,ts}` — test runner
- `<canonical_repo>/<canonical_path>/LINEAGE.md` — lineage doc explaining each non-obvious rule
- Updated CI config or pre-commit hook
- Memory entry naming the canonical location
- Turso fact for cross-agent visibility

## When NOT to use this skill

- Single-file domain that has no prior implementations → just refactor normally
- Domain that's brand new (no git history) → just write it
- Domain where the existing implementation is genuinely correct and well-tested → leave it alone
- Time-critical incident response → fix the immediate symptom first, run /lift-and-constrain on the postmortem
