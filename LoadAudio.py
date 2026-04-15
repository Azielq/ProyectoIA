import os
import io
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from pydub import AudioSegment
from google.cloud import speech

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/google-service-account.json"
)

CHUNK_LENGTH_MS = 55_000  # 55 seconds per chunk (under 1-min sync limit)
MAX_WORKERS = 5           # parallel API requests


def transcribe_audio(audio_source, output_file="call.txt", on_progress=None):
    if isinstance(audio_source, str):
        audio = AudioSegment.from_mp3(audio_source)
    elif hasattr(audio_source, "read"):
        audio = AudioSegment.from_mp3(audio_source)
    else:
        raise ValueError("audio_source must be a file path or file-like object")

    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    total_ms = len(audio)
    total_chunks = math.ceil(total_ms / CHUNK_LENGTH_MS)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="es-ES",
        enable_automatic_punctuation=True,
    )

    # Prepare all chunks as WAV bytes upfront
    chunks_data = []
    for start_ms in range(0, total_ms, CHUNK_LENGTH_MS):
        chunk = audio[start_ms : start_ms + CHUNK_LENGTH_MS]
        buf = io.BytesIO()
        chunk.export(buf, format="wav")
        chunks_data.append(buf.getvalue())

    # Transcribe a single chunk (called from thread pool)
    def transcribe_chunk(index, content):
        client = speech.SpeechClient()
        request_audio = speech.RecognitionAudio(content=content)
        response = client.recognize(config=config, audio=request_audio)
        text = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        return index, text

    # Process chunks in parallel
    results = [None] * total_chunks
    completed = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(transcribe_chunk, i, data): i
            for i, data in enumerate(chunks_data)
        }

        for future in as_completed(futures):
            idx, text = future.result()
            results[idx] = text

            with lock:
                completed += 1
                if on_progress:
                    on_progress(completed, total_chunks, "transcribing")

    transcript = " ".join(t for t in results if t)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcript)

    return transcript


def transcribe():
    import sys

    audio_file = sys.argv[1] if len(sys.argv) > 1 else "llamada.mp3"
    output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(audio_file)[0] + ".txt"

    print(f"Loading {audio_file} ...")
    audio = AudioSegment.from_mp3(audio_file)
    total_ms = len(audio)
    print(f"Duration: {total_ms / 1000:.1f}s — splitting into chunks of {CHUNK_LENGTH_MS / 1000:.0f}s")

    result = transcribe_audio(audio_file, output_file)
    print(f"Done! Transcript written to {output_file} ({len(result)} chars)")


if __name__ == "__main__":
    transcribe()
