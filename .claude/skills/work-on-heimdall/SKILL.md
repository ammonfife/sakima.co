---
name: work-on-heimdall
description: Onboarding skill for any agent or Claude session picking up work on Ben's Heimdall monetization/productization effort. Run this skill first. Covers the 15-year methodology arc (Cerebro → Heimdall → Scheme L), the private archive monorepo, the proprietary-only IP stance, the center-to-left-of-center targeting constraint, and where each workstream (biz dev, technical archaeology, scheme L development) lives. Sub-agents append their findings to this skill as they learn.
metadata:
  {
    "openclaw":
      {
        "emoji": "🗝️",
        "requires": { "bins": ["gh", "turso", "huggingface-cli"] },
      },
  }
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


# /work-on-heimdall — onboarding skill

Run this every time you start work on Heimdall monetization, archive consolidation, or scheme L development. The goal: zero re-onboarding cost across sessions and sub-agents.

---

## 0. READ FIRST — Ben's locked strategic decisions

These are NOT up for debate. If you think you should change one of these, SendMessage to Ben and wait for his explicit go-ahead.

1. **Proprietary only.** No OSS, no academic papers with method details, no licensing to competitors. Internal tools (`~/bin/scheme-L-score`, `~/bin/pole-build`) stay internal. The 48GB data stays behind the API wall.
2. **Center-to-left-of-center positioning only.** Target = Dem/progressive campaigns, causes, foundations, labor, UN-Foundation-adjacent orgs. **No Republican work.**
3. **Customer-facing language never mentions "geospatial."** Public positioning is "audience voice intelligence API" / "revealed-preference behavioral signal" — NOT geospatial, NOT Pearson correlation, NOT Heimdall-as-technology. Marketing category matters for valuation multiple.
4. **"Heimdall" stays internal codename.** Public product brand is TBD (candidates: Voicebox, Echo, Cerebro, Clearwater, Resonance). Ben decides the brand.
5. **Cloud marketplace distribution is the primary GTM.** AWS Marketplace first, then GCP, then Azure. Enterprise direct sales as upsell layer on top.
6. **Pricing tiers (approximate):** Starter $299/mo, Pro $1,499/mo, Enterprise $5-25K/mo, Custom (direct).
7. **Benchmark strategy: own it.** Build "Audience Voice Authenticity Benchmark v1" ourselves. Block unilateral competitor benchmarks via MSA clause. Invite competitors to submit to OUR benchmark.

---

## 1. The 15-year arc (context you need before any work)

| Year | System | What it was | Where the artifacts live |
|---|---|---|---|
| 2014–2017 | **Cerebro** | Java REST + PHP UI for audience-vocabulary mapping via geospatial keyword correlation. Used at Boncom. Included the "Google Translate for Religious Concepts" UI (UN Foundation, LDS Church work). | `~/github/ammonfife/heimdall-archive/02_cerebro_boncom/` |
| 2015 | **Prezi "Missionary Work and Big Data"** | The DECK that crystallized the whole approach. Slide title: "Google Translate for Religious Concepts." | `~/github/ammonfife/heimdall-archive/01_origin_2015_unf/missionary-work-and-big-data.prezi/` |
| 2017–2018 | **CHD LDS Church data science** | Church History Department commercial engagement. Applied Cerebro methodology to faith-crisis analysis. CONFIDENTIAL. | `~/github/ammonfife/heimdall-archive/03_chd_lds_2017-2018/` |
| 2020 | **DigiMarCon "Data is Delicious"** | Conference talk that publicly framed the approach to marketing audience. | `~/github/ammonfife/heimdall-archive/03b_digimarcon_2020/` |
| 2020–2023 | **Heimdall (Tableau era)** | Tableau-powered production (`.hyper` / `.twb` files) for agency clients (Hopin OOH, Utah tourism, Belle Medical, TAB Bank). | `~/github/ammonfife/heimdall-archive/04_heimdall_tableau_2020-2023/` |
| 2023–present | **Heimdall (PySpark + GCP)** | Production system at Genomic Digital. `ammonfife/heimdall` GitHub repo + GCP project `heimdall-8675309`. | Live: `~/github/ammonfife/heimdall/` (separate repo) |
| 2024 | **Genomic Digital Overview** | Agency pitch deck naming Heimdall AI + Genormous ML as the proprietary engines. | `~/github/ammonfife/heimdall-archive/05_genomic_digital_2024-2026/` |
| 2026 | **Scheme L** | Nonlinear scoring (`cbrt(cos_A³ − cos_B³)`) on neural embeddings + opposing concept poles. Complementary to Heimdall's geospatial core. | `~/github/ammonfife/heimdall-archive/06_scheme_L_2026/` |

