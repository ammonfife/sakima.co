"""
Message router — parses inbound SMS body and dispatches to correct handler.
Fuzzy: case-insensitive, strips extra whitespace, handles common typos via prefix matching.
"""
import re
from handlers.cert    import handle_cert
from handlers.price   import handle_price
from handlers.bid     import handle_bid
from handlers.hours   import handle_hours
from handlers.help    import handle_help
from handlers.default import handle_default


# Keyword → (handler, expects_arg)
ROUTES = [
    (r"^certs?\s+(.+)",  handle_cert,  True),
    (r"^price\s+(.+)",   handle_price, True),
    (r"^bid\s+(.+)",     handle_bid,   True),
    (r"^hours?$",        handle_hours, False),
    (r"^help$",          handle_help,  False),
    # Partial / typo-tolerant extras
    (r"^look\s*up\s+(.+)", handle_cert, True),   # "look up 12345"
    (r"^lookup\s+(.+)",    handle_cert, True),
    (r"^value\s+(.+)",     handle_price, True),
    (r"^buy\s+(.+)",       handle_bid,  True),
]


async def route_message(body: str) -> str:
    """Return reply string for inbound SMS body."""
    normalized = re.sub(r"\s+", " ", body.strip()).lower()

    for pattern, handler, has_arg in ROUTES:
        m = re.match(pattern, normalized, re.IGNORECASE)
        if m:
            if has_arg:
                arg = m.group(1).strip()
                return await handler(arg)
            else:
                return await handler()

    return await handle_default()
