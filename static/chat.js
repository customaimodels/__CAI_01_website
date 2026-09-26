(function () {
  const API_URL = "/api/chat";
  const SESSION_KEY = "cai_chat_session_id";

  let sessionId = window.localStorage.getItem(SESSION_KEY) || null;
  // In-memory conversation history sent to the backend (excludes the
  // hardcoded greeting). Page refresh starts a fresh conversation.
  const history = [];

  function createElement(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function buildChatUI() {
    const root = createElement("div", "cai-chat-root");

    // Launcher button
    const launcher = createElement("button", "cai-chat-launcher");
    launcher.setAttribute("aria-label", "Open the CAI assistant");
    launcher.innerHTML =
      '<svg class="cai-launcher-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">' +
      '<path d="M12 3C7.03 3 3 6.58 3 11c0 2.05.87 3.92 2.3 5.34-.18 1.17-.65 2.31-1.51 3.16-.18.18-.05.5.21.5 1.87 0 3.42-.7 4.5-1.4 1.08.39 2.27.6 3.5.6 4.97 0 9-3.58 9-8s-4.03-8-9-8z" fill="currentColor"/>' +
      "</svg>" +
      '<span class="cai-launcher-label">Ask my AI</span>' +
      '<span class="cai-launcher-dot" aria-hidden="true"></span>';
    root.appendChild(launcher);

    // Chat window
    const win = createElement("div", "cai-chat-window");

    const header = createElement("div", "cai-chat-header");
    const title = createElement("div", "cai-chat-title", "Custom AI Models");
    const subtitle = createElement(
      "div",
      "cai-chat-subtitle",
      "Describe your use case — get a quick assessment."
    );
    const closeBtn = createElement("button", "cai-chat-close", "×");
    header.appendChild(title);
    header.appendChild(subtitle);
    header.appendChild(closeBtn);

    const messages = createElement("div", "cai-chat-messages");

    const suggestions = createElement("div", "cai-chat-suggestions");
    const suggestionTexts = [
      "Assess my use case",
      "Show me proof",
      "Work with me",
    ];
    suggestionTexts.forEach((label) => {
      const btn = createElement("button", "cai-chat-suggestion", label);
      btn.addEventListener("click", () => {
        sendUserMessage(label);
      });
      suggestions.appendChild(btn);
    });

    const form = createElement("form", "cai-chat-form");
    const input = createElement("textarea", "cai-chat-input");
    input.rows = 1;
    input.placeholder =
      "Ask about services, proof, or how to start. Shift+Enter for newline.";
    const sendBtn = createElement("button", "cai-chat-send", "Send");
    form.appendChild(input);
    form.appendChild(sendBtn);

    win.appendChild(header);
    win.appendChild(messages);
    win.appendChild(suggestions);
    win.appendChild(form);
    root.appendChild(win);

    document.body.appendChild(root);

    // Behavior
    function toggleWindow(open) {
      if (open) {
        win.classList.add("cai-chat-window-open");
        launcher.classList.add("cai-launcher-hidden");
        input.focus();
      } else {
        win.classList.remove("cai-chat-window-open");
        launcher.classList.remove("cai-launcher-hidden");
      }
    }

    launcher.addEventListener("click", () => toggleWindow(true));
    closeBtn.addEventListener("click", () => toggleWindow(false));

    // Any page element with [data-open-chat] opens the widget
    // (e.g. the "Describe Your Use Case" CTAs).
    document.addEventListener("click", (evt) => {
      const trigger = evt.target.closest("[data-open-chat]");
      if (trigger) {
        evt.preventDefault();
        toggleWindow(true);
        input.focus();
      }
    });

    function appendMessage(role, text) {
      const bubble = createElement(
        "div",
        role === "user" ? "cai-chat-bubble cai-chat-bubble-user" : "cai-chat-bubble cai-chat-bubble-bot"
      );
      bubble.textContent = text;
      messages.appendChild(bubble);
      messages.scrollTop = messages.scrollHeight;
    }

    function setInputDisabled(disabled) {
      input.disabled = disabled;
      sendBtn.disabled = disabled;
    }

    async function sendUserMessage(text) {
      const trimmed = (text || "").trim();
      if (!trimmed) return;

      appendMessage("user", trimmed);
      input.value = "";
      setInputDisabled(true);

      try {
        const res = await fetch(API_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: trimmed,
            history: history.slice(-12),
          }),
        });

        if (!res.ok) {
          appendMessage(
            "bot",
            "I hit an error processing that. Please try again in a moment."
          );
          return;
        }

        const data = await res.json();
        if (data.session_id) {
          sessionId = data.session_id;
          window.localStorage.setItem(SESSION_KEY, sessionId);
        }
        // Surface fallback mode in the header so visitors know answers may be brief
        if (data.llm_available === false) {
          subtitle.textContent = "Running on backup brain — answers may be brief.";
        } else {
          subtitle.textContent = "Describe your use case — get a quick assessment.";
        }
        if (data.reply) {
          appendMessage("bot", data.reply);
          history.push({ role: "user", content: trimmed });
          history.push({ role: "assistant", content: data.reply });
        } else {
          appendMessage(
            "bot",
            "I didn't get a clear reply from my brain. Please try again."
          );
        }
      } catch (e) {
        appendMessage(
          "bot",
          "My AI brain is currently unavailable. Try again shortly or use the contact form."
        );
      } finally {
        setInputDisabled(false);
        input.focus();
      }
    }

    form.addEventListener("submit", (evt) => {
      evt.preventDefault();
      sendUserMessage(input.value);
    });

    input.addEventListener("keydown", (evt) => {
      if (evt.key === "Enter" && !evt.shiftKey) {
        evt.preventDefault();
        form.dispatchEvent(new Event("submit"));
      }
    });

    // Initial system message
    appendMessage(
      "bot",
      "I'm the AI assistant for Custom AI Models (CAI). Describe what's slow, "
        + "manual, or messy in your business and I'll give you a quick assessment "
        + "of what an AI system could do about it — or click \"Work with me\" to "
        + "start a project."
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildChatUI);
  } else {
    buildChatUI();
  }
})();
