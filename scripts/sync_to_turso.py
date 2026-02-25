#!/usr/bin/env python3
"""
Sync sakima.co shows and listings data to Turso database.
Used by GitHub Actions and for manual backfills.

Environment variables:
  TURSO_URL   - Turso database URL (libsql:// or https://)
  TURSO_TOKEN - Turso auth token
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def get_turso_url():
    """Get Turso HTTP URL from env."""
    url = os.environ.get("TURSO_URL", "")
    if not url:
        raise ValueError("TURSO_URL not set")
    # Convert libsql:// to https://
    return url.replace("libsql://", "https://")


def get_turso_token():
    """Get Turso token from env or macOS keychain."""
    token = os.environ.get("TURSO_TOKEN", "")
    if token:
        return token
    # Try macOS keychain
    import subprocess
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "turso-bigmac-token", "-a", "bigmac", "-w"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        raise ValueError("TURSO_TOKEN not set and keychain lookup failed")


def turso_execute(url, token, statements):
    """Execute statements via Turso HTTP API v2 pipeline."""
    endpoint = f"{url}/v2/pipeline"
    body = {
        "requests": [
            {"type": "execute", "stmt": s} for s in statements
        ] + [{"type": "close"}]
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


def create_tables(url, token):
    """Create shows and items tables if they don't exist."""
    statements = [
        {
            "sql": """CREATE TABLE IF NOT EXISTS sakima_shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT,
                image TEXT,
                rsvp INTEGER,
                tags TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            )"""
        },
        {
            "sql": """CREATE UNIQUE INDEX IF NOT EXISTS idx_sakima_shows_title_date 
                ON sakima_shows(title, date)"""
        },
        {
            "sql": """CREATE TABLE IF NOT EXISTS sakima_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                title TEXT NOT NULL,
                price TEXT,
                bin_price TEXT,
                buying_options TEXT,
                bids INTEGER DEFAULT 0,
                end_date TEXT,
                image TEXT,
                url TEXT,
                platform TEXT DEFAULT 'eBay',
                updated_at TEXT DEFAULT (datetime('now'))
            )"""
        },
        {
            "sql": """CREATE UNIQUE INDEX IF NOT EXISTS idx_sakima_items_url 
                ON sakima_items(url)"""
        },
    ]
    result = turso_execute(url, token, statements)
    print("Tables created/verified.")
    return result


def sync_shows(url, token, data_dir):
    """Upsert shows from shows.json into Turso."""
    shows_file = Path(data_dir) / "shows.json"
    if not shows_file.exists():
        print("No shows.json found, skipping.")
        return

    with open(shows_file) as f:
        shows = json.load(f)

    if not shows:
        print("No shows to sync.")
        return

    # Clear and re-insert (simpler than complex upsert for small dataset)
    statements = [{"sql": "DELETE FROM sakima_shows"}]

    for show in shows:
        statements.append({
            "sql": """INSERT INTO sakima_shows (title, date, image, rsvp, tags, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            "args": [
                {"type": "text", "value": show.get("title", "")},
                {"type": "text", "value": show.get("date") or ""},
                {"type": "text", "value": show.get("image") or ""},
                {"type": "integer", "value": str(show.get("rsvp") or 0)},
                {"type": "text", "value": json.dumps(show.get("tags", []))},
            ]
        })

    turso_execute(url, token, statements)
    print(f"Synced {len(shows)} shows to Turso.")


def sync_items(url, token, data_dir):
    """Upsert items from listings.json into Turso."""
    items_file = Path(data_dir) / "listings.json"
    if not items_file.exists():
        print("No listings.json found, skipping.")
        return

    with open(items_file) as f:
        items = json.load(f)

    # Clear and re-insert
    statements = [{"sql": "DELETE FROM sakima_items"}]

    for item in items:
        statements.append({
            "sql": """INSERT INTO sakima_items (title, price, bin_price, buying_options, bids, end_date, image, url, platform, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            "args": [
                {"type": "text", "value": item.get("title", "")},
                {"type": "text", "value": item.get("price") or ""},
                {"type": "text", "value": item.get("binPrice") or ""},
                {"type": "text", "value": json.dumps(item.get("buyingOptions", []))},
                {"type": "integer", "value": str(item.get("bids") or 0)},
                {"type": "text", "value": item.get("endDate") or ""},
                {"type": "text", "value": item.get("image") or ""},
                {"type": "text", "value": item.get("url") or ""},
                {"type": "text", "value": item.get("platform", "eBay")},
            ]
        })

    turso_execute(url, token, statements)
    print(f"Synced {len(items)} items to Turso.")


def main():
    url = get_turso_url()
    token = get_turso_token()

    # Default data dir: ../data relative to this script, or CWD/data
    data_dir = os.environ.get("DATA_DIR")
    if not data_dir:
        script_dir = Path(__file__).parent
        data_dir = str(script_dir.parent / "data")

    print(f"Data dir: {data_dir}")

    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    if what in ("all", "init"):
        create_tables(url, token)
    if what in ("all", "shows"):
        sync_shows(url, token, data_dir)
    if what in ("all", "items", "listings"):
        sync_items(url, token, data_dir)

    print("Done.")


if __name__ == "__main__":
    main()
