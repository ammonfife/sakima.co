#!/usr/bin/env python3
"""
playwright_test.py — Run Playwright tests in a BIGMAC desktop sandbox

REQUIRES: bigmac-desktop-v3-3-3 or later (has Playwright + Chromium pre-installed)
DO NOT use with code interpreter sandboxes.

Usage:
    python3 playwright_test.py --id <sandbox_id> --url https://example.com
    python3 playwright_test.py --id <sandbox_id> --script /path/to/local_script.py
    python3 playwright_test.py --id <sandbox_id> --url https://lkup.info --screenshot

The script uploads playwright code to the sandbox and runs it.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


PLAYWRIGHT_TEMPLATE = """
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = await browser.new_page()
        await page.goto("{url}", wait_until="networkidle", timeout=30000)
        title = await page.title()
        print(f"Title: {{title}}")
        print(f"URL: {{page.url}}")
{screenshot_code}
        await browser.close()
        return title

asyncio.run(main())
"""


def get_api_key():
    key = os.environ.get("E2B_API_KEY", "")
    if key:
        return key
    try:
        r = subprocess.run(["secrets", "get", "e2b_api_key"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return "e2b_a352bd385dbdc359d90a635006737dc331c6a9f0"


def run_playwright_in_sandbox(sandbox_id: str, script_code: str, api_key: str,
                               save_screenshot: bool = False):
    try:
        from e2b_desktop import Sandbox
        sbx = Sandbox.connect(sandbox_id, api_key=api_key)

        # Write the script to the sandbox
        sbx.files.write("/home/user/pw_test.py", script_code)

        # Run it
        result = sbx.commands.run(
            "cd /home/user && DISPLAY=:99 python3 pw_test.py",
            timeout=60
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)

        if save_screenshot:
            # Read screenshot if script saved one
            try:
                data = sbx.files.read("/home/user/screenshot.png")
                Path("screenshot.png").write_bytes(data)
                print("Screenshot saved to: screenshot.png", file=sys.stderr)
            except Exception:
                pass

        return result.exit_code or 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run Playwright in a desktop sandbox")
    parser.add_argument("--id", required=True, help="Desktop sandbox ID")
    parser.add_argument("--url", help="URL to visit and test")
    parser.add_argument("--script", help="Local Playwright Python script to upload and run")
    parser.add_argument("--screenshot", action="store_true",
                        help="Capture screenshot (saves to ./screenshot.png)")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.script:
        script_code = Path(args.script).read_text()
    elif args.url:
        screenshot_code = (
            '        await page.screenshot(path="/home/user/screenshot.png")\n'
            '        print("Screenshot saved")'
            if args.screenshot else ""
        )
        script_code = PLAYWRIGHT_TEMPLATE.format(
            url=args.url,
            screenshot_code=screenshot_code
        )
    else:
        print("ERROR: provide --url or --script", file=sys.stderr)
        return 1

    return run_playwright_in_sandbox(args.id, script_code, api_key,
                                      save_screenshot=args.screenshot)


if __name__ == "__main__":
    sys.exit(main())
