// ===============================
// CHILILI AI Assistant - Database Connected
// ===============================

const aiToggle = document.getElementById("aiToggle");
const aiPanel = document.getElementById("aiPanel");
const aiClose = document.getElementById("aiClose");

const aiForm = document.getElementById("aiForm");
const aiInput = document.getElementById("aiInput");
const aiMessages = document.getElementById("aiMessages");

const quickButtons = document.querySelectorAll(".assistant-actions button");


// -------------------------------
// Open / Close Assistant
// -------------------------------

if (aiToggle && aiPanel) {
    aiToggle.addEventListener("click", () => {
        aiPanel.classList.toggle("open");
    });
}

if (aiClose && aiPanel) {
    aiClose.addEventListener("click", () => {
        aiPanel.classList.remove("open");
    });
}


// -------------------------------
// Add Chat Bubble
// -------------------------------

function addMessage(text, sender = "bot") {
    if (!aiMessages) return;

    const message = document.createElement("div");
    message.className = `ai-message ${sender}`;
    message.textContent = text;

    aiMessages.appendChild(message);
    aiMessages.scrollTop = aiMessages.scrollHeight;
}


// -------------------------------
// Ask Backend AI Route
// -------------------------------

async function askAssistant(question) {
    if (!question.trim()) return;

    addMessage(question, "user");

    if (aiInput) {
        aiInput.value = "";
    }

    addMessage("Thinking...", "bot");

    try {
        const response = await fetch("/ai-assistant", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        const botMessages = document.querySelectorAll(".ai-message.bot");
        const lastBotMessage = botMessages[botMessages.length - 1];

        if (lastBotMessage && lastBotMessage.textContent === "Thinking...") {
            lastBotMessage.textContent = data.reply;
        } else {
            addMessage(data.reply, "bot");
        }

    } catch (error) {
        const botMessages = document.querySelectorAll(".ai-message.bot");
        const lastBotMessage = botMessages[botMessages.length - 1];

        if (lastBotMessage && lastBotMessage.textContent === "Thinking...") {
            lastBotMessage.textContent = "Sorry, I could not connect to the assistant right now.";
        } else {
            addMessage("Sorry, I could not connect to the assistant right now.", "bot");
        }
    }
}


// -------------------------------
// Quick Buttons
// -------------------------------

quickButtons.forEach(button => {
    button.addEventListener("click", () => {
        const question = button.dataset.question;
        askAssistant(question);
    });
});


// -------------------------------
// User Input
// -------------------------------

if (aiForm) {
    aiForm.addEventListener("submit", function (e) {
        e.preventDefault();

        const question = aiInput.value.trim();

        if (question === "") return;

        askAssistant(question);
    });
}


// -------------------------------
// Welcome Message
// -------------------------------

window.addEventListener("load", () => {
    setTimeout(() => {
        addMessage("👋 Welcome back! I'm your CHILILI AI Assistant. Ask me anything about your wallet, transactions, spending or notifications.");
    }, 800);
});