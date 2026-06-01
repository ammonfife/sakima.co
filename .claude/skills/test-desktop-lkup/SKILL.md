---
name: test-desktop-lkup
description: Test the lkup.info Mac desktop scanner (Client A — desktop_scanner.py) end-to-end against LIVE data by emulating the HID barcode scanner, watching the scanner logs, and verifying the result in Supabase. Use when the user says "/test-desktop-lkup", "test the desktop scanner", "emulate the keyboard scanner", "scan a coin on the desktop app", or wants to exercise the scan→enrich→price pipeline through the real dealer-station client (not the web /scan EF directly). Verified working 2026-05-31.
---

<!-- READ ENTIRE FILE — load-bearing ports, schemas, and the two injection methods are all verified-live. -->

# /test-desktop-lkup — Drive the Mac desktop scanner end-to-end on live data

The Mac desktop scanner (`desktop/unified/interfaces/gui/desktop_scanner.py`, ~19.8K lines)
is **Client A** — the dealer-station GUI with USB/BT HID scanner, multi-cam, label printer.
It is NOT replaceable by the web app. This skill drives it the way a real USB/BT barcode
scanner does, then verifies the write reached Supabase.

**Key architectural fact (verified 2026-05-31):** the desktop scanner is a *thin client* over
the Supabase scan Edge Function. Every barcode path converges on `_process_barcode` →
**`[2] POST /scan → Supabase EF`**. So a scan through the desktop scanner exercises the SAME
server-side enrichment + pricing the web `/scan` and iOS app use. Fixing the EF fixes all three.

Pipeline: `barcode → _process_barcode → POST {EDGE_FN_BASE}/scan → certs row → enqueue-enrichment → grader_data → pricing_consensus (trigger) → coin_current`.

---

## Repo + paths (all under `~/github/ammonfife/lkup.info/desktop/unified/`)

| What | Path / value |
|---|---|
| Scanner GUI | `interfaces/gui/desktop_scanner.py` |
| Launcher (sets API keys, runs GUI) | `launch_scanner.sh` (runs `python3 interfaces/gui/desktop_scanner.py`, **no stdout redirect** — capture it yourself) |
| Keyboard/barcode daemon | `services/keyboard_listener_service.py` (separate process) |
| SUPER_LOG (forensic, rotated hourly) | `desktop/unified/logs/SUPER_LOG.txt` |
| Cert broadcast log | `/Users/benfife/unified-scanner-logs/cert_broadcasts.log` |
| Python interpreter | `/Users/benfife/.pyenv/versions/3.13.7/bin/python3` (has `websockets`) |
| Scan EF | `POST https://vsotvatntzlrzrhemayh.supabase.co/functions/v1/scan` `{barcode}` |
| DB | `psql "$LKUP_DB_URL"` |

### Ports (CRITICAL — verified live, easy to get wrong)
The `keyboard_listener_service` daemon (one process) listens on **TWO** ports:
- **:5556** — cert-scraper bridge (forwards `COIN_CERT_DATA` from the browser extension). **NOT the barcode port.**
- **:5557** — keyboard/barcode service. The scanner connects here (`ws://127.0.0.1:5557`) and receives `barcode_scanned` messages. **This is the inject target.**

Injecting a barcode to :5556 silently does nothing useful — the scanner isn't listening there for barcodes. Always use **:5557**.

---

## Step 1 — Ensure the scanner is running (launch fresh, capture stdout)

```bash
cd ~/github/ammonfife/lkup.info/desktop/unified
ps aux | grep -E "desktop_scanner.py" | grep -v grep   # already running?
```

If not running (or the user closed it for a fresh test), launch with stdout captured to a durable log
(the launcher does NOT redirect — the GUI's `write_output` goes to a Tk widget you can't tail, but stdout you can):

```bash
RUNLOG=~/clawd/logs/scanner-runtime-$(date +%Y%m%d-%H%M%S).log
echo "$RUNLOG" > /tmp/.scanner_runlog_path
nohup bash launch_scanner.sh > "$RUNLOG" 2>&1 &
sleep 20   # heavy imports: OpenCV, Tk, E2B pool reconnect
grep -E "DesktopScannerController initialized|keyboard listener|5557" "$RUNLOG" | tail -3
```

