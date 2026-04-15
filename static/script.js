// === DOM Elements ===
const fileInput = document.getElementById("audio-file");
const uploadBtn = document.getElementById("upload-btn");
const fileNameSpan = document.getElementById("file-name");
const uploadStatus = document.getElementById("upload-status");
const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const welcome = document.getElementById("welcome");
const chatArea = document.getElementById("chat-area");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");
const topbarToggle = document.getElementById("topbar-toggle");
const sidebarOverlay = document.getElementById("sidebar-overlay");
const conversationList = document.getElementById("conversation-list");
const conversationEmpty = document.getElementById("conversation-empty");
const newChatBtn = document.getElementById("new-chat-btn");
const dropArea = document.getElementById("drop-area");
const topbarTitle = document.getElementById("topbar-title");

// === Chat bubbles ===
function addBubble(text, className) {
    const div = document.createElement("div");
    div.className = "bubble " + className;
    div.textContent = text;
    messages.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
    return div;
}

function showChat() {
    welcome.classList.add("hidden");
}

function showWelcome() {
    welcome.classList.remove("hidden");
    messages.innerHTML = "";
}

// === Sidebar toggle ===
function isMobile() {
    return window.innerWidth <= 768;
}

function openSidebar() {
    sidebar.classList.remove("collapsed");
    sidebar.classList.add("open");
    sidebarOverlay.classList.add("visible");
}

function closeSidebar() {
    sidebar.classList.add("collapsed");
    sidebar.classList.remove("open");
    sidebarOverlay.classList.remove("visible");
}

function toggleSidebar() {
    if (sidebar.classList.contains("collapsed")) {
        openSidebar();
    } else {
        closeSidebar();
    }
}

sidebarToggle.addEventListener("click", toggleSidebar);
topbarToggle.addEventListener("click", toggleSidebar);
sidebarOverlay.addEventListener("click", closeSidebar);

// === Conversations ===
async function loadConversations() {
    try {
        const res = await fetch("/conversations");
        const data = await res.json();

        conversationList.innerHTML = "";

        if (data.length === 0) {
            const empty = document.createElement("div");
            empty.className = "conversation-empty";
            empty.textContent = "Sin conversaciones aun";
            conversationList.appendChild(empty);
            return;
        }

        data.forEach((conv) => {
            const btn = document.createElement("button");
            btn.className = "conversation-item" + (conv.active ? " active" : "");
            btn.innerHTML =
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
                '</svg>' +
                '<span class="conversation-item-text">' + conv.name.replace(".txt", "") + '</span>';
            btn.addEventListener("click", () => selectConversation(conv.name));
            conversationList.appendChild(btn);
        });
    } catch (err) {
        // silently ignore
    }
}

async function selectConversation(filename) {
    try {
        const res = await fetch("/select", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename }),
        });

        if (res.ok) {
            messages.innerHTML = "";
            showChat();
            addBubble("Conversacion '" + filename.replace(".txt", "") + "' cargada. Preguntame lo que quieras sobre esta llamada.", "assistant");
            topbarTitle.textContent = filename.replace(".txt", "");
            await loadConversations();
            closeSidebar();
        }
    } catch (err) {
        addBubble("Error al cargar la conversacion.", "error");
    }
}

newChatBtn.addEventListener("click", () => {
    showWelcome();
    uploadStatus.textContent = "";
    uploadStatus.className = "upload-status";
    fileNameSpan.textContent = "Arrastra un archivo MP3 o haz clic para seleccionar";
    fileNameSpan.classList.remove("has-file");
    uploadBtn.disabled = true;
    topbarTitle.textContent = "Call Center AI";
    closeSidebar();
});

// === Drag & Drop ===
dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("dragover");
});

dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("dragover");
});

dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file && file.name.toLowerCase().endsWith(".mp3")) {
        fileInput.files = e.dataTransfer.files;
        fileNameSpan.textContent = file.name;
        fileNameSpan.classList.add("has-file");
        uploadBtn.disabled = false;
    }
});

// === File selection ===
fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        fileNameSpan.textContent = fileInput.files[0].name;
        fileNameSpan.classList.add("has-file");
        uploadBtn.disabled = false;
    } else {
        fileNameSpan.textContent = "Arrastra un archivo MP3 o haz clic para seleccionar";
        fileNameSpan.classList.remove("has-file");
        uploadBtn.disabled = true;
    }
});

