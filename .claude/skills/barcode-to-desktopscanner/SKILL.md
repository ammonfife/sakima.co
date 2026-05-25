---
name: barcode-to-desktopscanner
description: Inject barcodes into the running desktop scanner via WebSocket. Emulates a Bluetooth/USB barcode scanner. Use when testing the scan→enrich→price→print pipeline without physical hardware.
---

# /barcode-to-desktopscanner — Inject Barcodes Into Desktop Scanner

> [!IMPORTANT]
> **Local Mac only.** The desktop scanner runs on Ben's Mac with keyboard_listener_service on `:5557` and cert_scraper_bridge on `:5556`. This skill requires WebSocket access to `localhost:5557`.

## When to Use

- Testing the scan → enrichment → pricing → label print pipeline
- Verifying autoprint behavior after code changes
- Injecting known certs for regression testing
- Emulating Bluetooth/USB barcode scanner input without hardware

## Architecture

```
inject_barcode → :5557 (keyboard_listener_service)
    → broadcasts barcode_scanned to scanner GUI
    → scanner._process_bluetooth_barcode(barcode)
    → scanner._process_barcode(barcode)
        → POST /scan to Supabase EF
        → coin_current lookup
        → COIN_UPDATE → :5556 (cert_scraper_bridge)
            → label printer auto-prints (if enabled)
```

**Ports:**
- `:5557` — keyboard_listener_service (accepts `inject_barcode`, broadcasts `barcode_scanned`)
- `:5556` — cert_scraper_bridge (fan-out hub: label printer, extension, scanner client)

## Step 1 — Check Scanner Is Running

```bash
ps aux | grep desktop_scanner | grep -v grep
# Should show: python3 .../desktop_scanner.py
# If not running, launch it:
# PYTHONPATH="desktop/unified:desktop/unified/interfaces/gui" python3 desktop/unified/interfaces/gui/desktop_scanner.py --skip-deps-check &
```

Also verify the keyboard listener service:
```bash
lsof -i :5557 2>/dev/null | grep LISTEN
# Should show python3 listening
```

## Step 2 — Inject Barcode

### Method A: Inline Python (preferred — no temp files)

```bash
/Users/benfife/.pyenv/versions/3.13.7/bin/python3 -c "
import asyncio, json, websockets, sys
async def inject(b):
    async with websockets.connect('ws://localhost:5557', open_timeout=5) as ws:
        await asyncio.wait_for(ws.recv(), timeout=3)  # welcome
        await ws.send(json.dumps({'type': 'inject_barcode', 'barcode': b}))
        ack = await asyncio.wait_for(ws.recv(), timeout=3)
        print(f'Injected {b} → {ack}')
asyncio.run(inject('$BARCODE'))
"
```

Replace `$BARCODE` with the actual barcode string. Examples:

| Barcode | Grader | Coin | Price Guide |
|---------|--------|------|-------------|
| `20261776` | PCGS | 1973 Quarter MS66 | $35 |
| `47797246` | PCGS | 1922 Gold Dollar MS65 | $2,350 |
| `50692447` | PCGS | 1976-S Silver Dollar MS66 | $36 |
| `8687966087` | NGC | (varies) | varies |

### Method B: Multiple barcodes (batch test)

```bash
for CERT in 20261776 47797246 50692447; do
  /Users/benfife/.pyenv/versions/3.13.7/bin/python3 -c "
import asyncio, json, websockets
async def inject(b):
    async with websockets.connect('ws://localhost:5557', open_timeout=5) as ws:
        await asyncio.wait_for(ws.recv(), timeout=3)
        await ws.send(json.dumps({'type': 'inject_barcode', 'barcode': b}))
        ack = await asyncio.wait_for(ws.recv(), timeout=3)
        print(f'Injected {b} → {ack}')
asyncio.run(inject('$CERT'))
  "
  sleep 5  # give scanner time to process each scan
done
```

### Method C: Direct bridge injection (bypasses scan flow — prints only)

Sends `COIN_UPDATE` directly to the label printer via `:5556`. Does NOT trigger the scan EF or enrichment — just prints a label with the data you provide.

```bash
/Users/benfife/.pyenv/versions/3.13.7/bin/python3 -c "
import asyncio, json, websockets
async def send():
    async with websockets.connect('ws://localhost:5556', open_timeout=5) as ws:
        await ws.send(json.dumps({
            'type': 'COIN_UPDATE',
            'data': {
                'service': 'PCGS', 'cert': '20261776',
                'description': '1973 25C', 'grade': 'MS66',
                'priceGuide': '35', 'priceOverride': 35,
                'priceConsensus': 35,
            },
            'labelPrintingEnabled': True,
            'manualPrint': False,
        }))
        ack = await asyncio.wait_for(ws.recv(), timeout=3)
        print(f'Sent → {ack}')
asyncio.run(send())
"
```

## Step 3 — Verify Results

### Scanner log (stdout)
```bash
tail -30 ~/.claude/jobs/*/scanner.log 2>/dev/null || echo "No scanner log — check scanner process stdout"
```

Look for:
- `📡 BLUETOOTH SCANNER: Received barcode scan` — barcode arrived
- `✓ EF returned:` — scan EF processed
- `📊 coin_current:` — pricing resolved
- `🏷️ Label:` — label data formatted
- `🖨️  Auto-print: sent to label printer (print=ON)` — label sent to printer

### Supabase verification
```bash
psql "$LKUP_DB_URL" -c "
  SELECT c.id, c.grade, substring(c.description,1,40) as desc,
         c.price_guide, pc.consensus_price, pc.signal_max
  FROM certs c
  LEFT JOIN pricing_consensus pc ON c.id = pc.cert_id
  WHERE c.id = 'PCGS-$CERT';"
```

### EF invocation log
```bash
# Recent scan EF invocations (requires Supabase CLI or dashboard)
psql "$LKUP_DB_URL" -t -A -c "
  SELECT cert_number, service, source, created_at
  FROM raw.scan_events
  WHERE created_at > now() - interval '5 minutes'
  ORDER BY created_at DESC LIMIT 5;"
```

## Barcode Formats Reference

| Grader | Digits | Example | Cert Extraction |
|--------|--------|---------|----------------|
| PCGS | 8 (cert only) | `20261776` | whole string = cert |
| PCGS | 16 | `0038200026177601` | last 8 digits |
| NGC | 10 | `8687966087` | whole string = cert |
| NGC | 20 | `00724008500265xxxx` | positions [0:6] = coin_id |
| CAC | 24 | varies | positions [6:18] = cert |
| ANACS | 20 | varies | [0:6]=pcgs_num [6:8]=grade [8:16]=cert |
| ICG | 18 | varies | last 10 digits |
| SEGS | 20 | varies | last 8 digits |
| URL QR | varies | `https://gongbo.net/...` | entire string is URL |

## Troubleshooting

**"Connection refused" on :5557**
- keyboard_listener_service not running. Check: `ps aux | grep keyboard_listener`
- It auto-starts with CoinScanner.app or `launch_production.sh`

**Barcode injected but scanner doesn't process**
- Scanner might not be connected to :5557. Check scanner log for "Connected to keyboard listener service"
- Kill and restart scanner after keyboard_listener_service restart

**Label not printing**
- Check autoprint toggle: scanner log should show "print=ON" not "print=OFF"
- Check label printer process: `ps aux | grep coin_label_printer`
- Check :5556 connections: `lsof -i :5556`

**"duplicate barcode" skip**
- Scanner deduplicates within 2s window. Wait 3s between same-barcode injections.
