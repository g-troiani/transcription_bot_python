"""
Audio utilities module.

Provides helper functions for converting raw PCM audio to WAV format.
"""

import subprocess

def convert_pcm_to_wav(pcm_file: str, wav_file: str) -> None:
    """
    Convert a raw PCM file to a WAV file using FFmpeg.
    
    Args:
        pcm_file (str): Path to the input PCM file.
        wav_file (str): Path to the output WAV file.
    """
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "s16le",
        "-ar", "48000",
        "-ac", "1",
        "-i", pcm_file,
        wav_file
    ], check=True)
