---
name: grok-image
description: Generate images (including images preserving a real person's likeness) by driving the Grok web UI at grok.com with browser automation. Use when any image needs to be generated or edited and the Gemini/OpenAI image APIs are unavailable. As of 2026-08-03 this is the ONLY working image-generation path on this machine.
---

# grok-image — the working image-generation path

**Status 2026-08-03: Grok web UI is the only image generator that works on this machine.**
Every API path is dead. Do not burn an hour rediscovering this — the evidence is below.

## Dead paths (verified 2026-08-03, do not retry without new credentials)

| Path | Result |
|---|---|
| Gemini AI Studio, all 4 vault keys (`google_ai_api_key`, `google_ai_api_key_fallback`, `gemini_api_key`, `kbyg_gemini_api_key`) | HTTP 429 `limit: 0` on **every** image model. `limit: 0` = no entitlement at all — backoff can never succeed. |
| Vertex AI (`heimdall-8675309` + every other GCP project) | HTTP 403 `This API method requires billing to be enabled`. No project has billing on. |
| OpenAI `gpt-image-2` (`openai_api_key`) | HTTP 400 `Billing hard limit has been reached` (org-level — a new key won't help). |
| OpenAI admin key (`openai_admin_bigmac`) | Missing scope `api.model.images.request`. |
| xAI API (`xai_api_key`, `grok_api_key`) | `permission-denied` — team has used all available credits. |
| Adobe MCP | Adobe's own docs: *"Most generative AI capabilities... are not available"*; photo compositing explicitly unsupported. |
| Local | No Draw Things / ComfyUI / SD. LM Studio has text + embedding models only. |
| **Grok CLI** (`~/.grok/bin/grok`, `superagent-ai/grok-cli` v1.1.6) | `AI_APICallError: Forbidden` — it calls the **xAI API**, not the grok.com subscription. Buying SuperGrok would NOT fix it; only xAI API credits would. |

**grok.com free web tier still generates images** — that's why the browser path works while
every API is dead. It DOES have a daily image cap (hit 2026-08-03 after ~4 images).

Unblocking any API path is a **billing action = Ben's call**. Don't attempt it.

## Prerequisite: login

grok.com requires an X login. **Never type credentials** — that's a hard prohibition.
Click **"Continue with Google"** on the X OAuth screen; if Ben's Google session is live it
completes with no password entry. Otherwise ask Ben to click Log in.
Account: `Ben Fife / grok@boringdata.com`.

## Workflow

1. `tabs_context_mcp` → `tabs_create_mcp` → `navigate` to `https://grok.com`.
   Allow **~8-15s** to load; the first screenshot often returns a black frame — wait and retry.
2. `find` → "file input for attaching images" → `file_upload` with the reference photos.
   Multiple references in one call is fine and improves likeness (keep total under 10 MB).
3. Click the composer, `type` the prompt, press `Return`.
4. Wait ~20-30s ("Worked for 25s"), then `screenshot` to confirm the image rendered.
5. Continue in the **same thread** for additional images — Grok holds the likeness across turns,
   so follow-ups only need "same man, same exact face and likeness".

## Hard-won gotchas

**Composer input — always use `execCommand('insertText')`, never `type` for long prompts.**
Typing a long prompt with `computer`→`type` **silently strips every space**
(`brownhair,andafullbeardthat...`). It is length/speed related, NOT newlines. Reliable method:

```js
const ed = document.querySelector('[contenteditable="true"]');
ed.focus();
const sel=window.getSelection(), r=document.createRange();
r.selectNodeContents(ed); sel.removeAllRanges(); sel.addRange(r);
document.execCommand('delete', false, null);   // clear
document.execCommand('insertText', false, PROMPT);
ed.innerText.length + ' | spaces: ' + (ed.innerText.split(' ').length - 1);  // verify!
```
`insertText` delivers the string as ONE input event, so React can't drop characters.
**Always assert the space count** before submitting.

- The composer is a **contenteditable DIV**, not a textarea — `form_input` fails with
  `Element type "DIV" is not a supported form input`.
- **A cookie "Privacy Preference Center" modal silently opens and eats all input.** This is
  the real cause of the "frozen renderer" symptoms: `screenshot` times out with
  *"Script injection timed out"*, `Return` does nothing, and CDP throws
  `Input.dispatchKeyEvent timed out`, while `javascript_tool` still works fine.
  **Diagnose with JS, not screenshots** — if you see buttons named `Reject All` /
  `Confirm My Choices` / `Filter Cookie List`, the modal is up. Click **`Reject All`**
  (most privacy-preserving; sanctioned by the standing cookie-banner rule) and input resumes.
**SUBMITTING — use `form.requestSubmit()`. This is the single most important gotcha.**
After `execCommand('insertText')`, React's synthetic handlers often never see the text, so the
message will NOT send. Clicking the `Submit` button ref, pressing `Return`, and typing a
trailing space to nudge React ALL fail silently — the text just sits in the composer.
This works every time:

```js
document.querySelector('form').requestSubmit();   // fires the real submit handler
```
Confirm it took: the URL changes to `/c/<uuid>` and
`document.querySelector('button[aria-label="Stop model response"]')` becomes non-null.
- Verify submission by JS, not by the screenshot:
  `!!document.querySelector('button[aria-label="Stop model response"]')` = generating.
- Aspect ratio: "tall portrait 11:17" works; output lands ~784x1168 / ~816x1264 (~0.65).

## Retrieving the finished image

`assets.grok.com` returns **403 to plain curl** — it needs session cookies.
Cheapest reliable path is the UI download button:

```
find → "Download button on generated image" → computer left_click(ref)
# then: mv "$(ls -t ~/Downloads/*.jpg | head -1)" "<destination>"
```
Do NOT base64 the image back through `javascript_tool` — a 390 KB jpg is 521 KB of base64,
far too expensive for tool output.

## Prompting notes

- **Reference photos leak their contents.** The `ben_face_studio.jpg` reference has QR codes
  on the cap and shirt, and Grok faithfully reproduced BOTH into the output. When using it,
  explicitly say "no QR codes, plain cap, plain shirt".
- Grok garbles slab labels (`PCS`, `NIGC`). Saying "realistic PCGS label" helps but does not
  fully fix it — treat holder text as decorative.

## Likeness references (Ben)

Canonical set: `~/clawd/data/whatnot-show-prompts/ben-references/`

| File | What it is |
|---|---|
| `ben_face_studio.jpg` | 2048px clean front-facing studio-style portrait — **best framing** |
| `ben_real_4.jpg` / `ben_face_a.jpg` | Real camera selfie, July 2026, sharp close-up face |
| `ben_real_5.jpg` / `ben_face_b.jpg` | Real camera selfie, July 2026 |

**Ben's standing rule (2026-08-03): real face, splash styling.** Feed Grok the real photos
for the face, and describe the established art direction in words. Do NOT use an existing
AI-generated splash as the face reference — that's a copy of a copy and it drifts.

**Describe his actual face explicitly**, because models default to a generic heavyset
bearded man: fair skin, blue-grey eyes, receding light-brown hair, full beard that is
**grey/silver through the chin and moustache** with darker blonde-brown sides,
**lean-to-average build, not heavy**. Say "do not slim him, do not make him heavier,
do not darken his beard."

### More real photos
The Photos library has **6,358** face records tagged `Ben Fife` (person `Z_PK=586`).
Query for large, front-facing, in-focus ones:

```sql
-- against a COPY of ~/Pictures/Photos Library.photoslibrary/database/Photos.sqlite
SELECT a.ZDIRECTORY||'/'||a.ZFILENAME, f.ZSIZE, f.ZQUALITY, f.ZPOSEYAW
FROM ZDETECTEDFACE f JOIN ZASSET a ON a.Z_PK=f.ZASSETFORFACE
WHERE f.ZPERSONFORFACE=586 AND f.ZSIZE>0.13 AND f.ZQUALITY>0.5
  AND abs(f.ZPOSEYAW)<0.25 AND a.ZTRASHEDSTATE=0
ORDER BY a.ZDATECREATED DESC LIMIT 15;
```
Originals live under `~/Pictures/Photos Library.photoslibrary/originals/<dir>/<file>`.
**Many are iCloud placeholders and missing on disk** — check `-f` before converting.
Convert with `sips -s format jpeg -Z 1400 <src> --out <dst>`.

## Related

- `whatnot-show-images` — Whatnot show splash specs (canvas, safe zones, show catalog).
  Its Gemini script is dead; it routes here for generation.
- `nano-banana`, `nano-banana-pro`, `openai-image-gen` — **all currently non-functional**
  (dead credentials above). Left in place for when billing is restored.
