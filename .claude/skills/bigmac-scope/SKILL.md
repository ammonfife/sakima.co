# bigmac-scope — Universal Network + Event Recorder

A Chrome MV3 extension that captures all network traffic (fetch, XHR, WebSocket) and DOM click events on **any webpage**. Works on claude.ai, Whatnot, eBay, GitHub, anything.

**Extension path:** `~/github/ammonfife/bigmac-scope/`
**Version:** 1.0.0

---

## Loading the Extension

1. Open Chrome and navigate to `chrome://extensions`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the directory: `~/github/ammonfife/bigmac-scope/`
5. The BigMac Scope icon appears in the toolbar

After any code change: click the refresh icon on the extension card in `chrome://extensions` (or bump the version in `manifest.json` to force a clean reload).

---

## Usage

### Record Mode
- Click the extension icon to open the popup
- Click **Start Recording** — the red dot pulses, all network + click events are captured
- Navigate the site, interact as normal
- Click **Stop Recording** when done
- Event count appears in the counter badge

### Capture Now (instant snapshot)
- Click **Capture Now** without starting a full recording
- Grabs: current network log + full `document.body.innerText` DOM snapshot
- Good for one-shot page captures

### Export
- **Export JSON** — downloads `bigmac-scope-{hostname}-{timestamp}.json` to your Downloads folder
- **Copy to Clipboard** — copies the full JSON payload to clipboard
- **Clear** — wipes the log for the current tab

---

## Export Format

```json
{
  "bigmac_scope": "1.0",
  "captured_at": "2026-05-09T18:44:00.000Z",
  "url": "https://claude.ai/...",
  "hostname": "claude.ai",
  "event_count": 247,
  "events": [
    { "type": "fetch:request", "data": { "url": "...", "method": "POST" }, "ts": 1234567890 },
    { "type": "fetch:response", "data": { "url": "...", "status": 200, "body": {...} }, "ts": 1234567891 },
    { "type": "ws:message", "data": { "url": "wss://...", "data": {...} }, "ts": 1234567892 },
    { "type": "click", "data": { "tag": "BUTTON", "text": "Submit", "x": 400, "y": 300 }, "ts": 1234567893 }
  ],
  "dom_snapshot": "full page text..."
}
```

### Event types captured
| Type | Description |
|------|-------------|
| `fetch:request` | Outbound fetch — URL, method, body |
| `fetch:response` | Fetch response — status, parsed body |
| `fetch:error` | Fetch threw (network error, CORS, etc.) |
| `xhr:request` | XHR open+send — URL, method, body |
| `xhr:response` | XHR load — status, response body |
| `ws:open` | WebSocket connection opened |
| `ws:send` | Client → server message |
| `ws:message` | Server → client message |
| `ws:close` | Connection closed (code + reason) |
| `ws:error` | WebSocket error |
| `click` | DOM click — element tag, id, class, text, href, x/y |
| `scope:ready` | Injection confirmed (always emitted) |

---

## Architecture

```
content/relay.js        — ISOLATED world, relays postMessage → background
content/autoscope.js    — MAIN world (injected via scripting API), hooks fetch/XHR/WS/click
background/service-worker.js — stores per-tab logs (up to 10k events each)
popup/popup.js          — controls recording state, triggers export
```

**Key design choices:**
- `autoscope.js` is injected into **MAIN world** via `chrome.scripting.executeScript` so it can patch `window.fetch`, `XMLHttpRequest`, and `WebSocket` before page scripts run
- `relay.js` in ISOLATED world bridges `postMessage` → `chrome.runtime.sendMessage` (MAIN world can't call runtime APIs directly in MV3)
- Per-tab state lives in the service worker's `Map` — clears on tab close
- Body payloads >50KB are truncated to prevent memory bloat
- `window.__BIGMAC_RECORDING__` bool is the live gate — toggled from popup without re-injection

---

## Common Use Cases

**Capture Whatnot API calls during a live show:**
1. Navigate to a Whatnot live show
2. Open popup → Start Recording
3. Interact (bid, chat, view items)
4. Stop Recording → Export JSON

**Capture claude.ai SSE/WS stream format:**
1. Navigate to claude.ai
2. Start Recording
3. Send a message
4. Stop → Export to inspect the streaming protocol

**One-shot DOM capture:**
Navigate to any page → Capture Now → Copy to Clipboard → paste into analysis

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Inject failed" in popup | Page uses strict CSP; try navigating to the page first and then opening popup |
| 0 events after recording | Make sure you clicked Start Recording *before* the network activity happened |
| Missing fetch responses | Some responses use streaming body — body may be empty in log |
| Extension not in toolbar | Click the puzzle icon → pin BigMac Scope |
| Stale code after edit | Go to `chrome://extensions` → click reload icon on BigMac Scope card |
