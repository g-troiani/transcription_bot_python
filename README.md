# Transcription Bot

A Python bot that transcribes audio files to text using OpenAI's Whisper API.

## Requirements
- Python 3.x
- OpenAI API key
- ffmpeg
- Discord Bot Token

## Installation

# Clone the repository
git clone https://github.com/g-troiani/transcription_bot_python.git
cd transcription_bot_python

# Install dependencies
pip install -r requirements.txt

## Setup
1. Create a `.env` file in the project root
2. Add your environment variables:

OPENAI_API_KEY=your_api_key_here
DISCORD_TOKEN=your_discord_token_here
GUILD_ID=your_guild_id_here
APPLICATION_ID=your_application_id_here

## Running the Bot

# Standard start
python main_discord.py

# If on Linux and encountering issues
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6
python main_discord.py

## Discord Commands
- `/transcribe` - Transcribe an attached audio file
- `/help` - Display available commands
- `/ping` - Check if bot is responsive

## Supported Audio Formats
- mp3
- mp4
- mpeg
- mpga
- m4a
- wav
- webm

## Error Handling
- Ensure your audio file exists and is in a supported format
- Verify your API key and Discord tokens are correctly set in the `.env` file
- Check your internet connection if transcription fails
- Make sure the bot has proper permissions in your Discord server

## License
MIT

## Contributing
Pull requests are welcome. For major changes, please open an issue first.