Healthy startup shows: `CoinScanner initialized`, `E2B sandbox pool`, `✅ Connected to keyboard listener service`,
`Attempting to connect to keyboard service at ws://127.0.0.1:5557`, `DesktopScannerController initialized`.

> Note: the GUI banner "SCANNER STOPPED — COLD START to begin" refers to the **camera** detection loop only.
> The USB/BT barcode path works WITHOUT clicking START. (Confirmed by Ben + by reading `_on_usb_barcode_scan` —
> it has no started-state gate, only a `barcode_input_disabled` hard gate.)

---

## Step 2 — Inject a barcode (TWO methods; prefer the webhook)

### Method A (PREFERRED) — webhook injection to :5557

Clean, reliable, no window focus required. Send `inject_barcode`; the daemon re-broadcasts it as
`barcode_scanned` to the scanner → `_process_bluetooth_barcode` → full pipeline.

```bash
RUNLOG=$(cat /tmp/.scanner_runlog_path)
echo "$(wc -l < "$RUNLOG")" > /tmp/.runlog_base
BARCODE="71394069008689129049"   # known silver NGC -> NGC-8689129049, 2026 ASE MS69
/Users/benfife/.pyenv/versions/3.13.7/bin/python3 - "$BARCODE" <<'PY'
import asyncio, json, sys, websockets
bc=sys.argv[1]
async def inject():
    async with websockets.connect("ws://127.0.0.1:5557") as ws:
        await ws.send(json.dumps({"type":"inject_barcode","barcode":bc}))
        for _ in range(4):
            m=await asyncio.wait_for(ws.recv(), timeout=4)
            print("resp:", m[:120])
            if json.loads(m).get("type")=="ACK": break
asyncio.run(inject())
PY
sleep 8
tail -n +$(( $(cat /tmp/.runlog_base)+1 )) "$RUNLOG" | grep -vE "heartbeat|Message type: heartbeat|pool-rotate"
```

Success looks like: `barcode_scanned` → `📱 Bluetooth scanner: <barcode>` → `[1] coin_scanner.scan` →
`✅ Scan complete` → `[2] POST /scan → Supabase EF` → `✓ EF returned: <desc>` → `📊 coin_current: consensus=$…`.

### Method B (FALLBACK) — emulate the HID keyboard via cliclick

A USB/BT scanner *is* a keyboard. The scanner's hidden `barcode_entry` Tk widget (`<Return>` →
`_on_usb_barcode_scan`) holds keyboard focus. Two gotchas that WILL bite:
1. **The window must be the macOS *key* window** — `frontmost`-app is not enough for synthetic keystrokes.
   Click the **title bar** first to make it key (clicking the body may trigger a button).
2. **Do it in ONE uninterrupted cliclick chain** — any gap (a screenshot, another tool call) lets focus
   drift and the keystrokes/Return go nowhere.

```bash
# Get the window bounds via Quartz (Tk doesn't expose its title to System Events):
/Users/benfife/.pyenv/versions/3.13.7/bin/python3 - <<'PY'
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID
import subprocess
pid=int(subprocess.check_output(["pgrep","-f","desktop_scanner.py"]).split()[0])
for w in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID):
    if w.get('kCGWindowOwnerPID')==pid:
        b=w.get('kCGWindowBounds')
        if b and b['Width']>200 and b['Height']>200:
            print(f"TITLEBAR {int(b['X']+b['Width']/2)},{int(b['Y']+12)}"); break
PY
# Then (TBX,TBY from above), one chain — click-to-key, type, Return:
cliclick c:TBX,TBY w:400 t:"71394069008689129049" w:150 kp:return
```

To verify the digits landed before pressing Return, you can screenshot the window with
`screencapture -x -l <windowid>` — but then re-key (`cliclick c:TBX,TBY w:400 kp:return`) in a fresh
single chain, because the screenshot/capture may have stolen key focus.

---

## Step 3 — Watch the logs

