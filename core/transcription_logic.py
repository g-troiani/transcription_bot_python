# ************************************************************
#  core/transcription_logic.py
# ************************************************************

"""
Transcription logic module.

Manages sessions for multiple guilds, buffers per-user audio, and performs
near-real-time transcription using the RealtimeSTT library.
"""

import os
import threading
import time
import uuid
from typing import Dict, List

from core import audio_utils
from RealtimeSTT import AudioToTextRecorder  # Import the recorder class from RealtimeSTT

class Session:
    """
    Represents a transcription session for a guild.
    
    Attributes:
        is_recording (bool): Whether the session is currently recording.
        user_transcripts (Dict[int, List[str]]): Accumulated transcript segments per user.
        user_names (Dict[int, str]): Mapping from user ID to display name.
        audio_buffers (Dict[int, bytearray]): Audio buffers (PCM) for each user.
    """
    def __init__(self) -> None:
        self.is_recording: bool = False
        self.user_transcripts: Dict[int, List[str]] = {}
        self.user_names: Dict[int, str] = {}
        self.audio_buffers: Dict[int, bytearray] = {}

    def append_final_line(self, user_id: int, text: str) -> None:
        """
        Append transcribed text for a given user.
        
        Args:
            user_id (int): The user's ID.
            text (str): The transcribed text.
        """
        self.user_transcripts.setdefault(user_id, []).append(text)
        print(f"[DEBUG] Appended transcript for user {user_id}: {text}")

    def get_combined_transcript(self) -> str:
        """
        Get the full transcript of the session with user labels.
        
        Returns:
            str: The aggregated transcript.
        """
        lines = []
        for uid, texts in self.user_transcripts.items():
            name = self.user_names.get(uid, f"User {uid}")
            for t in texts:
                lines.append(f"{name}:\n{t}\n")
        transcript = "\n".join(lines)
        print(f"[DEBUG] Combined transcript length: {len(transcript)} characters")
        return transcript

class SessionManager:
    """
    Manages transcription sessions for multiple guilds.
    
    Provides methods to start and stop recording, process audio chunks,
    and flush audio buffers to obtain transcriptions.
    """
    def __init__(self) -> None:
        self.sessions: Dict[int, Session] = {}
        threading.Thread(target=self._buffer_flusher, daemon=True).start()
        print("[DEBUG] SessionManager initialized and buffer flusher started.")

    def get_or_create_session(self, guild_id: int) -> Session:
        """
        Retrieve or create a transcription session for a guild.
        
        Args:
            guild_id (int): The Discord guild ID.
        
        Returns:
            Session: The transcription session.
        """
        if guild_id not in self.sessions:
            self.sessions[guild_id] = Session()
            print(f"[DEBUG] Created new session for guild {guild_id}")
        return self.sessions[guild_id]

    def remove_session(self, guild_id: int) -> None:
        """
        Remove the transcription session for a guild.
        
        Args:
            guild_id (int): The Discord guild ID.
        """
        if guild_id in self.sessions:
            del self.sessions[guild_id]
            print(f"[DEBUG] Removed session for guild {guild_id}")

    def start_recording(self, guild_id: int) -> Session:
        """
        Start a transcription session for a guild.
        
        Args:
            guild_id (int): The Discord guild ID.
        
        Returns:
            Session: The started session.
        """
        session = self.get_or_create_session(guild_id)
        session.is_recording = True
        print(f"[DEBUG] Recording started for guild {guild_id}")
        return session

    def stop_recording(self, guild_id: int) -> str:
        """
        Stop recording for a guild and return the full transcript.
        
        Args:
            guild_id (int): The Discord guild ID.
        
        Returns:
            str: The aggregated transcript.
        """
        session = self.get_or_create_session(guild_id)
        session.is_recording = False
        print(f"[DEBUG] Recording stopped for guild {guild_id}")
        for user_id in list(session.audio_buffers.keys()):
            self._flush_buffer(session, user_id)
        transcript = session.get_combined_transcript()
        return transcript

    def process_audio_chunk(self, guild_id: int, user_id: int, pcm_data: bytes) -> None:
        """
        Append a PCM audio chunk to the buffer for a user.
        
        Args:
            guild_id (int): The Discord guild ID.
            user_id (int): The user's ID.
            pcm_data (bytes): Raw PCM audio data.
        """
        session = self.get_or_create_session(guild_id)
        if not session.is_recording:
            print(f"[DEBUG] Received audio chunk for user {user_id}, but recording is not active.")
            return
        session.audio_buffers.setdefault(user_id, bytearray()).extend(pcm_data)
        print(f"[DEBUG] Processed audio chunk for user {user_id}; buffer size now: {len(session.audio_buffers[user_id])} bytes.")

    def set_user_name(self, guild_id: int, user_id: int, display_name: str) -> None:
        """
        Set or update the display name for a user in a session.
        
        Args:
            guild_id (int): The Discord guild ID.
            user_id (int): The user's ID.
            display_name (str): The user's display name.
        """
        session = self.get_or_create_session(guild_id)
        session.user_names[user_id] = display_name
        print(f"[DEBUG] Set display name for user {user_id} to '{display_name}'.")

    def _buffer_flusher(self) -> None:
        """
        Background thread that flushes audio buffers periodically.
        """
        while True:
            for session in self.sessions.values():
                if session.is_recording:
                    for user_id in list(session.audio_buffers.keys()):
                        if session.audio_buffers[user_id]:
                            print(f"[DEBUG] Flushing buffer for user {user_id}; buffer length: {len(session.audio_buffers[user_id])} bytes.")
                            self._flush_buffer(session, user_id)
            time.sleep(2)

    def _flush_buffer(self, session: Session, user_id: int) -> None:
        """
        Flush the audio buffer for a user: convert PCM to WAV and transcribe.
        
        Args:
            session (Session): The transcription session.
            user_id (int): The user's ID.
        """
        buffer_data = bytes(session.audio_buffers.get(user_id, b""))
        print(f"[DEBUG] _flush_buffer: Buffer length for user {user_id}: {len(buffer_data)} bytes.")
        if not buffer_data:
            print(f"[DEBUG] _flush_buffer: No data to flush for user {user_id}.")
            return
        session.audio_buffers[user_id] = bytearray()  # Clear buffer

        pcm_filename = f"/tmp/{uuid.uuid4()}.pcm"
        wav_filename = f"/tmp/{uuid.uuid4()}.wav"
        with open(pcm_filename, "wb") as f:
            f.write(buffer_data)
        try:
            print(f"[DEBUG] _flush_buffer: Converting PCM to WAV for user {user_id}...")
            audio_utils.convert_pcm_to_wav(pcm_filename, wav_filename)
            print(f"[DEBUG] _flush_buffer: Conversion complete for user {user_id}.")
            # Create an AudioToTextRecorder instance using the "tiny" model.
            recorder = AudioToTextRecorder(model="tiny")
            transcript_text = recorder.transcribe_file(wav_filename).strip()
            print(f"[DEBUG] _flush_buffer: Transcribed text for user {user_id}: {transcript_text}")
            session.append_final_line(user_id, transcript_text)
        except Exception as e:
            print(f"[DEBUG] _flush_buffer: Transcription error for user {user_id}: {e}")
        finally:
            if os.path.exists(pcm_filename):
                os.remove(pcm_filename)
            if os.path.exists(wav_filename):
                os.remove(wav_filename)
