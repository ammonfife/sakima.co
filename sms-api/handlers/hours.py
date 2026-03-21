"""
HOURS handler — return Sakima business hours.
Edit HOURS_TEXT to update without redeploying.
"""

HOURS_TEXT = """🕐 Sakima Hours

Mon–Fri: 10am – 6pm MT
Saturday: 10am – 4pm MT
Sunday: Closed

📍 Park City, UT
🌐 sakima.co
📞 Text or call anytime — we respond during business hours."""


async def handle_hours() -> str:
    return HOURS_TEXT
