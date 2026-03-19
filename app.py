import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TRANSCRIPTION_FILE = "call.txt"
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
        return jsonify({"answer": "No transcription found. Run LoadAudio.py first."}), 404

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


if __name__ == "__main__":
    app.run(host="localhost", port=8090, debug=True)
