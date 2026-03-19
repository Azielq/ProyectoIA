import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from LoadAudio import transcribe_audio

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TRANSCRIPTION_FILE = "call.txt"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SYSTEM_PROMPT = (
    "You are a call center analysis assistant. You are given the transcription of a "
    "customer service phone call. Answer the user's questions about the call accurately "
    "and concisely, based only on the transcription. If the information is not in the "
    "transcription, say so. Respond in the same language the user uses to ask the question."
)


def load_transcription():
    if not os.path.exists(TRANSCRIPTION_FILE):
        return None
    with open(TRANSCRIPTION_FILE, "r", encoding="utf-8") as f:
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
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not file.filename.lower().endswith(".mp3"):
        return jsonify({"error": "Only MP3 files are accepted."}), 400

    try:
        save_path = os.path.join(UPLOAD_FOLDER, "uploaded_audio.mp3")
        file.save(save_path)

        transcript = transcribe_audio(save_path, TRANSCRIPTION_FILE)

        os.remove(save_path)

        return jsonify({
            "message": "Transcription complete.",
            "transcript_length": len(transcript),
        })
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File is too large. Maximum size is 50 MB."}), 413


if __name__ == "__main__":
    app.run(host="localhost", port=8090, debug=True)
