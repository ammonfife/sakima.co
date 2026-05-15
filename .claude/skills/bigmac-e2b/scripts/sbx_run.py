#!/usr/bin/env python3
"""
sbx_run.py — Execute code or shell commands in an E2B code interpreter sandbox.

Usage:
  python3 sbx_run.py --code "import sys; print(sys.version)"
  python3 sbx_run.py --shell "pip install requests && python3 -c 'import requests; print(requests.__version__)'"
  python3 sbx_run.py --file /path/to/script.py
  python3 sbx_run.py --code "..." --sandbox-id <existing_id>  # reuse existing sandbox
  python3 sbx_run.py --code "..." --keep  # keep sandbox alive after run (prints sandbox_id)
  python3 sbx_run.py --timeout 60 --code "..."  # custom timeout (default: 300s)

Browser automation (installs Playwright chromium on first use):
  python3 sbx_run.py --playwright "https://example.com" --screenshot /tmp/out.png
  python3 sbx_run.py --selenium "https://example.com" --screenshot /tmp/out.png

Note: E2B code interpreter runs in an async event loop.
  - Playwright: use async API (async_playwright), NOT sync API
  - Shell commands: use --shell flag (wraps in subprocess)
"""

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BACKUP_DIR = Path.home() / ".openclaw/sandbox-backups"


def get_e2b_api_key():
    key = os.environ.get("E2B_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(
            ["secrets", "get", "e2b_api_key"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    sys.exit("ERROR: E2B_API_KEY not found. Set env var or add to secrets vault.")


def _get_sandbox_class():
    try:
        from e2b_code_interpreter import Sandbox
        return Sandbox
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "e2b-code-interpreter", "-q"])
        from e2b_code_interpreter import Sandbox
        return Sandbox


def pre_kill_hook(sbx):
    """
    Pre-kill hook for code interpreter sandboxes.
    Checks for output files, downloaded data, logs before kill.
    Lighter than desktop version (no cookies/VNC to save).

    Returns dict with backup results.
    """
    sandbox_id = sbx.sandbox_id
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = BACKUP_DIR / f"code_{sandbox_id}_{ts}"

    report = {"sandbox_id": sandbox_id, "backup_dir": str(out_dir), "saved": {}, "errors": []}

    try:
        # Check for user-created files
        result = sbx.run_code("""
import os, json

files = []
for root, dirs, filenames in os.walk('/home/user'):
    # Skip cache/venv/node_modules
    dirs[:] = [d for d in dirs if d not in ('.cache', '.local', '.npm', '.playwright', 'node_modules', '__pycache__', '.venv', 'venv', '.config', '.nvm')]
    for fn in filenames:
        fp = os.path.join(root, fn)
        try:
            st = os.stat(fp)
            if st.st_size > 0 and st.st_size < 10_000_000:  # < 10MB
                files.append({"path": fp, "size": st.st_size, "mtime": st.st_mtime})
        except:
            pass

# Also check /tmp for outputs
for root, dirs, filenames in os.walk('/tmp'):
    dirs[:] = [d for d in dirs if d not in ('.cache', '__pycache__')]
    for fn in filenames:
        fp = os.path.join(root, fn)
        try:
            st = os.stat(fp)
            if st.st_size > 0 and st.st_size < 10_000_000:
                files.append({"path": fp, "size": st.st_size, "mtime": st.st_mtime})
        except:
            pass

print(json.dumps(files))
""")
        file_list = []
        for out in result.logs.stdout:
            try:
                file_list = json.loads(out.strip())
            except (json.JSONDecodeError, ValueError):
                pass

        if file_list:
            # Only save if there are interesting files
            out_dir.mkdir(parents=True, exist_ok=True)
            manifest = out_dir / "files_manifest.json"
            manifest.write_text(json.dumps(file_list, indent=2))
            report["saved"]["file_count"] = len(file_list)

            # Download files under 1MB (max 20)
            download_dir = out_dir / "files"
            download_dir.mkdir(exist_ok=True)
            downloaded = 0
            for f_info in sorted(file_list, key=lambda x: x["mtime"], reverse=True)[:20]:
                if f_info["size"] > 1_048_576:
                    continue
                try:
                    content = sbx.files.read(f_info["path"])
                    local_name = f_info["path"].replace("/", "_").lstrip("_")
                    if isinstance(content, bytes):
                        (download_dir / local_name).write_bytes(content)
                    else:
                        (download_dir / local_name).write_text(content)
                    downloaded += 1
                except Exception:
                    pass

            if downloaded:
                report["saved"]["downloaded"] = downloaded
                print(f"[pre-kill] Saved {downloaded} files from code sandbox", file=sys.stderr)

    except Exception as e:
        report["errors"].append(f"Pre-kill scan: {e}")

    if report["saved"]:
        summary = out_dir / "backup_summary.json"
        summary.write_text(json.dumps(report, indent=2))
        print(f"[pre-kill] Code sandbox backup → {out_dir}", file=sys.stderr)

    return report