```bash
RUNLOG=$(cat /tmp/.scanner_runlog_path)
# live tail (filter the heartbeat + pool-rotate noise):
tail -f "$RUNLOG" | grep --line-buffered -vE "heartbeat|Message type: heartbeat|pool-rotate"
# cert broadcasts (label printer / extension fan-out):
tail -20 /Users/benfife/unified-scanner-logs/cert_broadcasts.log
```

---

## Step 4 — Verify the write reached Supabase (close the loop)

HTTP 200 / "EF returned" is NOT proof — read the rows back. `enrichment_attempted_at` and
`grader_data.enriched_at` should be freshly stamped (within seconds). Column is `superseded_at` (NOT `superseded_by`).

```bash
CERT="NGC-8689129049"
psql "$LKUP_DB_URL" <<SQL
SELECT id, grade, left(description,24) AS descr, enrichment_attempted_at::time
  FROM public.certs WHERE id='$CERT';
SELECT source, (enriched_at AT TIME ZONE 'MST')::time AS enriched_mst, (composition IS NOT NULL) AS has_comp
  FROM public.grader_data WHERE cert_id='$CERT' ORDER BY enriched_at DESC NULLS LAST LIMIT 2;
SELECT grade, melt_value, ngc_guide, pcgs_guide, ebay_median, consensus_price,
       (calculated_at AT TIME ZONE 'MST')::time AS calc_mst
  FROM public.pricing_consensus WHERE cert_id='$CERT' AND superseded_at IS NULL;
SQL
```

What "pass" looks like (verified 2026-05-31 for NGC-8689129049):
- `certs`: grade 69, "2026 Eagle S$1 MS", `enrichment_attempted_at` = now.
- `grader_data`: `enriched_at` freshly stamped (this is the #10146 trigger working; NGC rows have `has_comp=f` — NGC API returns no MetalContent, that's expected, not a bug).
- `pricing_consensus`: `melt_value=75` (silver, from `spot_prices_latest` — #10148), `ngc_guide=175`, `ebay_median≈112`, `consensus_price=110`, `calc_mst` = now.

---

## Cold-start variant (true new-cert test)

Methods above re-enrich an existing cert. For a genuine INSERT-path test, Ben has authorized
backup → delete → resubmit (scoped permission — confirm it's still in scope before deleting):
1. Backup the cert + all child rows to `archive.*` (FKs: `grader_data`, `pricing_consensus`, `coin_xref`,
   `barcode_cert_xref`, `auction_comps`, `cert_photos`, `inventory`, `draft_listings`, etc. — 22 tables ref `certs.id`; only `cert_xref`/`cert_coin_id_overrides` are `ON DELETE CASCADE`).
2. Delete child rows then the cert.
3. Re-inject the barcode (Step 2) → confirm the cert is recreated from scratch with correct enriched_at/melt/pricing.

Alternatively (no delete): find an eBay/Whatnot comp cert NOT yet in `certs` and inject its barcode — natural cold-start.

---

## Known scanner bugs surfaced by this test (file/fix, don't ignore)

- **#10195** — E2B pool-rotate fails: `SandboxBase.__init__() got an unexpected keyword argument 'template'`.
  All 3 rotation spawns fail, keeps 1 stale sandbox. E2B SDK API changed (`template=` removed). Cert pages still
  open via the reconnected sandbox, so non-blocking, but rotation is dead.
- **#10196** — Realtime council subscription fails: `This feature isn't available in the sync client. You can use
  the realtime feature in the async client only.` Scanner uses the **sync** Supabase client for Realtime; it falls
  back to poll (works), but the Realtime "Accurate mode" path is dead until switched to the async client.

Per error-handling discipline: any NEW bug surfaced by a run gets a `todo add` BEFORE you move on.

---

## Anti-patterns

- **Don't inject to :5556** for barcodes — that's the cert bridge. Use **:5557**.
- **Don't treat "EF returned" as done** — read the Supabase rows (HTTP 200 ≠ working).
- **Don't split the cliclick click/type/Return across tool calls** — focus drifts; the keystrokes vanish.
- **Don't click START expecting it to enable barcode input** — START is camera-only; the USB/BT path is always live.
- **Don't fabricate a barcode** — use a real known cert barcode or a real uncaptured comp. No synthetic data to prod.
