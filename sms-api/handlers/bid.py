"""
BID <cert> handler — return our current buy/bid price for a coin.
Checks Turso inventory for bid_price field; falls back to graceful message.
"""
import logging
from handlers.cert import _turso_query, _lookup_pcgs, _lookup_ngc

logger = logging.getLogger(__name__)

# Redis caching (optional — speeds up repeated lookups)
import os, json

REDIS_HOST  = os.environ.get("REDIS_HOST", "")
REDIS_TOKEN = os.environ.get("REDIS_TOKEN", "")


def _redis_get(key: str) -> str | None:
    if not REDIS_HOST or not REDIS_TOKEN:
        return None
    import urllib.request
    try:
        url = f"https://{REDIS_HOST}/get/{key}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("result")
    except Exception as e:
        logger.debug("Redis GET failed: %s", e)
        return None


def _redis_set(key: str, value: str, ex: int = 3600) -> None:
    if not REDIS_HOST or not REDIS_TOKEN:
        return
    import urllib.request
    try:
        url = f"https://{REDIS_HOST}/set/{key}/{urllib.parse.quote(value)}?ex={ex}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
        )
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        logger.debug("Redis SET failed: %s", e)


async def handle_bid(cert_raw: str) -> str:
    """Return bid/buy price for a cert."""
    cert = "".join(c for c in cert_raw if c.isalnum())
    if not cert:
        return "Please send: BID <certification number>\nExample: BID 12345678"

    cache_key = f"sakima:bid:{cert}"
    cached = _redis_get(cache_key)
    if cached:
        return cached

    # Check inventory
    rows = _turso_query(
        "SELECT * FROM coins WHERE cert = ? ORDER BY id DESC LIMIT 1",
        [cert]
    )
    if rows:
        r = rows[0]
        name  = r.get("description") or r.get("name") or "Coin"
        grade = r.get("grade") or "?"
        bid   = r.get("bid_price") or r.get("buy_price") or r.get("bid")
        service = r.get("service") or "PCGS/NGC"

        if bid:
            reply = (
                f"🤝 Cert #{cert} ({service})\n{name} - {grade}\n"
                f"Our Buy Price: ${float(bid):,.0f}\n"
                f"To sell: sakima.co or reply SELL"
            )
        else:
            # Coin is in DB but no bid price on file
            reply = (
                f"🪙 Cert #{cert} — {name} ({grade})\n"
                f"No current bid on file.\n"
                f"Submit an offer at sakima.co or call us."
            )
        _redis_set(cache_key, reply, ex=1800)
        return reply

    # Not in inventory — get name from PCGS/NGC for friendly response
    coin = _lookup_pcgs(cert) or _lookup_ngc(cert)
    if coin:
        name  = coin["name"]
        grade = coin["grade"]
        desig = coin.get("designation") or ""
        grade_str = f"{grade} {desig}".strip()
        reply = (
            f"🪙 Cert #{cert} — {name} ({grade_str})\n"
            f"Not currently in our inventory.\n"
            f"Submit a sell offer at sakima.co"
        )
    else:
        reply = (
            f"Cert #{cert} not found.\n"
            f"To get a buy price, visit sakima.co or call us directly."
        )

    _redis_set(cache_key, reply, ex=900)
    return reply
