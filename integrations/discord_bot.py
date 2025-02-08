# ************************************************************
#  integrations/discord_bot.py
# ************************************************************

"""
Discord integration module for the live transcription bot.

This module provides a minimal Discord bot that can join a voice channel,
start a transcription session (including capturing audio via a custom sink),
post the transcript and summary, and leave the channel.
It includes detailed debug statements to help trace command interactions and overall flow.
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from core.config import DISCORD_TOKEN, GUILD_ID
from core.transcription_logic import SessionManager
from core.summarizer import summarize_transcript

# Import the custom voice client subclass.
from integrations.custom_voice_client import CustomVoiceClient

# Create a global session manager for transcription.
session_manager = SessionManager()

# Set up minimal intents.
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

# Instantiate the bot.
bot = commands.Bot(command_prefix="!", intents=intents)

##############################
# Audio Sink Implementation  #
##############################

class MyAudioSink:
    """
    A minimal audio sink that captures PCM data and passes it to the session manager.
    
    This sink is intended to be used with a voice client's recording method.
    """
    def __init__(self, guild_id: int, user_id: int, session_manager: SessionManager):
        """
        Initialize the audio sink.
        
        Args:
            guild_id (int): The guild ID.
            user_id (int): The ID of the user whose audio is being recorded.
            session_manager (SessionManager): The session manager instance.
        """
        self.guild_id = guild_id
        self.user_id = user_id
        self.session_manager = session_manager
        print(f"[DEBUG] MyAudioSink initialized for user {user_id} in guild {guild_id}.")

    def write(self, data: bytes):
        """
        Called when a chunk of PCM audio data is received.
        
        Args:
            data (bytes): The raw PCM audio data.
        """
        print(f"[DEBUG] MyAudioSink received {len(data)} bytes for user {self.user_id}.")
        self.session_manager.process_audio_chunk(self.guild_id, self.user_id, data)

    def cleanup(self):
        """
        Called when recording is finished to perform any necessary cleanup.
        """
        print(f"[DEBUG] MyAudioSink cleanup for user {self.user_id}.")

def finished_callback(sink, channel):
    """
    Callback function called when the voice client's recording finishes.
    
    Args:
        sink (MyAudioSink): The audio sink used during recording.
        channel (discord.TextChannel): The text channel associated with the recording session.
    """
    print(f"[DEBUG] Finished recording for user {sink.user_id} in guild {sink.guild_id}.")

##############################
# End Audio Sink Section     #
##############################

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """
    Event handler that logs every interaction received.
    """
    print("[DEBUG] on_interaction event received.")
    print("   Type:", interaction.type)
    print("   User:", interaction.user)
    print("   Data:", interaction.data)

class TranscriptionCog(commands.Cog):
    """
    Cog containing slash commands for live transcription.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[DEBUG] TranscriptionCog loaded.")

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction) -> None:
        """
        Join the voice channel of the invoking user.
        """
        print(f"[DEBUG] /join command invoked by {interaction.user} in guild {interaction.guild.id}")
        print(f"[DEBUG] Interaction data: {interaction.data}")
        if not interaction.user.voice or not interaction.user.voice.channel:
            try:
                await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
                print("[DEBUG] /join: User is not in a voice channel.")
            except Exception as e:
                print("[DEBUG] /join: Exception sending message:", e)
            return
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            try:
                await interaction.response.send_message("Already in a voice channel.", ephemeral=True)
                print("[DEBUG] /join: Bot already connected to a voice channel.")
            except Exception as e:
                print("[DEBUG] /join: Exception sending 'already connected' message:", e)
            return
        try:
            await interaction.response.defer()
            vc = await channel.connect()
            print(f"[DEBUG] /join: Successfully connected to {channel.name}")
            await interaction.followup.send(f"Joined {channel.name}.")
        except Exception as e:
            print(f"[DEBUG] /join: Error connecting to voice channel: {e}")
            try:
                await interaction.followup.send("Failed to join the voice channel.", ephemeral=True)
            except Exception as inner_e:
                print("[DEBUG] /join: Exception sending failure message:", inner_e)

    @app_commands.command(name="record", description="Start transcription")
    async def record(self, interaction: discord.Interaction) -> None:
        """
        Start the transcription session for the guild.
        """
        print(f"[DEBUG] /record command invoked by {interaction.user} in guild {interaction.guild.id}")
        try:
            session_manager.start_recording(interaction.guild.id)
            await interaction.response.send_message("Recording started.")
            print("[DEBUG] /record: Recording session started.")
        except Exception as e:
            print("[DEBUG] /record: Exception occurred:", e)
            await interaction.response.send_message("Error starting recording.", ephemeral=True)

    @app_commands.command(name="joinrecord", description="Join voice channel and start transcription")
    async def joinrecord(self, interaction: discord.Interaction) -> None:
        """
        Join the user's voice channel and start the transcription session.
        Combines /join and /record, and attaches an audio sink to capture PCM audio.
        """
        print(f"[DEBUG] /joinrecord command invoked by {interaction.user} in guild {interaction.guild.id}")
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("Join a voice channel first.", ephemeral=True)
            print("[DEBUG] /joinrecord: User not in a voice channel.")
            return
        channel = interaction.user.voice.channel
        try:
            if not interaction.guild.voice_client:
                # Connect using the custom voice client.
                vc = await channel.connect(cls=CustomVoiceClient)
                print(f"[DEBUG] /joinrecord: Connected to {channel.name} using CustomVoiceClient.")
            else:
                vc = interaction.guild.voice_client
                print("[DEBUG] /joinrecord: Already connected to a voice channel.")
        except Exception as e:
            print(f"[DEBUG] /joinrecord: Error connecting to voice channel: {e}")
            await interaction.followup.send("Failed to connect to the voice channel.", ephemeral=True)
            return
        try:
            session_manager.start_recording(interaction.guild.id)
            # Check if the voice client supports audio receiving.
            if not hasattr(vc, "start_recording"):
                error_msg = "Voice receiving is not supported by this bot's voice client. No audio will be captured."
                print(f"[DEBUG] /joinrecord: {error_msg}")
                await interaction.followup.send(error_msg, ephemeral=True)
                return
            # Create an audio sink to capture audio.
            sink = MyAudioSink(interaction.guild.id, interaction.user.id, session_manager)
            try:
                # IMPORTANT: await the start_recording coroutine.
                await vc.start_recording(sink, finished_callback, interaction.channel)
                print(f"[DEBUG] /joinrecord: Voice recording started with sink for user {interaction.user.id}.")
            except Exception as e:
                print("[DEBUG] /joinrecord: Error starting voice recording with sink:", e)
                await interaction.followup.send("Error starting voice recording.", ephemeral=True)
                return
            await interaction.followup.send(f"Joined {channel.name} and started recording.")
            print(f"[DEBUG] /joinrecord: Recording started in {channel.name}.")
        except Exception as e:
            print(f"[DEBUG] /joinrecord: Error starting recording: {e}")
            await interaction.followup.send("Error starting recording.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop transcription and post transcript")
    async def stop(self, interaction: discord.Interaction) -> None:
        """
        Stop the transcription session and post the transcript and summary.
        """
        print(f"[DEBUG] /stop command invoked by {interaction.user} in guild {interaction.guild.id}")
        await interaction.response.defer()
        try:
            transcript = session_manager.stop_recording(interaction.guild.id)
            print("[DEBUG] /stop: Transcript obtained. Length:", len(transcript))
            if not transcript.strip():
                print("[DEBUG] /stop: Transcript is empty.")
                await interaction.followup.send("No transcript available.")
                return
            await interaction.followup.send("Transcript:")
            await interaction.channel.send(transcript)
            print("[DEBUG] /stop: Transcript posted in channel.")
            summary = summarize_transcript(transcript)
            if not summary.strip():
                print("[DEBUG] /stop: Summary is empty.")
                summary = "No summary available."
            await interaction.channel.send(f"Summary:\n{summary}")
            print("[DEBUG] /stop: Summary posted in channel.")
        except Exception as e:
            print("[DEBUG] /stop: Error during stop command:", e)
            await interaction.response.send_message("Error stopping transcription.", ephemeral=True)

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        """
        Disconnect the bot from the voice channel and remove the session.
        """
        print(f"[DEBUG] /leave command invoked by {interaction.user} in guild {interaction.guild.id}")
        try:
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.disconnect()
                session_manager.remove_session(interaction.guild.id)
                await interaction.response.send_message("Left voice channel.")
                print("[DEBUG] /leave: Disconnected from voice channel.")
            else:
                await interaction.response.send_message("Not connected to any voice channel.", ephemeral=True)
                print("[DEBUG] /leave: No active voice connection found.")
        except Exception as e:
            print("[DEBUG] /leave: Exception during disconnect:", e)
            await interaction.response.send_message("Error leaving the voice channel.", ephemeral=True)

@bot.event
async def on_ready() -> None:
    """
    Event handler triggered when the bot is ready.
    
    If PROPAGATE_ONLY is set in the environment, sync slash commands to the guild.
    Otherwise, simply print "Bot is online!".
    """
    if os.getenv("PROPAGATE_ONLY"):
        print("[DEBUG] Propagation mode: Syncing commands...")
        try:
            guild = discord.Object(id=int(GUILD_ID))
            synced = await bot.tree.sync(guild=guild)
            print("[DEBUG] Commands synced:", [cmd.name for cmd in synced])
        except Exception as e:
            print("[DEBUG] Error syncing commands:", e)
    print("Bot is online!")

async def run_discord_bot() -> None:
    """
    Start the Discord bot.
    
    Adds the TranscriptionCog to the bot and starts the bot using the Discord token.
    """
    print("[DEBUG] Adding TranscriptionCog to the bot...")
    await bot.add_cog(TranscriptionCog(bot))
    print("[DEBUG] Starting bot with token.")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_discord_bot())
