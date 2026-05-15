#!/usr/bin/env python3
"""
sbx_desktop.py — Get or create a BIGMAC desktop E2B sandbox with pre-baked Google auth.

Usage:
  python3 sbx_desktop.py                    # Get warm sandbox from pool or create new
  python3 sbx_desktop.py --new              # Always create fresh (skip pool)
  python3 sbx_desktop.py --kill <id>        # Kill with pre-kill backup (cookies, files, logs)
  python3 sbx_desktop.py --kill <id> --no-backup  # Kill immediately, skip backup
  python3 sbx_desktop.py --shell "cmd" --sandbox-id <id>   # Run shell cmd in sandbox
  python3 sbx_desktop.py --upload /local/file /remote/path --sandbox-id <id>
  python3 sbx_desktop.py --download /remote/path /local/path --sandbox-id <id>
  python3 sbx_desktop.py --screenshot /local/path.png --sandbox-id <id>
  python3 sbx_desktop.py --playwright "https://example.com" --sandbox-id <id>

Outputs JSON with: sandbox_id, vnc_url, status
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

POOL_JSON = Path.home() / ".openclaw/e2b-desktop-pool.json"
DESKTOP_TEMPLATE = "bigmac-desktop-v3-3-3"
BACKUP_DIR = Path.home() / ".openclaw/sandbox-backups"

# Files/dirs always worth checking in pre-kill scan
INTERESTING_PATHS = [
    "/home/user/Downloads",
    "/home/user/Documents",
    "/home/user/Desktop",
    "/home/user/screenshots",
    "/tmp",
]

# Log files to grab
LOG_PATHS = [
    "/home/user/.xsession-errors",
    "/tmp/playwright-install.log",
    "/var/log/syslog",
]


def get_e2b_api_key():
    key = os.environ.get("E2B_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(["secrets", "get", "e2b_api_key"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    sys.exit("ERROR: E2B_API_KEY not found. Set env var or add to secrets vault.")


def get_desktop_sandbox():
    """Import e2b_desktop module with install fallback."""
    try:
        from e2b_desktop import Sandbox as DesktopSandbox
        return DesktopSandbox
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "e2b-desktop", "-q"])
        from e2b_desktop import Sandbox as DesktopSandbox
        return DesktopSandbox


def _connect(sandbox_id):
    """Connect to a desktop sandbox, handling common errors."""
    DesktopSandbox = get_desktop_sandbox()
    api_key = get_e2b_api_key()
    try:
        return DesktopSandbox.connect(sandbox_id, api_key=api_key)
    except Exception:
        # Pool-managed sandboxes created by CF Worker may not be accessible
        # via e2b-desktop SDK connect(). Try generic SDK as fallback.
        try:
            from e2b import Sandbox
            return Sandbox.connect(sandbox_id, api_key=api_key)
        except Exception as e2:
            raise ConnectionError(
                f"Cannot connect to sandbox {sandbox_id} via desktop or generic SDK: {e2}"
            )


def _run_cmd(sbx, command, timeout=120):
    """Run a command in sandbox, catching exit code errors."""
    try:
        result = sbx.commands.run(command, timeout=timeout)
        return {
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "exit_code": result.exit_code,
        }
    except Exception as e:
        # CommandExitException includes stdout/stderr in some SDK versions
        err_str = str(e)
        return {
            "stdout": getattr(e, 'stdout', '') or "",
            "stderr": getattr(e, 'stderr', err_str) or err_str,
            "exit_code": getattr(e, 'exit_code', 1) or 1,
        }


def get_from_pool():
    """Try to grab a warm sandbox from the local pool JSON."""
    if not POOL_JSON.exists():
        return None
    try:
        pool = json.loads(POOL_JSON.read_text())
        sandboxes = pool.get("sandboxes", [])
        if sandboxes:
            s = sandboxes[0]
            return {
                "sandbox_id": s["sandbox_id"],
                "vnc_url": s["vnc_url"],
                "source": "pool",
            }
    except Exception as e:
        print(f"[sbx_desktop] Pool read error: {e}", file=sys.stderr)
    return None


def create_sandbox(timeout=3600):
    """Create a new desktop sandbox."""
    DesktopSandbox = get_desktop_sandbox()
    api_key = get_e2b_api_key()
    print(f"[sbx_desktop] Creating new sandbox (template={DESKTOP_TEMPLATE})...", file=sys.stderr)
    sbx = DesktopSandbox.create(template=DESKTOP_TEMPLATE, api_key=api_key, timeout=timeout)
    sandbox_id = sbx.sandbox_id
    vnc_url = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
    return {
        "sandbox_id": sandbox_id,
        "vnc_url": vnc_url,
        "source": "created",
    }


def run_shell_in_sandbox(sandbox_id, command, timeout=120):
    """Run a shell command inside an existing desktop sandbox."""
    try:
        sbx = _connect(sandbox_id)
    except ConnectionError as e:
        return {"stdout": "", "stderr": str(e), "exit_code": 1}
    return _run_cmd(sbx, command, timeout=timeout)


def upload_file(sandbox_id, local_path, remote_path):
    """Upload a local file into the sandbox."""
    sbx = _connect(sandbox_id)
    with open(local_path, "rb") as f:
        sbx.files.write(remote_path, f.read())
    return {"uploaded": local_path, "to": remote_path}


def download_file(sandbox_id, remote_path, local_path):
    """Download a file from the sandbox to local filesystem."""
    sbx = _connect(sandbox_id)
    content = sbx.files.read(remote_path)
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(content)
    return {"downloaded": remote_path, "to": local_path, "size": len(content)}


def take_screenshot(sandbox_id, local_path):
    """Take a screenshot of the desktop and download it."""
    sbx = _connect(sandbox_id)
    screenshot_bytes = sbx.screenshot()
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(screenshot_bytes)
    return {"screenshot": local_path, "size": len(screenshot_bytes)}


def run_playwright(sandbox_id, url, screenshot_path=None, timeout=60):
    """Run Playwright automation in the desktop sandbox."""
    code = f'''
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("{url}", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    print("Page title:", page.title())
    print("URL:", page.url)
    {"page.screenshot(path='/home/user/screenshot.png')" if screenshot_path else ""}
    browser.close()
print("Playwright complete")
'''
    result = run_shell_in_sandbox(sandbox_id, f'python3 -c {repr(code)}', timeout=timeout)
    if screenshot_path and result.get("exit_code") == 0:
        download_file(sandbox_id, "/home/user/screenshot.png", screenshot_path)
        result["screenshot_downloaded"] = screenshot_path
    return result


def click_element(sandbox_id, selector, timeout=30):
    """Click an element using Playwright."""
    code = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0] if browser.contexts else browser.new_page()
    page.wait_for_selector("{selector}", timeout={timeout * 1000})
    page.click("{selector}")
    print("Clicked:", "{selector}")
    browser.close()
'''
    return run_shell_in_sandbox(sandbox_id, f'python3 -c {repr(code)}', timeout=timeout)


def type_text(sandbox_id, selector, text, timeout=30):
    """Type text into an element using Playwright."""
    code = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0] if browser.contexts else browser.new_page()
    page.wait_for_selector("{selector}", timeout={timeout * 1000})
    page.locator("{selector}").fill("{text}")
    print("Typed into:", "{selector}")
    browser.close()
'''
    return run_shell_in_sandbox(sandbox_id, f'python3 -c {repr(code)}', timeout=timeout)


# ──────────────────────────────────────────────────────────────
# Pre-kill hook: save cookies, files, logs before sandbox dies
# ──────────────────────────────────────────────────────────────

def pre_kill_hook(sandbox_id):
    """
    Runs before killing a sandbox. Backs up:
      1. Chrome/Chromium login cookies (Google auth etc.)
      2. Recently modified files in user home
      3. Session logs and crash dumps
      4. Playwright traces if any
      5. Git status (uncommitted work detection)

    Saves to ~/.openclaw/sandbox-backups/{sandbox_id}_{timestamp}/
    Returns dict with backup results.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = BACKUP_DIR / f"{sandbox_id}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {"sandbox_id": sandbox_id, "backup_dir": str(out_dir), "saved": {}, "errors": []}

    try:
        sbx = _connect(sandbox_id)
    except ConnectionError as e:
        report["errors"].append(f"Cannot connect for backup: {e}")
        print(f"[pre-kill] Cannot connect to {sandbox_id}: {e}", file=sys.stderr)
        return report

    # ── 1. Export Chrome cookies ──────────────────────────────
    cookie_script = r'''python3 << 'COOKIE_EOF'
import json, sqlite3, os, shutil, tempfile

# Chrome stores cookies in an encrypted SQLite DB
# Try multiple possible locations
cookie_dbs = [
    os.path.expanduser("~/.config/google-chrome/Default/Cookies"),
    os.path.expanduser("~/.config/chromium/Default/Cookies"),
    os.path.expanduser("~/.config/google-chrome-for-testing/Default/Cookies"),
]

for db_path in cookie_dbs:
    if not os.path.exists(db_path):
        continue
    # Copy to temp to avoid lock issues
    tmp = tempfile.mktemp(suffix=".db")
    shutil.copy2(db_path, tmp)
    try:
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, value, host_key as domain, path, expires_utc, is_secure, is_httponly "
            "FROM cookies WHERE host_key LIKE '%.google.com' OR host_key LIKE '%.youtube.com' "
            "OR host_key LIKE '%.googleapis.com'"
        ).fetchall()
        cookies = [dict(r) for r in rows]
        conn.close()
        os.unlink(tmp)
        if cookies:
            print(json.dumps({"source": db_path, "count": len(cookies), "cookies": cookies}))
            break
    except Exception as e:
        os.unlink(tmp)
        continue
else:
    print(json.dumps({"source": None, "count": 0, "cookies": []}))
COOKIE_EOF'''

    r = _run_cmd(sbx, cookie_script, timeout=15)
    try:
        cookie_data = json.loads(r["stdout"].strip().split("\n")[-1])
        if cookie_data.get("count", 0) > 0:
            cookie_file = out_dir / "chrome_cookies.json"
            cookie_file.write_text(json.dumps(cookie_data, indent=2))
            report["saved"]["cookies"] = {
                "file": str(cookie_file),
                "count": cookie_data["count"],
                "source": cookie_data["source"],
            }
            print(f"[pre-kill] Saved {cookie_data['count']} cookies", file=sys.stderr)
    except Exception as e:
        report["errors"].append(f"Cookie export: {e}")

    # ── 2. Find recently modified files ───────────────────────
    # Files modified in the last 4 hours (likely user-generated, not template)
    find_cmd = (
        "find /home/user -maxdepth 4 -type f -mmin -240 "
        "-not -path '*/.*cache*' -not -path '*/.local/share/Trash/*' "
        "-not -path '*/node_modules/*' -not -path '*/__pycache__/*' "
        "-not -name '*.pyc' -not -name '.DS_Store' "
        "2>/dev/null | head -100"
    )
    r = _run_cmd(sbx, find_cmd, timeout=10)
    modified_files = [f for f in r["stdout"].strip().split("\n") if f]

    if modified_files:
        manifest = out_dir / "modified_files.txt"
        manifest.write_text("\n".join(modified_files))
        report["saved"]["modified_files"] = {
            "manifest": str(manifest),
            "count": len(modified_files),
        }

        # Auto-download small important files (< 1MB each, max 20)
        downloaded = []
        download_dir = out_dir / "files"
        download_dir.mkdir(exist_ok=True)
        for remote_path in modified_files[:20]:
            # Skip huge/binary files by checking size first
            size_r = _run_cmd(sbx, f"stat -c %s '{remote_path}' 2>/dev/null || echo 0", timeout=5)
            try:
                size = int(size_r["stdout"].strip())
            except (ValueError, AttributeError):
                continue
            if size > 1_048_576 or size == 0:  # Skip > 1MB or empty
                continue
            try:
                local_name = remote_path.replace("/", "_").lstrip("_")
                local_path = download_dir / local_name
                content = sbx.files.read(remote_path)
                local_path.write_bytes(content)
                downloaded.append({"remote": remote_path, "local": str(local_path), "size": size})
            except Exception:
                pass

        if downloaded:
            report["saved"]["downloaded_files"] = downloaded
            print(f"[pre-kill] Downloaded {len(downloaded)} files", file=sys.stderr)

    # ── 3. Grab logs ──────────────────────────────────────────
    saved_logs = []
    for log_path in LOG_PATHS:
        r = _run_cmd(sbx, f"tail -c 65536 '{log_path}' 2>/dev/null", timeout=5)
        if r["stdout"].strip():
            log_name = Path(log_path).name
            log_file = out_dir / f"log_{log_name}"
            log_file.write_text(r["stdout"])
            saved_logs.append({"source": log_path, "saved": str(log_file)})

    if saved_logs:
        report["saved"]["logs"] = saved_logs
        print(f"[pre-kill] Saved {len(saved_logs)} log files", file=sys.stderr)

    # ── 4. Check for Playwright traces ────────────────────────
    r = _run_cmd(sbx, "find /home/user -name '*.zip' -path '*/traces/*' 2>/dev/null | head -5", timeout=5)
    trace_files = [f for f in r["stdout"].strip().split("\n") if f]
    if trace_files:
        trace_dir = out_dir / "traces"
        trace_dir.mkdir(exist_ok=True)
        for tf in trace_files:
            try:
                local_name = Path(tf).name
                content = sbx.files.read(tf)
                (trace_dir / local_name).write_bytes(content)
            except Exception:
                pass
        report["saved"]["playwright_traces"] = len(trace_files)

    # ── 5. Git status (detect uncommitted work) ───────────────
    r = _run_cmd(sbx, "cd /home/user && for d in */; do (cd \"$d\" && git status --short 2>/dev/null | head -5); done", timeout=10)
    if r["stdout"].strip():
        git_status = out_dir / "git_uncommitted.txt"
        git_status.write_text(r["stdout"])
        report["saved"]["git_uncommitted"] = str(git_status)
        print(f"[pre-kill] WARNING: Uncommitted git changes detected", file=sys.stderr)

    # Write summary
    summary_file = out_dir / "backup_summary.json"
    summary_file.write_text(json.dumps(report, indent=2))
    print(f"[pre-kill] Backup complete → {out_dir}", file=sys.stderr)

    return report


