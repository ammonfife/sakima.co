# Speedbumps hit while building the first deck (Ragnar, 2026-09-05) — and their fixes

| speedbump | root cause | fix / route-around |
|---|---|---|
| `/v1/score` answered 202 `not_scorable_yet` on every retry for customer text | `/api/score` tried only the exact text as a Matrix row | n-gram decompose added to `/api/score` (`demo_server.py`, space `matrix:ngram`). First touch now HTTP 200 <1 s |
| Negative seeds silently dropped or ADDED | `-term` was parsed nowhere in `heimdall_core/matrix.py`; a literal `-ragnar lothbrok` column got minted (r=+0.76 with the bare term) | `matrix.parse_term`/`split_sign`; `audience_columns` negates; `register_columns`/`mint_columns` never mint signed names; `scripts/remint_signed_audiences.py` repairs saved audiences; `scripts/fix_signed_debris_poles.py` rewrites literal signed columns in place |
| Seed formula weights had nowhere to live in the saved-audience store | store holds terms only | weight rides the term: `term*2`, `-term*0.5` |
| Batch scoring run died mid-way | peers restart the demo (launchd `com.heimdall.demo`) every few minutes during active work | `deck_data.py::batch` retries with back-off up to ~6 min; never start a long run without it |
| `/api/batch_score` "missing" list was wrong | `in_corpus` = fingerprint presence, not row presence | chart on `h is not None` |
| Per-entity "lift vs Average Person" nonsense (creatine −0.315) | the 20-generic-row control is a popularity axis | y = segment h; average = band of the middle half of entities |
| Substitute search over `master_keyword` with LIKE took >10 min | 2.8 M rows, no index on surface substrings | index `rows.json` by first token in memory (2.6 s) |
| Keynote `.key` decks would not export (partner deck 244 slides, Foxtrot) | iCloud "Modifications aren't in sync" sheet blocks AppleScript export; separate exports also raced | `keynote-parser unpack` on a zip built from the package's `Data/`, `Metadata/` + extracted `Index.zip`; read text from the Slide-*.iwa.yaml |
| No images from any Gemini key (5 keys, all `429 … free_tier … limit: 0` for image models) | Gemini image models not enabled on these projects | Cloudflare Workers AI `@cf/black-forest-labs/flux-1-schnell` with `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` from `~/.zshrc` (`scripts/cfgen.sh`); no `width`/`height` params; regenerate anything with lettering |
| `python3` on PATH has no duckdb | system python vs pyenv | `~/.pyenv/versions/3.13.7/bin/python3.13` for anything in phase1 |
| `artifacts/columns/*.json` (curated declared columns) untracked | `artifacts/` gitignored wholesale | `git add -f` the small curated files |
| `knowledge-search --keyword` crashed with an uncaught TimeoutError | `searchKnowledgeView` db() call unwrapped | fixed in bigmac-state `scripts/knowledge-search.js` (degrades to a warning) |
| zsh ate `$ACC`, `====`, `=cmd` | zsh `=` expansion and variable names from `source ~/.zshrc` | quote, or use Python for string work |
| Chart labels illegible on the slide | 9.6×6 in figure shrunk to 8.5 in | render at 8.5×5.3 in, labels 8.3/9.6 pt, bubbles 26+14·log(v)^1.6 |
| Key-insight callouts ran off the slide | 7 callouts + 4 negatives | 6 + 3, 0.6 in step |
| 5-card strategy page overflowed | 2-column card grid | 3 columns when cards > 4 |
