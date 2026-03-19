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