def kill_sandbox(sandbox_id, backup=True):
    """Kill a sandbox with pre-kill backup by default."""
    results = {}

    if backup:
        print(f"[sbx_desktop] Running pre-kill backup for {sandbox_id}...", file=sys.stderr)
        results["backup"] = pre_kill_hook(sandbox_id)

    try:
        r = subprocess.run(
            ["e2b", "sandbox", "kill", sandbox_id],
            capture_output=True, text=True, timeout=30,
        )
        results["killed"] = sandbox_id
        results["success"] = r.returncode == 0
        if not results["success"]:
            results["kill_stderr"] = r.stderr.strip()
    except Exception as e:
        results["killed"] = sandbox_id
        results["success"] = False
        results["error"] = str(e)

    return results


def poll_vnc_ready(vnc_url, max_attempts=10, interval=3):
    """Poll VNC URL until it's ready (up to 30s)."""
    import urllib.request
    for attempt in range(max_attempts):
        try:
            urllib.request.urlopen(vnc_url, timeout=5)
            return {"ready": True, "attempts": attempt + 1}
        except Exception:
            time.sleep(interval)
    return {"ready": False, "attempts": max_attempts}


def main():
    parser = argparse.ArgumentParser(description="Get/create BIGMAC desktop E2B sandbox")
    parser.add_argument("--new", action="store_true", help="Create fresh sandbox (skip pool)")
    parser.add_argument("--kill", metavar="SANDBOX_ID", help="Kill a sandbox (runs pre-kill backup first)")
    parser.add_argument("--no-backup", action="store_true", help="Skip pre-kill backup on --kill")
    parser.add_argument("--shell", metavar="CMD", help="Run shell command in sandbox")
    parser.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"), help="Upload file to sandbox")
    parser.add_argument("--download", nargs=2, metavar=("REMOTE", "LOCAL"), help="Download file from sandbox")
    parser.add_argument("--screenshot", metavar="LOCAL_PATH", help="Take desktop screenshot and save locally")
    parser.add_argument("--playwright", metavar="URL", help="Run Playwright against URL")
    parser.add_argument("--click", metavar="SELECTOR", help="Click element by CSS selector")
    parser.add_argument("--type", nargs=2, metavar=("SELECTOR", "TEXT"), help="Type text into element")
    parser.add_argument("--sandbox-id", help="Target sandbox ID (for operations)")
    parser.add_argument("--timeout", type=int, default=3600, help="Sandbox lifetime in seconds")
    parser.add_argument("--poll", action="store_true", help="Poll VNC until ready (use with get)")
    args = parser.parse_args()

    if args.kill:
        result = kill_sandbox(args.kill, backup=not args.no_backup)
        print(json.dumps(result, indent=2))
        return

    if args.shell:
        if not args.sandbox_id:
            parser.error("--shell requires --sandbox-id")
        result = run_shell_in_sandbox(args.sandbox_id, args.shell, timeout=args.timeout)
        print(json.dumps(result, indent=2))
        return

    if args.upload:
        if not args.sandbox_id:
            parser.error("--upload requires --sandbox-id")
        result = upload_file(args.sandbox_id, args.upload[0], args.upload[1])
        print(json.dumps(result, indent=2))
        return

    if args.download:
        if not args.sandbox_id:
            parser.error("--download requires --sandbox-id")
        result = download_file(args.sandbox_id, args.download[0], args.download[1])
        print(json.dumps(result, indent=2))
        return

    if args.screenshot:
        if not args.sandbox_id:
            parser.error("--screenshot requires --sandbox-id")
        result = take_screenshot(args.sandbox_id, args.screenshot)
        print(json.dumps(result, indent=2))
        return

    if args.playwright:
        if not args.sandbox_id:
            parser.error("--playwright requires --sandbox-id")
        result = run_playwright(args.sandbox_id, args.playwright, timeout=args.timeout)
        print(json.dumps(result, indent=2))
        return

    if args.click:
        if not args.sandbox_id:
            parser.error("--click requires --sandbox-id")
        result = click_element(args.sandbox_id, args.click)
        print(json.dumps(result, indent=2))
        return

    if args.type:
        if not args.sandbox_id:
            parser.error("--type requires --sandbox-id")
        result = type_text(args.sandbox_id, args.type[0], args.type[1])
        print(json.dumps(result, indent=2))
        return

    # Get or create desktop sandbox
    result = None
    if not args.new:
        result = get_from_pool()
        if result:
            print(f"[sbx_desktop] Got warm sandbox from pool: {result['sandbox_id']}", file=sys.stderr)

    if not result:
        result = create_sandbox(timeout=args.timeout)

    if args.poll:
        poll_result = poll_vnc_ready(result["vnc_url"])
        result["vnc_ready"] = poll_result["ready"]
        result["poll_attempts"] = poll_result["attempts"]

    print(json.dumps(result, indent=2))
    print(f"\n[sbx_desktop] VNC URL: {result['vnc_url']}", file=sys.stderr)


if __name__ == "__main__":
    main()
