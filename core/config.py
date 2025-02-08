"""
Configuration module for the transcription bot.

This module pulls configuration variables from the environment.
"""

import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = os.getenv("GUILD_ID", "")
APPLICATION_ID = os.getenv("APPLICATION_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
