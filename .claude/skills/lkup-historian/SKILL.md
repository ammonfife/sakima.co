---
name: lkup-historian
description: >
  Spawn a BACKGROUND agent that audits recent lkup.info session activity against the canonical
  ground-truth (the distilled history, memory, lkup_knowledge, policy #858, and the regression
  landmine classes). It reads all saved durable artifacts + any history newer than them, then
  reads the CURRENT session.jsonl plus any OTHER session.jsonl modified within a time window, and
  ALSO audits the canonical docs themselves (lkup_knowledge.md + README/CLAUDE/AGENTS/NEXT_SESSION +
  the hand-maintained-and-stale CONTEXT_SUMMARY.md) for staleness / contradiction / regression. It
  FLAGS anything that happened in a session that is wrong or should have been done differently —
  regressions, landmine attempts, canonical-model violations, agent-asserted false confidence, or
  drift from Ben's verbatim intent. **Primary output is TURSO** (findings fact + todos + violations,
  durable/cross-agent) — the file + returned summary are secondary (the return evaporates). It flags
  + files, it does NOT auto-mutate production. Invoke: `/lkup-historian [windowHours]`
  (default 6). Use after a multi-session burst, before trusting "done" claims, or on a loop.
---

# /lkup-historian — background session-audit watchdog

When invoked, **launch a background agent** (Agent tool, `run_in_background: true`, `general-purpose`)
with the task below. Pass the window: `windowHours` = the skill arg, default **6**. Do not do the
work inline — spawn it so the foreground stays free. Then tell Ben it's running and end.

The `$ARGUMENTS` (if numeric) is `windowHours`. Compute `cutoff = now - windowHours`.

---

## Background-agent task (embed this verbatim as the Agent prompt, substituting windowHours)

