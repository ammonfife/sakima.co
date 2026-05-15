# test-with-e2b — Load and Test Chrome Extensions in E2B

Load a local Chrome extension into an E2B desktop sandbox, navigate to test URLs, and capture screenshot evidence.

**Requires:** `bigmac-desktop-v3-3-3` (has Chrome + Playwright + VNC)

---

## Quick Pattern

```python
import subprocess, os, json
from pathlib import Path

# 1. Get API key
api_key = os.environ.get("E2B_API_KEY") or subprocess.run(
    ["bigmac-secrets", "get", "e2b_api_key"],
    capture_output=True, text=True
).stdout.strip().strip('"')

# 2. Acquire sandbox (pool first, then fresh)
result = json.loads(subprocess.check_output([
    "python3", "/Users/benfife/.claude/skills/e2b-bigmac/acquire.py",
    "--type", "desktop"
]))
sandbox_id = result["sandbox_id"]
print(f"VNC: {result.get('vnc_url')}")

# 3. Connect and upload extension
from e2b_desktop import Sandbox
sbx = Sandbox.connect(sandbox_id, api_key=api_key)

ext_dir = Path("/local/path/to/extension")
sbx.commands.run("mkdir -p /home/user/ext")
for f in ext_dir.rglob("*"):
    if f.is_file():
        rel = str(f.relative_to(ext_dir))
        sbx.files.write(f"/home/user/ext/{rel}", f.read_bytes())

# 4. Launch Chrome with extension loaded
test_url = "https://example.com"
sbx.commands.run(
    f"DISPLAY=:99 google-chrome --no-sandbox --no-first-run "
    f"--no-default-browser-check --load-extension=/home/user/ext "
    f"'{test_url}' &",
    timeout=10
)

import time; time.sleep(3)  # let Chrome open

# 5. Take screenshot as evidence
screenshot = sbx.screenshot()
Path("ext-test-screenshot.png").write_bytes(screenshot)
print("PASS: screenshot saved to ext-test-screenshot.png")
```

---

## Full Workflow Script

Save as a local `.py` and run:

```python
#!/usr/bin/env python3
"""
test-chrome-extension.py — Load Chrome extension in E2B and test against URLs

Usage:
    python3 test-chrome-extension.py /path/to/extension https://testurl.com
    python3 test-chrome-extension.py /path/to/extension https://url1.com https://url2.com
"""
import sys, os, json, subprocess, time
from pathlib import Path

def get_api_key():
    key = os.environ.get("E2B_API_KEY", "")
    if key:
        return key
    r = subprocess.run(["bigmac-secrets", "get", "e2b_api_key"],
                       capture_output=True, text=True, timeout=5)
    return r.stdout.strip().strip('"') if r.returncode == 0 else None

def upload_extension(sbx, ext_dir: Path):
    """Upload all extension files, preserving directory structure."""
    sbx.commands.run("rm -rf /home/user/ext && mkdir -p /home/user/ext")
    for f in sorted(ext_dir.rglob("*")):
        if f.is_file() and ".git" not in f.parts:
            rel = str(f.relative_to(ext_dir))
            sbx.files.write(f"/home/user/ext/{rel}", f.read_bytes())
    print(f"Uploaded {sum(1 for f in ext_dir.rglob('*') if f.is_file())} files", file=sys.stderr)

def main(ext_path: str, test_urls: list):
    from e2b_desktop import Sandbox

    api_key = get_api_key()
    if not api_key:
        sys.exit("ERROR: E2B_API_KEY not found")

    # Acquire sandbox from pool
    result = json.loads(subprocess.check_output([
        "python3", "/Users/benfife/.claude/skills/e2b-bigmac/acquire.py",
        "--type", "desktop"
    ]))
    sandbox_id = result["sandbox_id"]
    print(f"Sandbox: {sandbox_id}", file=sys.stderr)
    print(f"VNC: {result.get('vnc_url', 'N/A')}", file=sys.stderr)

    sbx = Sandbox.connect(sandbox_id, api_key=api_key)

    ext_dir = Path(ext_path)
    upload_extension(sbx, ext_dir)

    results = []
    for url in test_urls:
        print(f"Testing: {url}", file=sys.stderr)

        # Kill any existing Chrome
        sbx.commands.run("pkill -f chrome 2>/dev/null || true", timeout=5)
        time.sleep(1)

        # Launch Chrome with extension
        sbx.commands.run(
            f"DISPLAY=:99 google-chrome --no-sandbox --no-first-run "
            f"--no-default-browser-check --disable-extensions-except=/home/user/ext "
            f"--load-extension=/home/user/ext '{url}' &",
            timeout=10
        )
        time.sleep(4)  # wait for page load

        # Screenshot
        screenshot = sbx.screenshot()
        fname = f"screenshot-{url.replace('https://','').replace('/','_')[:40]}.png"
        Path(fname).write_bytes(screenshot)

        results.append({"url": url, "screenshot": fname, "status": "captured"})
        print(f"  Screenshot: {fname}", file=sys.stderr)

    # Print results
    print(json.dumps({"pass": True, "results": results}, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: test-chrome-extension.py <ext_dir> <url> [url2 ...]")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2:])
```

---

## Key Notes

- **Only desktop sandboxes** have Chrome + DISPLAY. Never use code interpreter for this.
- **`--disable-extensions-except` + `--load-extension`** — both flags required for MV3 extensions.
- **DISPLAY=:99** — Xvfb is on :99 in all bigmac-desktop images.
- **Extension upload** uses `sbx.files.write()` directly — no base64 workaround needed in e2b_desktop SDK.
- **Screenshot timing** — wait 3–5s after Chrome launch before screenshotting. Complex pages need more.
- **Bump manifest.json version** before every test run (per HARD RULE in MEMORY.md) — Chrome caches extension JS by version.

## Template Names

| Template | Use |
|---|---|
| `bigmac-desktop-v3-3-3` | Desktop with Playwright/Chrome/VNC/Google auth cookies |
| `bigmac-code-v2-9-3` | Fast code interpreter (NO browser, NO Chrome) |

## Verification Pattern

```python
# After Chrome opens, check extension is loaded:
ext_check = sbx.commands.run(
    "DISPLAY=:99 google-chrome --no-sandbox --no-first-run "
    "--load-extension=/home/user/ext --dump-dom "
    "chrome://extensions/ 2>&1 | grep -i 'extension' | head -5",
    timeout=10
)
print(ext_check.stdout)
```