// === Upload with real progress ===
function formatTime(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? m + "m " + s + "s" : s + "s";
}

const STAGE_LABELS = {
    loading:      "Preparando audio",
    transcribing: "Transcribiendo",
    naming:       "Generando nombre",
};

function buildLoader() {
    uploadStatus.className = "upload-status";
    uploadStatus.innerHTML = `
        <div class="ai-loader">
            <span class="ai-loader-label" id="loader-label">Preparando audio</span>
            <div class="ai-loader-dots">
                <span></span><span></span><span></span>
            </div>
            <div class="ai-loader-track idle" id="loader-track">
                <div class="ai-loader-fill" id="loader-fill"></div>
            </div>
            <span class="ai-loader-pct" id="loader-pct"></span>
        </div>`;
}

function updateProgress(current, total, stage) {
    const labelEl = document.getElementById("loader-label");
    const trackEl = document.getElementById("loader-track");
    const fillEl  = document.getElementById("loader-fill");
    const pctEl   = document.getElementById("loader-pct");
    if (!labelEl) return;

    if (stage === "loading") {
        labelEl.textContent = STAGE_LABELS.loading;
        trackEl.classList.add("idle");
        fillEl.classList.remove("active");
        pctEl.classList.remove("visible");
    } else if (stage === "transcribing") {
        const pct = Math.round((current / total) * 100);
        labelEl.textContent = STAGE_LABELS.transcribing + "  " + current + " / " + total;
        trackEl.classList.remove("idle");
        fillEl.style.width = pct + "%";
        fillEl.classList.add("active");
        pctEl.textContent = pct + "%";
        pctEl.classList.add("visible");
    } else if (stage === "naming") {
        labelEl.textContent = STAGE_LABELS.naming;
        trackEl.classList.remove("idle");
        fillEl.style.width = "98%";
        fillEl.classList.add("active");
        pctEl.classList.remove("visible");
    }
}

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
    document.getElementById("send-btn").disabled = true;

    buildLoader();
    const startTime = Date.now();

    try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("/upload", { method: "POST", body: formData });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;

                try {
                    const event = JSON.parse(jsonStr);

                    if (event.type === "progress") {
                        updateProgress(event.current, event.total, event.stage);
                    } else if (event.type === "done") {
                        finalData = event;
                    } else if (event.type === "error") {
                        throw new Error(event.error);
                    }
                } catch (parseErr) {
                    if (parseErr.message !== jsonStr) throw parseErr;
                }
            }
        }

        if (finalData) {
            const totalSecs = Math.floor((Date.now() - startTime) / 1000);
            const title = finalData.title || file.name.replace(".mp3", "");

            uploadStatus.textContent = "Completado en " + formatTime(totalSecs) + " (" + finalData.transcript_length + " caracteres)";
            uploadStatus.className = "upload-status success";

            showChat();
            messages.innerHTML = "";
            addBubble("Audio transcrito exitosamente. Preguntame lo que quieras sobre la llamada.", "assistant");
            topbarTitle.textContent = title;
            await loadConversations();
        } else {
            uploadStatus.textContent = "Error: no se recibio respuesta del servidor.";
            uploadStatus.className = "upload-status error";
        }
    } catch (err) {
        uploadStatus.textContent = "Error: " + err.message;
        uploadStatus.className = "upload-status error";
    } finally {
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        input.disabled = false;
        document.getElementById("send-btn").disabled = false;
    }
});

// === Chat ===
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    showChat();
    addBubble(question, "user");
    input.value = "";
    input.disabled = true;
    document.getElementById("send-btn").disabled = true;

    const loading = document.createElement("div");
    loading.className = "bubble loading";
    loading.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(loading);
    chatArea.scrollTop = chatArea.scrollHeight;

    try {
        const res = await fetch("/ask?question=" + encodeURIComponent(question));
        const data = await res.json();
        loading.remove();

        if (res.ok) {
            addBubble(data.answer, "assistant");
        } else {
            addBubble(data.answer || "Ocurrio un error.", "error");
        }
    } catch (err) {
        loading.remove();
        addBubble("Error de conexion: " + err.message, "error");
    } finally {
        input.disabled = false;
        document.getElementById("send-btn").disabled = false;
        input.focus();
    }
});

// === Init ===
loadConversations();
