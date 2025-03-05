from elevenlabs import get_voices
import os
from dotenv import load_dotenv
from openai import OpenAI
from elevenlabs.client import ElevenLabs

load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = ElevenLabs(apikey=os.getenv("ELEVENLABS_API_KEY"))

voices = get_voices()
for voice in voices:
    print(f"ID: {voice.id}, Name: {voice.name}")