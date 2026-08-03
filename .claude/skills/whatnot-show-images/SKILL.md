---
name: whatnot-show-images
description: Generate Whatnot show splash/thumbnail images for sakima's coin show. Use when asked to create, regenerate, or update Whatnot show cover images, thumbnails, splash screens, or live show previews. Handles new show concepts, iterative edits, and batch generation. Uses Gemini 3 Pro Image API with Ben's likeness reference.
---

# Whatnot Show Images

Generate and iterate on Whatnot show splash images for sakima's coin shows.

## Canvas Specs

- **Format:** 11:17 portrait (1080×1880px recommended)
- **Critical safe zone:** center ~750px wide × ~1100px tall (keep all text/faces here)
- **Top margin:** ≥150px clear before first text element
- **Bottom margin:** ≥150px clear after last text element
- **Side margin:** ≥65px (9:16 preview crops ~64px per side)
- **No text boxes/banners** — text must be part of the design, not in overlaid panels

## Output Location

`/Users/benfife/Desktop/Whatnot Streams/`

Name files descriptively: `show-name_v1.png`, `show-name_v2.png`, etc.

## Generation — use the `grok-image` skill

> **⚠️ 2026-08-03: the Gemini path below is DEAD.** All 4 Gemini keys return
> `limit: 0` on every image model, Vertex has no billed project, and OpenAI is at its
> billing hard limit. **Use the `grok-image` skill** — the Grok web UI is currently the only
> working image generator on this machine. It documents the composer/submit gotchas and the
> real likeness references. `scripts/generate_show_image.py` will fail until billing changes.

<details><summary>Legacy Gemini API (non-functional — kept for when billing is restored)</summary>

Use **Gemini 3 Pro Image** for new images or edits with Ben's likeness.
Use **Gemini 2.0 Flash Exp Image** for fast iterations without people.

```bash
API_KEY=$(secrets get google_ai_api_key)
MODEL="gemini-3-pro-image-preview"  # for people/likeness
# MODEL="gemini-2.0-flash-exp-image-generation"  # for fast/no-people
URL="https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}"
```

See `scripts/generate_show_image.py` for the full generation script.
</details>

## Workflow

### New image from scratch

1. Confirm show concept: title, theme, items (floor vs wins), any people
2. Check `references/show-catalog.md` for style patterns from existing shows
3. Use Ben's reference: `assets/ben_likeness_reference.jpg` (copy of `fast_games_v5.png`, downscale to ~640px wide to cut input tokens ~9x)
   - Note: most files in `Whatnot Streams/` named `.png` are actually JPEGs. The script sniffs magic bytes — never trust the extension.
4. Run `scripts/generate_show_image.py` with text prompt
5. Open in Chrome: `open -a "Google Chrome" <path>`
6. Iterate with v2, v3... until approved

### Editing existing image

- Pass the existing PNG as `inline_data` reference image to Gemini
- Be specific: name the exact element to change, describe the replacement
- Preserve everything else explicitly in the prompt

### Batch (multiple shows)

- Generate in parallel if concepts are independent
- Save each to its own file, open all in Chrome when done

## Prompt Patterns

See `references/prompt-patterns.md` for proven prompts by show type.

**Key rules:**

- Always specify "tall portrait 11:17 ratio" in prompt
- Say "no text boxes or banners — text is part of the design"
- Say "text safe zones: nothing within 150px of top or bottom edge"
- For slabs: "PCGS/NGC graded slabs with realistic labels" (reduces hallucination)
- Describe floor items as "scattered low" and hero items as "prominent center"

## Show Types

See `references/show-catalog.md` for full catalog.

**Common formats:**

- **Coin floor + slab wins:** wheats/buffalos/silver grams as floor, graded silver eagles/Morgans/Peace dollars as hero
- **Fast games:** FAST GAMES title, $2 max shipping hook, Mr. Beast Giveaway element
- **Fractional silver:** Valcambi bars, 1g–100g, premium brand visual
- **Only gram show:** single gram focus, minimal design

## Whatnot Rules

- ❌ No Whatnot wordmark/logo on thumbnail
- ❌ No landscape orientation
- ❌ No small low-contrast text
- ✅ Portrait only
- ✅ High contrast text
- ✅ Keep critical info in yellow safe zone center
