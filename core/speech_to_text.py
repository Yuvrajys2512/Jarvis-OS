import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from config.settings import (
    WHISPER_MODEL_SIZE,
    WHISPER_LANGUAGE,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
)

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    """Load the Whisper model once and reuse it — loading takes ~3s the first time."""
    global _model
    if _model is None:
        print(f"Loading Whisper '{WHISPER_MODEL_SIZE}' model... (first time only)")
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        print("Whisper ready.")
    return _model


def record_until_silence() -> np.ndarray:
    """
    Record from the mic until the user stops speaking.
    Returns a float32 numpy array of the full audio at 16kHz mono.

    How silence detection works:
    - We record in small 100ms chunks.
    - Each chunk's volume (RMS) is measured.
    - Once volume drops below SILENCE_THRESHOLD for SILENCE_DURATION seconds, we stop.
    - This means JARVIS waits for you to finish your full sentence.
    """
    chunk_duration = 0.1  # seconds per chunk
    chunk_samples = int(AUDIO_SAMPLE_RATE * chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)

    recorded_chunks = []
    silent_chunk_count = 0
    started_speaking = False

    print("Listening...")

    with sd.InputStream(samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, dtype="float32") as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            rms = np.sqrt(np.mean(chunk ** 2))

            if rms > SILENCE_THRESHOLD:
                started_speaking = True
                silent_chunk_count = 0
                recorded_chunks.append(chunk.copy())
            elif started_speaking:
                recorded_chunks.append(chunk.copy())
                silent_chunk_count += 1
                if silent_chunk_count >= silence_chunks_needed:
                    break

    audio = np.concatenate(recorded_chunks, axis=0).flatten()
    return audio


def transcribe(audio: np.ndarray) -> str:
    """Convert a float32 audio array to text using Whisper."""
    model = _get_model()
    segments, _ = model.transcribe(audio, language=WHISPER_LANGUAGE, beam_size=5)
    return " ".join(segment.text.strip() for segment in segments)


def listen_and_transcribe() -> str:
    """Convenience function: record then immediately transcribe."""
    audio = record_until_silence()
    print("Transcribing...")
    return transcribe(audio)
