---
name: tag-whatnot-buyers
description: Post bare @mentions into a target Whatnot live-show chat using the proven E2B sandbox workflow and Sakima auth.
---

# /tag-whatnot-buyers — Post @mentions into a Whatnot live-show chat

Delegates to E2B desktop sandbox + Playwright + Sakima's Whatnot cookies to post a bare `@username` per chat line into a target live-show chat. Built for competitive-buyer outreach: grab a rival show's sold-buyers list, cross-tag them into one of our (or a consignor's) live show to funnel them over.

**First proved 2026-04-18** — 38/38 mentions posted across two batches (SHACK PACK TRANSCENDENT + CHASING KELLOGG GOLD #1) into Kyle's thesilverbandits live show, zero failures, total ~5 min wall clock, one reused sandbox.

**Canonical artifacts already on disk:**
- In-sandbox tagger (uploads into E2B and drives Playwright): `~/clawd/scripts/whatnot-tag-buyers.py`
- Local driver template (uploads files + kicks off remote run + downloads screenshots/logs): `~/clawd/scripts/whatnot-tag-driver.py`
- Proven cookie bundle: `~/clawd/data/whatnot-cookies/profile15-raw.txt` (Turso key `browser_auth:whatnot.com:ammonfife-profile15`)
- E2B API key: `~/clawd/data/whatnot-cookies/e2b_key.txt`

---

## When to invoke

Ben asks any variant of:
- "tag these buyers into <show URL>"
- "use e2b as sakima to tag these people one at a time"
- "cross-post these usernames into Kyle's show"
- "post @mentions for <list> into <show>"

Also invoke when running a competitive outreach sweep — scraped another dealer's sold-products feed, want to funnel their buyers to one of our streams.

**Don't invoke** if Ben wants an actual message (not just a bare mention), or if the target is a DM rather than a live-show public chat, or if the show URL isn't live. Those are different flows.

---

## Hard rules (Ben-stated, non-negotiable)

1. **Bare `@username` per line, no corny text.** Ben 2026-04-18: "DO NOT USE CORNY text, just tag them, that's all, one user per chat line." No "👋", no "check this out", no intro message. The `@mention` alone triggers the DM-style notification — that's the whole mechanism.
2. **E2B desktop sandbox only.** Never drive Ben's local Chrome, never use the Clawd extension profile. Per chloe's `feedback_e2b_primary.md` — auth-gated anti-bot sites go through E2B.
3. **Sakima is Ben.** Use he/him. The Whatnot account operator for this skill is Ben's `sakima` seller identity (Sakima LLC). Cookie bundle `profile15` is the one that logged in successfully first try.
4. **Throttle 3–5s** between posts. Whatnot chat rate-limits + auto-mutes if too fast.
5. **Screenshot every post** to `~/clawd/data/chloe-screenshots/<slug>/` — evidence trail + debugging anchor.
6. **Log every post** to `~/clawd/logs/<slug>.log` — timestamp, username, success/fail.

---

## Step 0 — Identity + target validation

Confirm before claiming a sandbox:

1. **Show URL** is a live `/live/<uuid>` Whatnot URL. Sold-out or scheduled-only shows don't have the chat input rendered — posting will silently fail.
2. **Buyer list** is saved durably (never `/tmp/`) as one `@username` per line. Order top-spender first so late-run cutoffs (e.g. show ends) still land the high-value ones. Save to `~/clawd/data/<batch-slug>.txt`.
3. **Dedup against overlap lists** before running. Per 2026-04-18: `@philme007` appeared in both SHACK PACK and Kellogg lists — tag ONCE total. If running multiple batches against the same show, maintain a `posted-so-far.txt` and pre-filter each new batch.

---

## Step 1 — Claim or reuse a warm sandbox

Warm pool first — the Cloudflare Worker keeps 3+ desktops available:

```bash
POOL=$(curl -sS https://e2b-pool-lb.sakima-api.workers.dev/pool/desktop)
SANDBOX_ID=$(echo "$POOL" | python3 -c "import json,sys; print(json.load(sys.stdin)['sandboxes'][0]['sandbox_id'])")
echo "Claimed: $SANDBOX_ID"
```

**Reuse if you're running a second batch within ~20 min.** Verify liveness:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "https://${SANDBOX_ID}.e2b.app/"
# 400 is NORMAL for /root path on E2B — NOT a dead sandbox. Any 2xx/3xx/4xx proves it's routing.
# Only 5xx or DNS failure means it's actually dead.
```

Reusing a sandbox saves ~30s (Playwright install + cookie load are cached).

---

## Step 2 — Run the driver

The reusable driver at `~/clawd/scripts/whatnot-tag-driver.py` does the full pipeline:

1. Uploads `whatnot-tag-buyers.py` + buyers.txt + cookies.json into the sandbox
2. `pip install playwright + playwright install chromium` if not cached
3. Launches Chromium with Sakima's cookies injected
4. Navigates to the show URL, waits for `[data-testid="chat-input"]`
5. For each `@username` in buyers.txt:
   - Click chat input → type `@username` → press Enter
   - Screenshot to `/tmp/shot-<ts>-<username>.png` in sandbox
   - Sleep 3–5s (randomized)
6. Final full-page screenshot
7. Downloads all screenshots + log back to `~/clawd/data/chloe-screenshots/<slug>/` + `~/clawd/logs/<slug>.log`

To run a new batch, **copy the driver, update the 3 constants at top, execute:**

```bash
# Parameterize
BATCH=kellogg-gold
SHOW_URL=https://www.whatnot.com/live/6a1204bf-d1d8-4287-aa19-618ce60ecc9a
BUYERS_FILE=~/clawd/data/kellogg-gold-buyers-ordered.txt

# Copy driver
cp ~/clawd/scripts/whatnot-tag-driver.py ~/clawd/scripts/whatnot-tag-driver-${BATCH}.py

# Edit constants at top of copy:
#   SANDBOX_ID
#   SCRIPT_SRC (keep as whatnot-tag-buyers.py — same tagger, different inputs)
#   BUYERS_SRC = "$BUYERS_FILE"
#   LOCAL_SHOT_DIR = .../chloe-screenshots/${BATCH}-tagging
# (buyers.txt path + show URL + log slug. show URL lives inside whatnot-tag-buyers.py as SHOW_URL constant — override via env or edit.)

# Run
python3 ~/clawd/scripts/whatnot-tag-driver-${BATCH}.py
```

---

## Step 3 — Scroll-grep pre-pass (dedup against pre-tagged)

**REQUIRED when Ben says "I already tagged some of them" or when re-running into the same chat.** The 2026-04-18 second run skipped this and posted blindly — harmless double-pings but wasted cycles.

Before the posting loop, add this pre-pass inside `whatnot-tag-buyers.py`:

```python
# Scroll chat panel up to load backlog
chat_panel = page.locator('[data-testid="chat-messages"]')  # verify selector
for _ in range(5):
    chat_panel.evaluate("el => el.scrollTop = 0")
    time.sleep(0.4)

# Extract last N messages as plain text
backlog_text = chat_panel.inner_text()

# Filter input list
dedup_list = []
already_tagged = []
for uname in input_buyers:
    if f"@{uname}" in backlog_text:
        already_tagged.append(uname)
    else:
        dedup_list.append(uname)

log.info(f"Skipping {len(already_tagged)} already-tagged: {already_tagged}")
```

If Ben pre-tagged manually, those `@username` strings render in the backlog as plain text mentions and are grep-able. Whatnot doesn't obfuscate mention text — the `@` + literal handle is always in the DOM.

---

## Step 4 — Report back

End-of-run template Ben expects:

```
**Attempted:** <N>
**Posted:** <M> / <N> (XX%)
**Failed:** <k>
**Skipped — already-tagged in chat:** <j> (list names)
**Skipped — cross-list overlap:** <j> (list names, e.g. @philme007)

**Sandbox used:** <id> (fresh|reused)
**Auth:** browser_auth:whatnot.com:ammonfife-profile15 (<n> cookies) — "<identity> joined" visible
**Chat selector:** [data-testid="chat-input"] (first try|retry with <fallback>)
**Throttle:** 3–5s random, total run <Nm Ns>
**Order:** top-spender first: @first → @second → ... → @last

**Log:** /Users/benfife/clawd/logs/<slug>.log
**Screenshots:** /Users/benfife/clawd/data/chloe-screenshots/<slug>/
**Last screenshot:** .../zz-final-<iso-ts>.png
**Driver:** /Users/benfife/clawd/scripts/whatnot-tag-driver-<slug>.py (reusable)
```

---

## Gotchas learned from 2026-04-18 runs

- **"sakima joined" appears in final screenshot** → auth worked. If missing, the cookie bundle is stale → try a different `browser_auth:whatnot.com:*` Turso key.
- **Chat append animates ~0.8s after Enter** → a screenshot taken immediately after `press("Enter")` may show the input still holding text. Take the verify-screenshot AFTER the 3–5s throttle, not before.
- **Sandbox direct_url `/` returns 400 not 200** → that's E2B routing behavior (no app listening on root). Don't interpret as dead. Only DNS-level failure = dead.
- **Playwright install is slow first time (~60s)** → budget for it on a fresh sandbox. Reuse saves ~30s.
- **Claude Code subagent `chloe` vs OpenClaw `chloe`** are different personas. The Claude Code one (at `~/.claude/agents/chloe.md`) is scoped to paid-ads and may reject this task. If delegating, give the spawned agent the FULL brief with the proven paths inline — don't assume she'll re-read her own memory files.

---

## Anti-patterns

- **DON'T** spawn two tagging agents in parallel posting to the same chat as Sakima — cookie-session state collides and rate-limits hit mid-batch.
- **DON'T** add greetings, emojis, or context to the mention. Ben's rule: bare `@username`. Any additional text kills the "DM-ping" signal that triggers notifications on the recipient's side.
- **DON'T** skip screenshots to "save time" — they're the only way to prove post success/failure after the fact, since chat history eventually scrolls away.
- **DON'T** post to a show you don't have auth/admin on. The target show must be one where Sakima has posting rights (consignor-granted, team-admin, or his own channel).
- **DON'T** rerun the same batch file without dedup against the prior run's log — you'll re-tag everyone.

---

## Related skills + context

- `~/.claude/projects/-Users-benfife/memory/feedback_sakima_is_ben_he.md` — Sakima is Ben, he/him pronouns
- `~/clawd/agents/chloe/memory/feedback_e2b_primary.md` — E2B is primary browser for all chloe browser work
- `~/clawd/agents/chloe/memory/notes_whatnot_signup_phone.md` — Surge phone for new Whatnot account signup (if ever need another account)
- `/captains-log` — log the batch as type=milestone with the result counts + script paths so future agents find the pattern
- `/use-e2b` — general E2B sandbox skill (this skill is a specialization)
