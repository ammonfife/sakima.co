"""HELP handler — list available SMS commands."""

HELP_TEXT = """📱 Sakima SMS Commands

CERT <#>  — Coin details by cert number
  e.g. CERT 12345678

PRICE <#> — Price guide for a cert
  e.g. PRICE 12345678

BID <#>   — Our buy price for a cert
  e.g. BID 12345678

HOURS     — Business hours & contact info

HELP      — This message

🌐 sakima.co | Park City, UT
Reply STOP to unsubscribe"""


async def handle_help() -> str:
    return HELP_TEXT
