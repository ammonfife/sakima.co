#!/usr/bin/env python3
"""
run_code.py — Run Python or shell code in a BIGMAC E2B sandbox

Usage:
    python3 run_code.py --id <sandbox_id> --type code --code "print('hello')"
    python3 run_code.py --id <sandbox_id> --type code --file script.py
    python3 run_code.py --id <sandbox_id> --type desktop --shell "ls /home/user"
    python3 run_code.py --id <sandbox_id> --type desktop --shell "python3 /home/user/inject-google-cookies.py"

Outputs: stdout/stderr from execution
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


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


def run_in_code_interpreter(sandbox_id: str, code: str, api_key: str):
    try:
        from e2b_code_interpreter import Sandbox
        sbx = Sandbox.connect(sandbox_id, api_key=api_key)
        result = sbx.run_code(code)
        if result.logs.stdout:
            print("".join(result.logs.stdout))
        if result.logs.stderr:
            print("STDERR:", "".join(result.logs.stderr), file=sys.stderr)
        if result.error:
            print(f"ERROR: {result.error}", file=sys.stderr)
            return 1
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def run_shell(sandbox_id: str, cmd: str, sandbox_type: str, api_key: str):
    """Run a shell command via process execution in any sandbox type."""
    try:
        if sandbox_type == "code":
            from e2b_code_interpreter import Sandbox
        else:
            from e2b_desktop import Sandbox
        sbx = Sandbox.connect(sandbox_id, api_key=api_key)
        result = sbx.commands.run(cmd, timeout=120)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        return result.exit_code or 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run code in a BIGMAC E2B sandbox")
    parser.add_argument("--id", required=True, help="Sandbox ID")
    parser.add_argument("--type", choices=["desktop", "code"], default="code",
                        help="Sandbox type (default: code)")
    parser.add_argument("--code", help="Python code to run (code interpreter only)")
    parser.add_argument("--file", help="Python file to run")
    parser.add_argument("--shell", help="Shell command to run")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.file:
        args.code = Path(args.file).read_text()

    if args.code:
        if args.type != "code":
            # Run as python3 -c in shell on desktop
            escaped = args.code.replace("'", "'\"'\"'")
            return run_shell(args.id, f"python3 -c '{escaped}'", args.type, api_key)
        return run_in_code_interpreter(args.id, args.code, api_key)
    elif args.shell:
        return run_shell(args.id, args.shell, args.type, api_key)
    else:
        print("ERROR: provide --code, --file, or --shell", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