def run_in_sandbox(code=None, shell_cmd=None, file_path=None,
                   sandbox_id=None, keep=False, timeout=300,
                   template="bigmac-code-v2-9-3"):
    Sandbox = _get_sandbox_class()
    api_key = get_e2b_api_key()

    if file_path:
        with open(file_path) as f:
            code = f.read()

    if sandbox_id:
        sbx = Sandbox.connect(sandbox_id, api_key=api_key)
        print(f"[sbx_run] Connected to existing sandbox: {sandbox_id}", file=sys.stderr)
    else:
        sbx = Sandbox.create(template=template, api_key=api_key, timeout=timeout)
        print(f"[sbx_run] Created sandbox: {sbx.sandbox_id} (template={template})", file=sys.stderr)

    result_data = {"sandbox_id": sbx.sandbox_id, "outputs": [], "error": None}

    try:
        if shell_cmd:
            execution = sbx.run_code(
                f"import subprocess, sys\n"
                f"r = subprocess.run({repr(shell_cmd)}, shell=True, capture_output=True, text=True, timeout={timeout})\n"
                f"print(r.stdout)\n"
                f"if r.stderr: print('[stderr]', r.stderr, file=sys.stderr)\n"
                f"sys.exit(r.returncode)"
            )
        else:
            execution = sbx.run_code(code)

        for out in execution.logs.stdout:
            print(out, end="")
            result_data["outputs"].append(out)
        for err in execution.logs.stderr:
            print(err, end="", file=sys.stderr)

        if execution.error:
            result_data["error"] = str(execution.error)
            print(f"\n[sbx_run] Error: {execution.error}", file=sys.stderr)

        if execution.results:
            for res in execution.results:
                if hasattr(res, "text") and res.text:
                    print(res.text)
                    result_data["outputs"].append(res.text)

    finally:
        if not keep:
            # Pre-kill hook: check for files worth saving
            backup = pre_kill_hook(sbx)
            if backup.get("saved"):
                result_data["backup"] = backup

            sbx.kill()
            print(f"[sbx_run] Sandbox {sbx.sandbox_id} killed.", file=sys.stderr)
        else:
            sbx.set_timeout(3600)
            print(f"[sbx_run] Sandbox kept alive: {sbx.sandbox_id}", file=sys.stderr)
            result_data["kept_alive"] = True

    print(f"\n[sbx_run_result] {json.dumps(result_data)}", file=sys.stderr)
    return result_data


