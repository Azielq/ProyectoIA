import os
import io
from dotenv import load_dotenv
from pydub import AudioSegment
from google.cloud import speech

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "credentials/google-service-account.json"
)

CHUNK_LENGTH_MS = 55_000  # 55 seconds per chunk (under 1-min sync limit)


def transcribe_audio(audio_source, output_file="call.txt"):
    if isinstance(audio_source, str):
        audio = AudioSegment.from_mp3(audio_source)
    elif hasattr(audio_source, "read"):
        audio = AudioSegment.from_mp3(audio_source)
    else:
        raise ValueError("audio_source must be a file path or file-like object")

    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
    total_ms = len(audio)

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="es-ES",
        enable_automatic_punctuation=True,
    )

    full_transcript = []

    for start_ms in range(0, total_ms, CHUNK_LENGTH_MS):
        chunk = audio[start_ms : start_ms + CHUNK_LENGTH_MS]

        buf = io.BytesIO()
        chunk.export(buf, format="wav")
        content = buf.getvalue()

        request_audio = speech.RecognitionAudio(content=content)
        response = client.recognize(config=config, audio=request_audio)

        chunk_text = " ".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        if chunk_text:
            full_transcript.append(chunk_text)

    transcript = " ".join(full_transcript)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(transcript)

    return transcript


def transcribe():
    print(f"Loading llamada.mp3 ...")
    audio = AudioSegment.from_mp3("llamada.mp3")
    total_ms = len(audio)
    print(f"Duration: {total_ms / 1000:.1f}s — splitting into chunks of {CHUNK_LENGTH_MS / 1000:.0f}s")

    result = transcribe_audio("llamada.mp3", "call.txt")
    print(f"Done! Transcript written to call.txt ({len(result)} chars)")


if __name__ == "__main__":
    transcribe()
