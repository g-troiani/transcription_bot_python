"""
Propagation commands module.

This module is used to propagate slash commands to a guild. It sets an environment
flag to avoid duplicate cog addition and overrides the on_ready event to perform command
synchronization, print detailed debug information, and then close the bot and its HTTP session.
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

logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.DEBUG)

try:
    converted_guild_id = int(GUILD_ID)
    print(f"[DEBUG] GUILD_ID converted to integer: {converted_guild_id}")
except ValueError:
    print("[ERROR] GUILD_ID is not a valid integer!")
    converted_guild_id = None
if converted_guild_id is None:
    print("[ERROR] GUILD_ID is missing or invalid in your environment.")

@app_commands.guilds(discord.Object(id=converted_guild_id))
class TranscriptionCommands(commands.Cog):
    """
    Cog for testing guild-scoped commands.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DEBUG] TranscriptionCommands cog initialized.")

    @app_commands.command(
        name="record_test",
        description="Start a transcription session. (Example in propagate_commands.py)"
    )
    @app_commands.default_permissions(permissions=2150747648)
    async def record(self, interaction: discord.Interaction) -> None:
        print("[DEBUG] /record_test command invoked")
        await interaction.response.send_message("This is a test guild-scoped command from propagate_commands.py.")

@bot.event
async def on_ready() -> None:
    """
    Overridden on_ready event for propagation mode.

    Syncs the slash commands to the guild, prints detailed debug information,
    then waits before initiating shutdown.
    """
    print("[DEBUG] Propagation bot is ready. Beginning command sync...")
    try:
        guild = discord.Object(id=int(GUILD_ID))
        synced = await bot.tree.sync(guild=guild)
        print(f"[DEBUG] Commands synced for guild {converted_guild_id}")
        print("[DEBUG] Synced commands:", [cmd.name for cmd in synced])
    except Exception as e:
        print("[DEBUG] Error during propagation sync:", e)
    print("[DEBUG] Waiting 5 seconds before closing bot...")
    await asyncio.sleep(5)
    print("[DEBUG] Preparing to close bot after delay.")
    if hasattr(bot, "http") and bot.http.session:
        print(f"[DEBUG] HTTP session before close: {bot.http.session} Closed: {bot.http.session.closed}")
    else:
        print("[DEBUG] No HTTP session found before close.")
    try:
        print("[DEBUG] Calling bot.close() with timeout...")
        await asyncio.wait_for(bot.close(), timeout=10)
        print("[DEBUG] bot.close() completed.")
    except asyncio.TimeoutError:
        print("[DEBUG] bot.close() timed out!")
    except Exception as e:
        print("[DEBUG] Exception during bot.close():", e)
    await asyncio.sleep(3)
    if hasattr(bot, "http") and bot.http.session:
        print(f"[DEBUG] HTTP session after sleep: {bot.http.session} Closed: {bot.http.session.closed}")
        if not bot.http.session.closed:
            try:
                await bot.http.session.close()
                print("[DEBUG] HTTP session closed explicitly.")
            except Exception as e:
                print("[DEBUG] Exception while closing HTTP session:", e)
        else:
            print("[DEBUG] HTTP session was already closed after sleep.")
    else:
        print("[DEBUG] No HTTP session found after sleep.")
    pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
    print("[DEBUG] Pending tasks after bot.close():", pending_tasks)
    print("[DEBUG] Propagation shutdown complete.")

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
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print("[DEBUG] Exception in bot.start():", e)

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
        print("[DEBUG] Shutting down asynchronous generators...")
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print("[DEBUG] Event loop closed.")

if __name__ == "__main__":
    main()
