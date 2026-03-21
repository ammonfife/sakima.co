"""
PRICE <cert> handler — return pricing info for a cert.
Delegates cert lookup then surfaces price data.
"""
from handlers.cert import handle_cert, _turso_query, _lookup_pcgs, _lookup_ngc


async def handle_price(cert_raw: str) -> str:
    """Return price guide info for a cert number."""
    cert = "".join(c for c in cert_raw if c.isalnum())
    if not cert:
        return "Please send: PRICE <certification number>\nExample: PRICE 12345678"

    # Check inventory for our own price
    rows = _turso_query(
        "SELECT * FROM coins WHERE cert = ? ORDER BY id DESC LIMIT 1",
        [cert]
    )
    if rows:
        r = rows[0]
        name  = r.get("description") or r.get("name") or "Coin"
        price = r.get("price") or r.get("price_guide") or r.get("value")
        ask   = r.get("ask_price") or r.get("list_price")
        grade = r.get("grade") or "?"
        service = r.get("service") or "PCGS/NGC"

        msg = f"💰 Cert #{cert} ({service})\n{name} - {grade}"
        if price:
            msg += f"\nPrice Guide: ${float(price):,.0f}"
        if ask:
            msg += f"\nOur Ask: ${float(ask):,.0f}"
        if not price and not ask:
            msg += "\nPrice not on file — text BID for our buy price"
        return msg

    # Fall back to cert handler (includes price guide from PCGS)
    cert_reply = await handle_cert(cert_raw)
    if "not found" in cert_reply.lower():
        return cert_reply
    return cert_reply + "\nFor a personalized offer, visit sakima.co"
