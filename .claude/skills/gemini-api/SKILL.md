---
name: gemini-api
description: Use Google Gemini API directly via REST or SDKs (Python/Node.js) for text generation, vision, chat, streaming, and image generation (Imagen).
homepage: https://ai.google.dev/
metadata: {"moltbot":{"emoji":"♊️","requires":{"secrets":["google_ai_api_key"]}}}
---

# Gemini API

Direct API access to Google Gemini models (text, vision, chat, streaming) and Imagen (image generation).

## Reference Guide

**Full documentation:** `/Users/benfife/clawd/gemini-api-guide.md`

Contains:
- API authentication (key from secrets vault)
- Quick start examples (cURL, Python, Node.js)
- Advanced features (streaming, chat, vision, system instructions, image generation)
- Configuration options (temperature, tokens, safety)
- Pricing & rate limits
- Error handling
- Best practices

## Quick Start

### Get API Key

```bash
API_KEY=$(secrets get google_ai_api_key)
```

### Text Generation (cURL)

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Your prompt here"}]}]}'
```

### Image Generation (Python)

```python
import google.generativeai as genai

genai.configure(api_key="$(secrets get google_ai_api_key)")
model = genai.ImageGenerationModel("imagen-3.0-generate-001")

result = model.generate_images(
    prompt="A photorealistic cat wearing sunglasses",
    number_of_images=1,
    aspect_ratio="1:1"
)
result.images[0].save("output.png")
```

## Available Models

**Text & Vision:**
- `gemini-2.0-flash-exp` — Latest experimental (fast, cheap)
- `gemini-2.0-flash-thinking-exp-1219` — Reasoning model
- `gemini-1.5-pro` — Production pro model
- `gemini-1.5-flash` — Production flash model
- `gemini-pro-vision` — Vision capabilities

**Image Generation:**
- `imagen-3.0-generate-001` — Latest Imagen ($0.04/image)
- `imagen-2.0-generate-001` — Imagen 2.0 ($0.02/image)

## Common Use Cases

1. **Text generation** — Use flash for speed, pro for complex reasoning
2. **Image analysis** — Use `gemini-pro-vision` with image input
3. **Image generation** — Use `imagen-3.0` for creating images from text
4. **Streaming responses** — Set `stream=True` in Python SDK
5. **Multi-turn chat** — Use `start_chat()` to maintain context
6. **System instructions** — Set persona/behavior with `system_instruction`

## Pricing

**Text Generation:**
- **Gemini 2.0 Flash:** $0.075/1M input, $0.30/1M output
- **Gemini 1.5 Pro:** $1.25/1M input, $5.00/1M output

**Image Generation:**
- **Imagen 3.0:** $0.04 per image
- **Imagen 2.0:** $0.02 per image

## Notes

- API key stored in secrets vault as `google_ai_api_key`
- Free tier: 15 requests/min, 1M tokens/min
- Paid tier: 1000+ requests/min
- See full guide for advanced features and examples