---

## 2. Key paths (memorize these)

| Path | What's there |
|---|---|
| `~/github/ammonfife/heimdall-archive/` | **Private monorepo** — the consolidated IP archive (889MB+). Private on GitHub. |
| `~/github/ammonfife/heimdall/` | Live production PySpark correlation engine (existing public-by-design repo). |
| `/Users/data/HeimdallData/` | **48GB raw data** — 5 TSV shards, keyword × (50 states + ~100 reference entities) correlation matrix, Nov 2021. |
| `~/synthetic-rich-poor-vectors.npz` | Scheme L's example cluster vectors (rich/poor). Used by `scheme-L-score`. |
| `~/bin/scheme-L-score`, `~/bin/pole-build` | Internal scheme L tools. Not published externally. |
| `~/embeddings-m1-direct.json`, `~/embeddings-m2-hash-embed.json` | Cached Qwen3-Embedding-8B vectors for 1000 topics (scheme L training data). |
| `~/hf-datasets/jaswanth-qwen3-8b-distill/` | 1.275M text+vector pairs, Qwen3-Embedding-8B compatible. |

---

## 3. Active workstreams & who's working on what

Check these TODO files before starting anything — another agent may be mid-task.

| Workstream | Owner (agent) | TODO file | Inventory / output files |
|---|---|---|---|
| **Biz dev & monetization (strategy)** | Garcia | `~/github/ammonfife/heimdall-archive/biz_dev/GARCIA_TODO.md` | `target-accounts.csv`, `pricing.md`, `benchmark-spec.md`, `branding-brief.md`, `pitch/` |
| **Technical archaeology & cloud audit** | Lance | `~/github/ammonfife/heimdall-archive/tools/LANCE_TODO.md` | `REPO_INVENTORY.md`, `CLOUD_INVENTORY.md`, `DROPBOX_ICLOUD_INVENTORY.md`, `HYPER_INVENTORY.md`, `AGENT_KNOWLEDGE_SUMMARY.md` |
| **Sales & marketing execution** | Chloe | `~/github/ammonfife/heimdall-archive/marketing/CHLOE_TODO.md` | `landing_page/`, `outreach/`, `paid_ads/`, `thought_leadership/`, `events/` |
| **Scheme L development / iteration** | Main Claude (or dedicated session) | `~/github/ammonfife/heimdall-archive/06_scheme_L_2026/SCHEME_L_TODO.md` (create if missing) | Scripts in `06_scheme_L_2026/` |
| **API build / marketplace listing** | Not yet assigned | TBD — create `heimdall-api-todo.md` when work starts | TBD |

