import os
import json
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from LoadAudio import transcribe_audio

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

active_transcription = None

SYSTEM_PROMPT = (
    "You are a call center analysis assistant. You are given the transcription of a "
    "customer service phone call. Answer the user's questions about the call accurately "
    "and concisely, based only on the transcription. If the information is not in the "
    "transcription, say so. Respond in the same language the user uses to ask the question."
)


def generate_title(transcript):
    snippet = transcript[:1500]
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.7,
        max_tokens=30,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate a very short title (3-6 words max) in Spanish that describes "
                    "the main topic of this phone call transcript. Reply ONLY with the title, "
                    "no quotes, no punctuation at the end."
                ),
            },
            {"role": "user", "content": snippet},
        ],
    )
    title = response.choices[0].message.content.strip().strip('"').strip(".")
    return title


def load_transcription():
    if not active_transcription:
        return None
    path = os.path.join(UPLOAD_FOLDER, active_transcription)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask")
def ask():
    question = request.args.get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please provide a question."}), 400

    transcription = load_transcription()
    if not transcription:
        return jsonify({"answer": "No transcription found. Upload an audio file first."}), 404

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"TRANSCRIPTION:\n{transcription}\n\n"
                    f"QUESTION:\n{question}"
                ),
            },
        ],
    )

    answer = response.choices[0].message.content
    return jsonify({"answer": answer})


@app.route("/upload", methods=["POST"])
def upload():
    global active_transcription

    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not file.filename.lower().endswith(".mp3"):
        return jsonify({"error": "Only MP3 files are accepted."}), 400

    safe_name = secure_filename(file.filename)
    audio_path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(audio_path)

    def generate():
        global active_transcription

        try:
            def on_progress(current, total, stage):
                event = json.dumps({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "stage": stage,
                })
                return event

            progress_events = []

            def progress_callback(current, total, stage):
                progress_events.append(on_progress(current, total, stage))

            # Send initial event
            yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': 0, 'stage': 'loading'})}\n\n"

            temp_txt = os.path.join(UPLOAD_FOLDER, "_temp_transcript.txt")

            # We need to stream progress, so we use a thread for transcription
            import threading
            result = {}

            def do_transcribe():
                result["transcript"] = transcribe_audio(
                    audio_path, temp_txt, on_progress=progress_callback
                )

            thread = threading.Thread(target=do_transcribe)
            thread.start()

            sent = 0
            while thread.is_alive():
                thread.join(timeout=0.5)
                while sent < len(progress_events):
                    yield f"data: {progress_events[sent]}\n\n"
                    sent += 1

            # Flush remaining progress events
            while sent < len(progress_events):
                yield f"data: {progress_events[sent]}\n\n"
                sent += 1

            if "transcript" not in result:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Transcription failed'})}\n\n"
                return

            transcript = result["transcript"]
            os.remove(audio_path)

            # Generate title
            yield f"data: {json.dumps({'type': 'progress', 'current': 0, 'total': 0, 'stage': 'naming'})}\n\n"
            title = generate_title(transcript)
            txt_name = secure_filename(title) + ".txt"

            final_path = os.path.join(UPLOAD_FOLDER, txt_name)
            counter = 2
            while os.path.exists(final_path):
                txt_name = secure_filename(title) + f"_{counter}.txt"
                final_path = os.path.join(UPLOAD_FOLDER, txt_name)
                counter += 1

            os.rename(temp_txt, final_path)
            active_transcription = txt_name

            yield f"data: {json.dumps({'type': 'done', 'transcript_length': len(transcript), 'filename': txt_name, 'title': title})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/conversations")
def conversations():
    files = []
    for f in os.listdir(UPLOAD_FOLDER):
        if f.lower().endswith(".txt"):
            path = os.path.join(UPLOAD_FOLDER, f)
            files.append({
                "name": f,
                "date": os.path.getmtime(path),
                "active": f == active_transcription,
            })
    files.sort(key=lambda x: x["date"], reverse=True)
    return jsonify(files)


@app.route("/select", methods=["POST"])
def select_conversation():
    global active_transcription

    data = request.get_json()
    if not data or "filename" not in data:
        return jsonify({"error": "No filename provided."}), 400

    filename = data["filename"]
    path = os.path.join(UPLOAD_FOLDER, filename)

    if not filename.endswith(".txt") or not os.path.exists(path):
        return jsonify({"error": "File not found."}), 404

    active_transcription = filename
    return jsonify({"message": f"Conversation '{filename}' selected.", "filename": filename})


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File is too large. Maximum size is 50 MB."}), 413


if __name__ == "__main__":
    app.run(host="localhost", port=8090, debug=True)
