#!/usr/bin/env python3
"""
acquire.py — Get a warm E2B BIGMAC sandbox (code or desktop)

Usage:
    python3 acquire.py --type desktop          # Get desktop sandbox (Playwright, Chrome)
    python3 acquire.py --type code             # Get code interpreter sandbox
    python3 acquire.py --type desktop --fresh  # Force-create new (skip pool)
    python3 acquire.py --type desktop --vnc    # Print VNC URL after acquiring

Outputs JSON: {"sandbox_id": "...", "type": "desktop"|"code", "vnc_url": "...", "fresh": bool}
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

POOL_JSON = Path.home() / ".openclaw" / "e2b-desktop-pool.json"
DESKTOP_TEMPLATE = "bigmac-desktop-v3-3-3"
CODE_TEMPLATE = "bigmac-code-v2-9-3"


def get_e2b_api_key():
    key = os.environ.get("E2B_API_KEY", "")
    if key:
        return key
    # Try secrets vault
    try:
        result = subprocess.run(["secrets", "get", "e2b_api_key"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    # Try macOS keychain
    try:
        result = subprocess.run(["security", "find-generic-password", "-s", "E2B_API_KEY", "-a", "benfife", "-w"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    sys.exit("ERROR: E2B_API_KEY not found. Set env var, add to secrets vault, or add to macOS keychain.")


def pool_acquire_desktop():
    """Try to grab a warm desktop sandbox from the pool JSON."""
    if not POOL_JSON.exists():
        return None
    try:
        data = json.loads(POOL_JSON.read_text())
        sandboxes = data.get("sandboxes", [])
        if sandboxes:
            s = sandboxes[0]
            return {
                "sandbox_id": s["sandbox_id"],
                "type": "desktop",
                "vnc_url": s.get("vnc_url", ""),
                "direct_url": s.get("direct_url", ""),
                "fresh": False,
            }
    except Exception:
        pass
    return None


def create_sandbox(template: str, sandbox_type: str, timeout_min: int = 60):
    """Create a new sandbox via e2b CLI."""
    api_key = get_e2b_api_key()
    env = {**os.environ, "E2B_API_KEY": api_key}
    # Use e2b CLI to create
    cmd = ["e2b", "sandbox", "spawn", template,
           "--timeout", str(timeout_min * 60)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    if result.returncode != 0:
        # Fallback: use Python SDK
        return create_sandbox_sdk(template, sandbox_type, api_key, timeout_min)
    # Parse sandbox_id from output
    for line in result.stdout.splitlines():
        if "sandbox_id" in line.lower() or line.strip().startswith("i"):
            sandbox_id = line.strip().split()[-1]
            break
    else:
        sandbox_id = result.stdout.strip().split()[-1]
    return build_result(sandbox_id, sandbox_type, fresh=True)


def create_sandbox_sdk(template: str, sandbox_type: str, api_key: str, timeout_min: int):
    """Create sandbox via Python SDK."""
    try:
        if sandbox_type == "desktop":
            from e2b_desktop import Sandbox
        else:
            from e2b_code_interpreter import Sandbox
        sbx = Sandbox.create(template=template,
                              api_key=api_key,
                              timeout=timeout_min * 60)
        sandbox_id = sbx.sandbox_id
        sbx.close()
        return build_result(sandbox_id, sandbox_type, fresh=True)
    except Exception as e:
        print(f"ERROR: Failed to create sandbox: {e}", file=sys.stderr)
        sys.exit(1)


def build_result(sandbox_id: str, sandbox_type: str, fresh: bool):
    result = {"sandbox_id": sandbox_id, "type": sandbox_type, "fresh": fresh}
    if sandbox_type == "desktop":
        result["vnc_url"] = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
        result["direct_url"] = f"https://{sandbox_id}.e2b.app"
    else:
        result["direct_url"] = f"https://{sandbox_id}.e2b.app"
    return result


def main():
    parser = argparse.ArgumentParser(description="Acquire a BIGMAC E2B sandbox")
    parser.add_argument("--type", choices=["desktop", "code"], default="desktop",
                        help="Sandbox type (default: desktop)")
    parser.add_argument("--fresh", action="store_true",
                        help="Skip pool, force-create new sandbox")
    parser.add_argument("--vnc", action="store_true",
                        help="Print VNC URL after acquiring (desktop only)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Sandbox lifetime in minutes (default: 60)")
    args = parser.parse_args()

    result = None

    if not args.fresh and args.type == "desktop":
        result = pool_acquire_desktop()
        if result:
            print(f"# Using warm pool sandbox: {result['sandbox_id']}", file=sys.stderr)

    if result is None:
        template = DESKTOP_TEMPLATE if args.type == "desktop" else CODE_TEMPLATE
        print(f"# Spinning up new {args.type} sandbox ({template})...", file=sys.stderr)
        result = create_sandbox(template, args.type, args.timeout)

    print(json.dumps(result, indent=2))

    if args.vnc and result.get("vnc_url"):
        print(f"\nVNC: {result['vnc_url']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