**Clean workstream boundaries (enforce these, don't overlap):**
- **Garcia owns**: strategy, pricing tiers, target account list, pitch deck content, benchmark design, branding research. Produces raw materials.
- **Chloe owns**: marketing website, ad campaigns, outbound sequences, PR & thought leadership, conferences/events. Executes channels using Garcia's raw materials.
- **Lance owns**: all code, cloud infrastructure, data, repos, Tableau, hyper extracts, lift-and-constrain. Never touches pitch / sales / marketing content.
- **Main Claude owns**: strategic calibration across all three, scheme L technical iteration, session-level decisions, Ben-facing direct updates.

If you're a sub-agent picking up work: **read your TODO file, then SendMessage to main Claude for any ambiguity** before writing anything new.

---

## 4. State persistence — Turso + local files

**Turso (shared across all BIGMAC agents):**
- Run `claude-sync pull` at session start to re-hydrate memory.
- Run `claude-sync push` after any significant write to keep state durable.
- Tag memories with `project=heimdall-bizdev` (Garcia), `project=heimdall-archaeology` (Lance), `project=heimdall-scheme-l` (main).
- Knowledge search your own history: `knowledge-search "heimdall" --agent <your-name>` before starting work — you've probably seen it before.

**Local files (always authoritative over memory):**
- TODOs in the monorepo (see table above) are the source of truth for in-progress work.
- Decisions/outcomes get a dated entry in `~/github/ammonfife/heimdall-archive/DECISIONS_LOG.md` (create if absent).
- Any generated artifacts (pitch decks, demos, specs) live inside the monorepo, not in `~/Documents/` or `/tmp/`.

---

## 5. Communication protocol

**Between sub-agents (Garcia ↔ Lance):** SendMessage. Don't duplicate each other's work. Biz dev decisions that need technical context → Lance; technical decisions with customer implications → Garcia.

**Between sub-agents and Ben:** via main Claude session (preferred) OR directly via `bluebubbles` / `slack` if urgent and explicitly authorized. Don't ping Ben at 3am for non-urgent work.

**Cost-sensitive decisions:** ANYTHING that spends money (domain registration, benchmark funding, contractor hiring, cloud resource creation) must be flagged to Ben with itemized cost BEFORE execution. No exceptions.

---

## 6. Security & IP posture

- **Every file in the archive is confidential.** The repo is private on GitHub. No screenshots, no copy-pasting to chat tools without verifying the destination is under NDA.
- **Client names from decks (LDS Church, UN Foundation, Hopin, Visit SLC, etc.)** — these are historical engagements. When writing outputs for current marketing, anonymize unless Ben has explicitly approved naming them.
- **The 48GB data is the moat.** It NEVER leaves Ben's machine. Any API product serves computed outputs over HTTP, never raw rows.
- **Scheme L methodology stays internal.** External positioning uses "proprietary behavioral signal" as the description. Don't elaborate in public-facing copy.

---

## 7. Useful commands

```bash
# Resync state at session start
claude-sync pull

# Search memory for prior Heimdall context (across all agents)
knowledge-search "heimdall" --tables memory,facts,policies

# Run scheme L on arbitrary text
scheme-L-score -v "some text to score"

# Build a new concept pole for scheme L
pole-build --name my-new-pole --terms "term1,term2,term3"

# Monorepo state
du -sh ~/github/ammonfife/heimdall-archive/*/

# Garcia's current status
cat ~/github/ammonfife/heimdall-archive/biz_dev/GARCIA_TODO.md

# Lance's current status
cat ~/github/ammonfife/heimdall-archive/tools/LANCE_TODO.md

# Save your own state
claude-sync push
```

---

## 8. Sub-agent appendix — findings & amendments

Sub-agents append here as they learn. Use dated sections. Don't delete prior entries; annotate or supersede with a new entry.

### Appendix entries

<!-- TEMPLATE
### YYYY-MM-DD — <agent name> — <short topic>

<finding, decision, or amendment>

<!-- end template -->

<!-- Garcia and Lance: append your findings below as you go -->

---

## 9. If you're stuck or confused

1. Re-read this skill (it may have been updated since you last ran it).
2. Read your TODO file.
3. SendMessage to main Claude with: what you're doing, what's blocking, what you need.
4. Don't guess on strategic questions. Ben has spent 15 years on this; he has strong opinions. Ask.
5. Don't touch other agents' files without explicit handoff.

---

## 10. When this skill is stale

If you notice a section of this skill is out of date (paths moved, decisions changed, workstreams added), **update it in place and note the change in §8 with a dated entry**. This skill is the durable source of truth; let it evolve.

Last verified: 2026-04-16 (main Claude session).
