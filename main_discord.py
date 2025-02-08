"""
Main entry point for the Discord transcription bot.

This script starts the Discord bot.
"""

import asyncio
from integrations.discord_bot import run_discord_bot

async def main():
    """Run the Discord bot."""
    await run_discord_bot()

if __name__ == "__main__":
    asyncio.run(main())
