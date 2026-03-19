import os
import io
from dotenv import load_dotenv
from pydub import AudioSegment
from google.cloud import speech

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/google-service-account.json"
)

AUDIO_FILE = "llamada.mp3"
OUTPUT_FILE = "call.txt"
CHUNK_LENGTH_MS = 55_000  # 55 seconds per chunk (under 1-min sync limit)


def transcribe():
    print(f"Loading {AUDIO_FILE} ...")
    audio = AudioSegment.from_mp3(AUDIO_FILE)
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    total_ms = len(audio)
    print(f"Duration: {total_ms / 1000:.1f}s — splitting into chunks of {CHUNK_LENGTH_MS / 1000:.0f}s")

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="es-ES",
        enable_automatic_punctuation=True,
    )

    full_transcript = []
    chunk_index = 0

    for start_ms in range(0, total_ms, CHUNK_LENGTH_MS):
        chunk = audio[start_ms : start_ms + CHUNK_LENGTH_MS]
        chunk_index += 1

        buf = io.BytesIO()
        chunk.export(buf, format="wav")
        content = buf.getvalue()

        request_audio = speech.RecognitionAudio(content=content)
        print(f"  Chunk {chunk_index} ({start_ms / 1000:.0f}s–{min(start_ms + CHUNK_LENGTH_MS, total_ms) / 1000:.0f}s) — sending to Google Speech-to-Text ...")

        response = client.recognize(config=config, audio=request_audio)

        chunk_text = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        if chunk_text:
            full_transcript.append(chunk_text)
            print(f"    ✓ Got {len(chunk_text)} chars")
        else:
            print(f"    — No speech detected")

    transcript = " ".join(full_transcript)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"\nDone! Transcript written to {OUTPUT_FILE} ({len(transcript)} chars)")


if __name__ == "__main__":
    transcribe()
