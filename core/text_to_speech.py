import asyncio
import io
import numpy as np
import sounddevice as sd
import edge_tts
import av
from config.settings import TTS_VOICE, TTS_RATE, TTS_PITCH


def speak(text: str) -> None:
    """Speak text aloud. Blocks until the audio finishes playing."""
    asyncio.run(_speak_async(text))


async def speak_async(text: str) -> None:
    """Same as speak() but for use inside an already-running async context."""
    await _speak_async(text)


async def _speak_async(text: str) -> None:
    audio, sample_rate = await _synthesize(text)
    if audio.size == 0:
        return
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


async def _synthesize(text: str) -> tuple[np.ndarray, int]:
    # Step 1: Ask edge-tts to stream the audio in MP3 chunks
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE, pitch=TTS_PITCH)
    mp3_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_data += chunk["data"]

    if not mp3_data:
        return np.array([]), 24000

    # Step 2: Decode the MP3 bytes into raw PCM samples using PyAV (FFmpeg wrapper)
    buf = io.BytesIO(mp3_data)
    frames = []
    sample_rate = 24000

    with av.open(buf, format="mp3") as container:
        audio_stream = container.streams.audio[0]
        sample_rate = audio_stream.sample_rate
        for frame in container.decode(audio_stream):
            frames.append(frame.to_ndarray())

    if not frames:
        return np.array([]), sample_rate

    # Step 3: Stack all frames into a single array shaped (total_samples, channels)
    audio = np.concatenate(frames, axis=1).T

    # Step 4: Convert int16 → float32 so sounddevice can play it
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0

    return audio, sample_rate
