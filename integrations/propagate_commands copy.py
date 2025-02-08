"""
Propagation commands module.

This module is used to propagate slash commands to a guild.
It sets an environment flag to avoid duplicate cog addition and
overrides the on_ready event to perform command synchronization,
print debug information, and then close the bot and its HTTP session.
"""

import os
os.environ["PROPAGATE_ONLY"] = "1"  # Signal that we are only propagating commands

import sys
import asyncio
import discord
from discord import app_commands
import logging
from discord.ext import commands

# Append the project root to sys.path so modules can be imported.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.discord_bot import bot, TranscriptionCog
from core.config import DISCORD_TOKEN, GUILD_ID

# Set logging levels for detailed debug output.
logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.DEBUG)

try:
    converted_guild_id = int(GUILD_ID)
except ValueError:
    print("ERROR: GUILD_ID is not a valid integer!")
    converted_guild_id = None
if converted_guild_id is None:
    print("ERROR: GUILD_ID is missing or invalid in your environment.")

@app_commands.guilds(discord.Object(id=converted_guild_id))
class TranscriptionCommands(commands.Cog):
    """
    Cog for testing guild-scoped commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="record_test",
        description="Start a transcription session. (Example in propagate_commands.py)"
    )
    @app_commands.default_permissions(permissions=2150747648)
    async def record(self, interaction: discord.Interaction) -> None:
        print("[DEBUG] /record_test command invoked")
        await interaction.response.send_message("This is a test guild-scoped command from propagate_commands.py.")

# Override the on_ready event for propagation purposes.
@bot.event
async def on_ready() -> None:
    """
    Event handler for when the bot is ready.
    
    Syncs the slash commands to the specified guild, prints debug information,
    then closes the bot and ensures the HTTP client session is properly closed.
    """
    print("[DEBUG] Propagation bot is ready.")
    guild = discord.Object(id=converted_guild_id)
    try:
        synced = await bot.tree.sync(guild=guild)
        print("[DEBUG] Commands synced for guild", converted_guild_id)
        print("[DEBUG] Synced commands:", [cmd.name for cmd in synced])
    except Exception as e:
        print("[DEBUG] Error during propagation:", e)
    finally:
        await bot.close()
        await asyncio.sleep(1)  # Give cleanup time.
        if hasattr(bot, "http") and bot.http.session and not bot.http.session.closed:
            await bot.http.session.close()
            print("[DEBUG] HTTP session closed.")
        else:
            print("[DEBUG] HTTP session already closed.")

async def propagate_slash_commands() -> None:
    """
    Propagate and sync guild-scoped commands.
    
    Clears existing global commands for the target guild, adds both the testing cog
    and the main transcription cog (if not already present), copies global commands
    to the guild's command tree, and then starts the bot.
    """
    guild = discord.Object(id=converted_guild_id)
    
    print("[DEBUG] Global commands before clearing:", [cmd.name for cmd in bot.tree.get_commands()])
    bot.tree.clear_commands(guild=guild)
    print("[DEBUG] Global commands after clearing for guild:", [cmd.name for cmd in bot.tree.get_commands()])
    
    await bot.add_cog(TranscriptionCommands(bot))
    if not bot.get_cog("TranscriptionCog"):
        await bot.add_cog(TranscriptionCog(bot))
    print("[DEBUG] Global commands after adding cogs:", [cmd.name for cmd in bot.tree.get_commands()])
    
    bot.tree.copy_global_to(guild=guild)
    guild_commands = bot.tree.get_commands(guild=guild)
    print("[DEBUG] Guild command tree after copying global commands:", [cmd.name for cmd in guild_commands])
    
    print("[DEBUG] Starting bot for propagation...")
    await bot.start(DISCORD_TOKEN)

def main() -> None:
    """
    Create and run a new event loop to propagate slash commands.
    
    Ensures that asynchronous generators are properly shutdown.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(propagate_slash_commands())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    main()
