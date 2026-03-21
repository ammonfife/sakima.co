"""Default/fallback handler — unknown commands."""


async def handle_default() -> str:
    return (
        "Text HELP for available commands.\n"
        "🌐 sakima.co"
    )
