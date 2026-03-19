const fileInput = document.getElementById("audio-file");
const uploadBtn = document.getElementById("upload-btn");
const fileNameSpan = document.getElementById("file-name");
const uploadStatus = document.getElementById("upload-status");
const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("question");

function addBubble(text, className) {
    const div = document.createElement("div");
    div.className = "bubble " + className;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
}

// === Upload handling ===
fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        fileNameSpan.textContent = fileInput.files[0].name;
        uploadBtn.disabled = false;
    } else {
        fileNameSpan.textContent = "Selecciona un archivo MP3...";
        uploadBtn.disabled = true;
    }
});

uploadBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".mp3")) {
        uploadStatus.textContent = "Por favor selecciona un archivo MP3.";
        uploadStatus.className = "upload-status error";
        return;
    }

    uploadBtn.disabled = true;
    fileInput.disabled = true;
    input.disabled = true;
    form.querySelector("button").disabled = true;

    uploadStatus.textContent = "Subiendo y transcribiendo... Esto puede tardar un momento para grabaciones largas.";
    uploadStatus.className = "upload-status processing";

    try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/upload", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();

        if (res.ok) {
            uploadStatus.textContent =
                `Transcripcion completada (${data.transcript_length} caracteres). Ya puedes hacer preguntas sobre la llamada.`;
            uploadStatus.className = "upload-status success";
            addBubble("Archivo de audio transcrito exitosamente. Preguntame lo que quieras sobre la llamada.", "assistant");
        } else {
            uploadStatus.textContent = data.error || "Error al subir el archivo.";
            uploadStatus.className = "upload-status error";
        }
    } catch (err) {
        uploadStatus.textContent = "Error de conexion: " + err.message;
        uploadStatus.className = "upload-status error";
    } finally {
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        input.disabled = false;
        form.querySelector("button").disabled = false;
    }
});

// === Chat handling ===
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    addBubble(question, "user");
    input.value = "";
    input.disabled = true;
    form.querySelector("button").disabled = true;

    const loading = addBubble("Thinking...", "loading");

    try {
        const res = await fetch("/ask?question=" + encodeURIComponent(question));
        const data = await res.json();
        loading.remove();

        if (res.ok) {
            addBubble(data.answer, "assistant");
        } else {
            addBubble(data.answer || "An error occurred.", "error");
        }
    } catch (err) {
        loading.remove();
        addBubble("Connection error: " + err.message, "error");
    } finally {
        input.disabled = false;
        form.querySelector("button").disabled = false;
        input.focus();
    }
});
