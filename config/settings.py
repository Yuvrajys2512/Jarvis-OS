import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# --- Speech-to-Text ---
# Model size tradeoff: tiny=fastest/least accurate, large-v3=slowest/most accurate
# "base" is a good starting point for a personal machine
WHISPER_MODEL_SIZE = "base"
WHISPER_LANGUAGE = "en"

# --- Text-to-Speech ---
# edge-tts voice. Options close to Jarvis:
#   "en-GB-RyanNeural"   ← British male, closest to Jarvis (recommended)
#   "en-US-GuyNeural"    ← American male, deeper
#   "en-GB-ThomasNeural" ← British male, more formal
TTS_VOICE = "en-GB-RyanNeural"
TTS_RATE = "+0%"    # speaking speed: "-10%" slower, "+10%" faster
TTS_PITCH = "-5Hz"  # slight pitch down for a more authoritative tone

# --- Wake Word ---
WAKE_WORD_MODEL = "hey jarvis"   # OpenWakeWord model name
WAKE_WORD_THRESHOLD = 0.5        # 0.0–1.0, higher = less false triggers

# --- Vision ---
WEBCAM_INDEX = 0  # 0 is usually the built-in/default webcam

# --- Gemini ---
GEMINI_MODEL = "gemini-2.0-flash"

# --- Audio ---
AUDIO_SAMPLE_RATE = 16000   # Hz, Whisper expects 16kHz
AUDIO_CHANNELS = 1          # mono
SILENCE_THRESHOLD = 0.01    # amplitude below this = silence
SILENCE_DURATION = 1.5      # seconds of silence before stopping recording