> You are the **lkup.info Historian** — a read-only watchdog. Your job: read the canonical
> ground-truth, then audit recent session activity, and FLAG anything wrong or that should have
> been done differently. You do NOT edit production, DB, or docs — you flag + file only.
>
> ### Step 1 — Load ground truth (the standard you audit against)
> 1. `~/clawd/data/lkup-history-distill/MANIFEST.md` — the index of all durable artifacts.
> 2. Memory (the supreme rules): `~/.claude/projects/-Users-benfife-github-ammonfife-lkup-info/memory/`
>    → `ben-intent-preempts-agent-statements.md` (Ben's history.jsonl PREEMPTS any agent statement),
>    `regression-sweep-and-next-session.md` (the **landmine classes**), `canonical-data-model.md`,
>    `history-distill-artifacts.md`.
> 3. The distilled history chunks `~/clawd/data/lkup-history-distill/chunk-01..08.md` — Ben's verbatim
>    directives + decisions (read at least chunk-07 + chunk-08 = most recent; others on demand).
> 4. Canonical model = **Turso policy #858** + the regression landmine classes. Pull live:
>    `turso`/curl the `lkup_knowledge` view for policies #858/#857/#841/#827/#863/#861 and the
>    newest ~40 facts. (Use the Turso HTTP pipeline with `$TURSO_DATABASE_URL`/`$TURSO_AUTH_TOKEN`
>    via Python urllib or curl — same pattern as scripts/.)
> 5. Also load the canonical DOCS (you AUDIT these too, Step 4b): `lkup_knowledge.md` (the live
>    brain, symlink → docs/knowledge-snapshots/), `README.md`, `CLAUDE.md`, `AGENTS.md`,
>    `NEXT_SESSION.md`. ⚠️ `docs/CONTEXT_SUMMARY.md` is **HAND-MAINTAINED and goes STALE — it does
>    NOT auto-update** (yet it's the one doc @imported into every session). Treat lkup_knowledge.md
>    + policy #858 as truth; flag wherever CONTEXT_SUMMARY (or any doc) drifts from them.
>
> ### Step 2 — Read history NEWER than the distill
> The distill covers through ~2026-06-02. Capture anything since:
> `python3 ~/clawd/scripts/reduce-history.py --session-match "lkup,sakima.co,desktop_scanner.py" --session-min-hits 1 --since <distill-max-date> -o /tmp/... ` → NO, do not write /tmp; write to
> `~/clawd/data/lkup-historian/history-since.txt`. Read it. (distill-max-date = chunk-08's Dates
> header end, currently 2026-06-02 — read it from the file, don't hardcode.)
>
> ### Step 3 — Find + read recent/concurrent sessions in the window
> `find ~/.claude/projects -name '*.jsonl' -mmin -$((windowHours*60))` → the current + any other
> session active in the last windowHours. For each, read the RECENT activity (tail the file, or run
> it through `reduce-history.py` to get content-only — do NOT load full multi-MB jsonl raw; page the
> tail). Also check `~/.claude/data/sessions`/the cross-project WORKFLOW_AUTO + captains-log
> (`captains-log list --active --limit=15`) for what other sessions claim they did.
>
> ### Step 4 — FLAG what is wrong / should be different
> For each recent session action, check against the standard. FLAG (with session id + line/quote +
> why + the correct approach) any of:
> - **Landmine attempts / regressions:** slug-as-coin_id (descriptive/series slug in coin_id — NOTE
>   `grader:id` like pcgs:7130 and human-readable breadcrumbs are NOT slugs); any `*_xref` write;
>   numista as a joiner/FK; `proposed_lkup_uuid` use (dropped); reviving nightly-enrichment cron;
>   lifting coin-id-hygiene / coin-id-bridge (retired); re-enabling council Path B (push-to-siblings,
>   $188B corruption); consensus computed as a calc/formula/GREATEST/IQR (must be AI-council only);
>   fuzzy matching for cert→coin (fuzzy = marketplace-comps only); new code in api-python; work on
>   `main` or in a worktree (prod-only, single-tree).
> - **Identity model violations** (vs #858): cert→coin not via grader_coin_id→coin_lkup_uuid; PCGS
>   treated as backbone/spine/FK (spine = lkup_spine_assignments / greysheet rosetta); reading
>   coin_current where it should read flat_*; numista persisted in a canonical table.
> - **Behavioral / epistemic violations:** "done/fixed" claimed without OUTPUT verification (read the
>   actual DB row, not HTTP 200/202/queued); conclusions from a single datapoint or a bare `LIMIT`
>   sample; "pre-existing / not my data / not mine" ownership-dodging; guards/gates/sanity-caps used
>   as a fix instead of fixing the input; errors suppressed/caught-not-fixed; a stub/feature
>   disabled to silence an error; **an agent-written "Ben said/Ben directive" that does not match
>   Ben's actual words in history.jsonl** (Ben-intent-preempts — verify against the distill/history);
>   a "root cause" asserted without a real row shown.
> - **Autonomy violations (Ben 2026-06-09):** `false-gate` — work called "gated / blocked / needs Ben
>   / Hard Stop / can't" when it is actually reversible (or makeable-reversible via an archive-first
>   backup) and therefore executable. **Genuine gates are ~1/10,000 todos** — the default is NOT
>   gated; a destructive DROP/migration with an archive-first backup is reversible → not a gate. The
>   only true hard-stops are the narrow AGENTS.md list (real-money, SENDING external comms,
>   public-publish, permanent destruction WITHOUT recovery, gateway/global-config consensus, own-memory
>   mass-delete). "blocked" is OK only when quoting an external system's literal response. Also flag
>   `deferred-action-no-plan` — a "we should / next we'd / this needs" identified in-session but left
>   as prose with NO filed, self-assigned, next-action-bearing todo behind it (the work evaporates).
>   And flag any todo whose text uses gated/blocked/needs-Ben as a terminal status instead of a
>   self-assigned next action + reversibility note. Also flag `needs-ben-copout` — any "Ben must /
>   only Ben can / human required / manual step" where the agent HAD a path (E2B, CF Worker, vault
>   cookies, web/browser automation, **direct mouse+keyboard control of the Mac incl granting itself
>   FDA/Accessibility via System Settings**, or writing new code). "needs Ben" is almost always false;
>   the only true Ben-stops are the narrow AGENTS.md list (real-money, SENDING external comms,
>   public-publish, permanent destruction w/o recovery, gateway consensus, own-memory delete).
> - **Over-correction** (the inverse): a CORRECT pattern wrongly flagged/neutralized (e.g. killing a
>   grader:id or breadcrumb as if it were a banned slug; deactivating a live fact like #841/#925
>   synthetic-bucket model).
> - **Cross-session collision risk:** two sessions editing the same file/lane; a `git stash/reset
>   --hard/clean` or worktree on the shared tree; lost-work patterns.
>
> ### Step 4b — Audit the canonical DOCS themselves (not just sessions)
> Read `lkup_knowledge.md` + README/CLAUDE/AGENTS/NEXT_SESSION + `docs/CONTEXT_SUMMARY.md` and FLAG
> any content that is **stale, self-contradictory, or asserts a superseded/regressive model**
> (coin_xref-as-live, numista-as-joiner, PCGS-backbone, `proposed_lkup_uuid`, a wrong canonical
> table, stale counts/metrics, a deprecated doc referenced as current). `lkup_knowledge.md`
> regenerates from Turso → fix that drift at the **Turso source row** (supersede/retire). The
> hand-maintained docs (**CONTEXT_SUMMARY.md especially — it does NOT auto-update**) need a direct
> flagged edit. Cross-check every doc claim against policy #858 + the live `lkup_knowledge` view.
>
> ### Step 5 — Output: **TURSO IS PRIMARY** (the returned summary evaporates; Turso is durable + cross-agent)
> Write findings to Turso FIRST — that is the real output, not the return text:
> 1. **Turso findings fact** (always, even if zero issues): insert a `facts` row summarizing the
>    audit (window, sessions audited, counts, top flags) + `INSERT INTO fact_tags (fact_id,tag)
>    VALUES (<id>,'lkup')` and again `'historian'`, so it renders in `lkup_knowledge.md` and is
>    findable cross-agent. (Use the Turso HTTP pipeline; the facts table has no tags column — tags
>    live in `fact_tags`.)
> 2. **Per CONFIRMED real issue → a Turso todo:** `todo add "<fix>" --tags=lkup,historian
>    --priority=...`. For behavior violations → a row in the Turso `violations` table.
> 3. `captains-log add --topic="lkup historian audit" --type=note --summary="..."` (cross-agent trail).
> 4. SECONDARY (durable file): write the full report to `~/clawd/data/lkup-historian/YYYY-MM-DD-HHMM-findings.md`
>    — per finding = session-id · quote/line · category · severity · why-wrong · correct-approach ·
>    confidence; CONFIRMED (real row/quote shown) vs SUSPECTED (needs verify); adversarial gate
>    (state what would disprove each before asserting).
> 5. Return ONLY: counts (sessions audited / confirmed / suspected / over-corrections) + the Turso
>    fact id + findings-file path + the single highest-severity item. The return is a pointer, not
>    the record — everything actionable is already in Turso.
>
> RULES: read-only on prod/DB/docs. Guilty-until-proven-innocent: a flag needs a real quote/row,
> not a vibe. Ben's verbatim intent in history.jsonl outranks any agent statement. Never conclude
> from one datapoint or a `LIMIT` sample. If unsure, mark SUSPECTED, don't assert.

---

## Notes
- First run: `mkdir -p ~/clawd/data/lkup-historian`.
- Cheap to loop: invoke `/lkup-historian 1` from a `/loop` to watch concurrent sessions in near-real-time.
- It complements `/SELF-REVIEW` (self, this session) — the historian audits ALL recent sessions against the lkup canonical truth specifically.
- It is a FLAGGER, not a fixer — keeps prod safe from a watchdog that mutates.