def run_playwright(url, screenshot_path=None, sandbox_id=None, keep=False, timeout=300, template="bigmac-code-v2-9-3"):
    """Run Playwright automation against a URL.
    
    NOTE: E2B code interpreter runs in an async event loop.
    This uses async Playwright API automatically.
    """
    # Async code — E2B code interpreter already has an event loop running
    code = f'''
import subprocess, json

# Install chromium if needed (idempotent, ~10s first time)
subprocess.run(["playwright", "install", "chromium"], capture_output=True, timeout=120)

from playwright.async_api import async_playwright

p = await async_playwright().start()
browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
page = await browser.new_page()
await page.goto("{url}", wait_until="networkidle", timeout=30000)
await page.wait_for_timeout(2000)
print("Page title:", await page.title())
print("URL:", page.url)
{"await page.screenshot(path='/home/user/screenshot.png', full_page=True)" if screenshot_path else ""}
await browser.close()
await p.stop()
print("Playwright automation complete")
'''
    result = run_in_sandbox(code=code, sandbox_id=sandbox_id, keep=keep, timeout=timeout, template=template)

    if screenshot_path and not result.get("error"):
        # Download screenshot from sandbox
        try:
            Sandbox = _get_sandbox_class()
            api_key = get_e2b_api_key()
            sbx = Sandbox.connect(result["sandbox_id"], api_key=api_key) if keep else None
            if sbx:
                content = sbx.files.read("/home/user/screenshot.png")
                Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                mode = "wb" if isinstance(content, bytes) else "w"
                with open(screenshot_path, mode) as f:
                    f.write(content)
                result["screenshot_downloaded"] = screenshot_path
        except Exception as e:
            result["screenshot_error"] = str(e)
            print(f"[sbx_run] Screenshot download failed: {e}", file=sys.stderr)

    return result


def run_selenium(url, screenshot_path=None, sandbox_id=None, keep=False, timeout=300, template="bigmac-code-v2-9-3"):
    """Run Selenium automation against a URL."""
    code = f'''
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

from webdriver_manager.chrome import ChromeDriverManager
service = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=service, options=options)
try:
    driver.get("{url}")
    time.sleep(3)
    print("Page title:", driver.title)
    print("URL:", driver.current_url)
    {"driver.save_screenshot('/home/user/screenshot.png')" if screenshot_path else ""}
finally:
    driver.quit()
print("Selenium automation complete")
'''
    result = run_in_sandbox(code=code, sandbox_id=sandbox_id, keep=keep, timeout=timeout, template=template)

    if screenshot_path and not result.get("error"):
        print(f"[sbx_run] Screenshot saved in sandbox at /home/user/screenshot.png", file=sys.stderr)
        result["screenshot"] = "/home/user/screenshot.png"

    return result


def main():
    parser = argparse.ArgumentParser(description="Run code in E2B code interpreter sandbox")
    parser.add_argument("--code", help="Python code to execute")
    parser.add_argument("--shell", help="Shell command to execute")
    parser.add_argument("--file", help="Path to Python script file to execute")
    parser.add_argument("--sandbox-id", help="Reuse existing sandbox by ID")
    parser.add_argument("--keep", action="store_true", help="Keep sandbox alive after run")
    parser.add_argument("--timeout", type=int, default=300, help="Execution timeout in seconds")
    parser.add_argument("--template", default="bigmac-code-v2-9-3", help="E2B template name")

    parser.add_argument("--playwright", metavar="URL", help="Run Playwright against URL")
    parser.add_argument("--selenium", metavar="URL", help="Run Selenium against URL")
    parser.add_argument("--screenshot", metavar="PATH", help="Save screenshot locally")

    args = parser.parse_args()

    if args.playwright:
        result = run_playwright(
            url=args.playwright,
            screenshot_path=args.screenshot,
            sandbox_id=args.sandbox_id,
            keep=args.keep,
            timeout=args.timeout,
            template=args.template,
        )
        sys.exit(1 if result.get("error") else 0)

    if args.selenium:
        result = run_selenium(
            url=args.selenium,
            screenshot_path=args.screenshot,
            sandbox_id=args.sandbox_id,
            keep=args.keep,
            timeout=args.timeout,
            template=args.template,
        )
        sys.exit(1 if result.get("error") else 0)

    if not any([args.code, args.shell, args.file]):
        parser.error("Provide --code, --shell, --file, --playwright, or --selenium")

    result = run_in_sandbox(
        code=args.code,
        shell_cmd=args.shell,
        file_path=args.file,
        sandbox_id=args.sandbox_id,
        keep=args.keep,
        timeout=args.timeout,
        template=args.template,
    )
    sys.exit(1 if result.get("error") else 0)


if __name__ == "__main__":
    main()
