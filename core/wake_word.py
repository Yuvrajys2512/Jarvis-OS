import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from config.settings import AUDIO_SAMPLE_RATE

CHUNK_DURATION = 2.0  # seconds per listening chunk

_tiny_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    """
    Reuse the 'base' Whisper model — already downloaded in Phase 3, no internet needed.
    """
    global _tiny_model
    if _tiny_model is None:
        print("Loading wake word model...")
        _tiny_model = WhisperModel("base", device="cpu", compute_type="int8")
        print("Wake word model ready.")
    return _tiny_model


def wait_for_wake_word() -> None:
    """
    Block until the user says 'Jarvis'.

    How it works:
    - Records a fixed 2-second audio chunk from the mic
    - Transcribes it with the tiny Whisper model (~300ms on CPU)
    - If the word 'jarvis' appears anywhere in the transcription → trigger
    - Otherwise → discard and record the next chunk
    Total worst-case latency: ~2.3 seconds from when you say 'Jarvis'
    """
    model = _get_model()
    chunk_samples = int(AUDIO_SAMPLE_RATE * CHUNK_DURATION)

    print("Waiting for 'Jarvis'...")

    while True:
        audio = sd.rec(chunk_samples, samplerate=AUDIO_SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        audio = audio.flatten()

        # beam_size=1 = greedy decoding, fastest possible transcription
        segments, _ = model.transcribe(audio, language="en", beam_size=1)
        text = " ".join(s.text for s in segments).lower()

        if "jarvis" in text:
            _play_activation_tone()
            return


def _play_activation_tone() -> None:
    """
    Two rising tones as instant confirmation that JARVIS heard the wake word.
    Pure numpy — no audio files, no TTS delay.
    """
    sample_rate = 22050
    duration = 0.12

    def make_tone(freq: float) -> np.ndarray:
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * freq * t).astype(np.float32)
        return tone * np.linspace(1.0, 0.0, len(tone)) * 0.4

    beep = np.concatenate([make_tone(880), make_tone(1320)])
    sd.play(beep, samplerate=sample_rate)
    sd.wait()
