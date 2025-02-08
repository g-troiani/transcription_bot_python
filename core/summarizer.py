"""
Summarizer module.

Provides a function to summarize a conversation transcript using OpenAI's ChatCompletion API.
"""

import openai
from core.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def summarize_transcript(transcript: str) -> str:
    """
    Summarize the given conversation transcript using OpenAI's ChatCompletion API.
    
    Args:
        transcript (str): The full conversation transcript.
        
    Returns:
        str: A summarized version of the conversation.
    """
    print("[DEBUG] Summarization started.")
    if not transcript:
        print("[DEBUG] No transcript provided for summarization.")
        return "No conversation to summarize."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations."},
                {"role": "user", "content": f"Summarize the following conversation:\n{transcript}"}
            ],
            temperature=0.5,
            max_tokens=150
        )
        summary = response.choices[0].message.content.strip() if response.choices else "No summary available."
        print(f"[DEBUG] Summarization completed successfully. Summary: {summary}")
        return summary
    except Exception as e:
        print(f"[DEBUG] Error generating summary: {e}")
        return f"Error generating summary: {e}"
