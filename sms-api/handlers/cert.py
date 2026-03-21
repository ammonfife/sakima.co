"""
CERT <number> handler — looks up coin cert via:
1. Sakima Turso inventory (coins table if it exists)
2. PCGS Cert Verification API (public)
3. NGC Cert Verification API (public)
"""
import logging
import os
import json
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

TURSO_URL   = os.environ.get("TURSO_URL", "").replace("libsql://", "https://")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")


def _turso_query(sql: str, args: list = None) -> list[dict]:
    """Execute a read query against Turso via HTTP pipeline."""
    if not TURSO_URL or not TURSO_TOKEN:
        return []
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [{"type": "text", "value": str(a)} for a in args]
    body = json.dumps({
        "requests": [
            {"type": "execute", "stmt": stmt},
            {"type": "close"},
        ]
    }).encode()
    req = urllib.request.Request(
        f"{TURSO_URL}/v2/pipeline",
        data=body,
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        r0 = data["results"][0]
        # Turso returns {"type":"ok","response":...} or {"type":"error","error":...}
        if r0.get("type") == "error":
            logger.debug("Turso error response: %s", r0.get("error"))
            return []
        result = r0["response"]["result"]
        cols = [c["name"] for c in result["cols"]]
        return [dict(zip(cols, [v["value"] for v in row])) for row in result["rows"]]
    except Exception as e:
        logger.debug("Turso query error: %s", e)
        return []


def _lookup_pcgs(cert: str) -> dict | None:
    """Query PCGS public cert verification endpoint."""
    url = f"https://www.pcgs.com/cert/{cert}"
    # PCGS has a JSON cert lookup API endpoint
    api_url = f"https://api.pcgs.com/publicapi/coindetail/GetCoinDetailByCertNo?CertNo={cert}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "SakimaSMS/1.0 (coin lookup bot)"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        if data and isinstance(data, dict):
            return {
                "service": "PCGS",
                "cert": cert,
                "name": data.get("CoinName") or data.get("coinName") or "Unknown",
                "grade": str(data.get("Grade") or data.get("grade") or ""),
                "designation": data.get("Designation") or data.get("designation") or "",
                "price_guide": data.get("PriceGuideValue") or data.get("priceGuideValue"),
            }
    except Exception as e:
        logger.debug("PCGS lookup failed for %s: %s", cert, e)
    return None


def _lookup_ngc(cert: str) -> dict | None:
    """Query NGC public cert verification endpoint."""
    api_url = f"https://www.ngccoin.com/certlookup/{cert}/60/"
    # NGC has a JSON endpoint too
    json_url = f"https://api.ngccoin.com/v1/coins/{cert}"
    try:
        req = urllib.request.Request(
            json_url,
            headers={"User-Agent": "SakimaSMS/1.0 (coin lookup bot)"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
        if data:
            coin = data.get("coins", [{}])[0] if data.get("coins") else data
            return {
                "service": "NGC",
                "cert": cert,
                "name": coin.get("coinName") or coin.get("description") or "Unknown",
                "grade": str(coin.get("grade") or ""),
                "designation": coin.get("designation") or "",
                "price_guide": None,
            }
    except Exception as e:
        logger.debug("NGC lookup failed for %s: %s", cert, e)
    return None


async def handle_cert(cert_raw: str) -> str:
    """Handle CERT <number> — return coin name, grade, value."""
    # Sanitize: keep only alphanumeric
    cert = "".join(c for c in cert_raw if c.isalnum())
    if not cert:
        return "Please send: CERT <certification number>\nExample: CERT 12345678"

    # 1. Check Turso inventory first
    rows = _turso_query(
        "SELECT * FROM coins WHERE cert = ? ORDER BY id DESC LIMIT 1",
        [cert]
    )
    if rows:
        r = rows[0]
        name  = r.get("description") or r.get("name") or "Unknown coin"
        grade = r.get("grade") or "?"
        price = r.get("price") or r.get("price_guide") or r.get("value")
        service = r.get("service") or "PCGS/NGC"
        msg = f"🪙 Cert #{cert} ({service})\n{name}\nGrade: {grade}"
        if price:
            msg += f"\nEst. Value: ${float(price):,.0f}"
        msg += f"\nDetails: sakima.co"
        return msg

    # 2. Try PCGS
    coin = _lookup_pcgs(cert)
    if not coin:
        # 3. Try NGC
        coin = _lookup_ngc(cert)

    if coin:
        name  = coin["name"]
        grade = coin["grade"]
        desig = coin["designation"]
        grade_str = f"{grade} {desig}".strip() if desig else grade
        price = coin.get("price_guide")
        service = coin["service"]

        msg = f"🪙 Cert #{cert} ({service})\n{name}\nGrade: {grade_str}"
        if price:
            try:
                msg += f"\nPrice Guide: ${float(price):,.0f}"
            except Exception:
                msg += f"\nPrice Guide: {price}"
        msg += "\nReply BID <cert#> for our buy price"
        return msg

    # Not found anywhere
    return (
        f"Cert #{cert} not found in PCGS or NGC databases.\n"
        "Double-check the number or visit sakima.co for help."
    )
