(function () {
  // No network. Every answer is written here, in the page — nothing is sent,
  // nothing is stored. The live assistant comes back later behind the server.
  //
  // Edit the copy below freely: `q` is the bubble, `a` is the answer, and an
  // optional `cta` adds a button under it.
  const SCOPE_MAIL =
    "mailto:customaimodels@gmail.com?subject=Scope%20call%3A%20Custom%20AI%20Models";

  const QA = [
    {
      q: "What do you build?",
      a: "Copilots, decision support, monitoring, data products.\nThings that run in production, not demos.",
    },
    {
      q: "Who is this for?",
      a: "Operators and founders with a concrete problem: decisions are slow, work is manual, data sits unused.",
    },
    {
      q: "What is Cascade Araña?",
      a: "A chain of AI loops that wake on real events — a missed call, a quiet quote, a new review — do the work, and wait for your YES.\nEvery stage checks its own work.",
    },
    {
      q: "Show me proof",
      a: "8.5 years shipping production ML and AI.\n500+ locations under anomaly detection.\n~50 dealers on one quoting platform.\n100+ live signal features.\n\nNamed with permission, described under NDA.",
    },
    {
      q: "Who builds it?",
      a: "One engineer, end to end. Design, data, models, deployment.\nNo handoffs.",
    },
    {
      q: "How does a project run?",
      a: "Scope call. Fixed-phase plan, fixed quote.\n50% deposit — scope locks.\nWeekly review.\nBalance on delivery.\nThen the next phase, or a clean handover.",
    },
    {
      q: "What does it cost?",
      a: "Every quote is tied to one problem, a phase plan, named deliverables. Fixed, per phase.\nThe number comes after the scope call.",
      cta: { label: "Book a scope call", href: SCOPE_MAIL },
    },
    {
      q: "How do we start?",
      a: "Bring one concrete problem. We scope it together.",
      cta: { label: "Book a scope call", href: SCOPE_MAIL },
    },
  ];

  const GREETING = "The eight questions people ask first. Pick one.";

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
    win.setAttribute("role", "dialog");
    win.setAttribute("aria-label", "Custom AI Models — questions");

    const header = createElement("div", "cai-chat-header");
    const headText = createElement("div", "cai-chat-headtext");
    headText.appendChild(createElement("div", "cai-chat-title", "Custom AI Models"));
    headText.appendChild(createElement("div", "cai-chat-subtitle", "Pick a question."));
    const closeBtn = createElement("button", "cai-chat-close", "×");
    closeBtn.setAttribute("aria-label", "Close");
    header.appendChild(headText);
    header.appendChild(closeBtn);

    const messages = createElement("div", "cai-chat-messages");
    messages.setAttribute("aria-live", "polite");

    const questions = createElement("div", "cai-chat-questions");
    QA.forEach((item) => {
      const btn = createElement("button", "cai-chat-q", item.q);
      btn.type = "button";
      btn.addEventListener("click", () => ask(item, btn));
      questions.appendChild(btn);
    });

    const footer = createElement("div", "cai-chat-footer");
    footer.appendChild(document.createTextNode("Something else? "));
    const mail = createElement("a", "cai-chat-footer__link", "Email Yeriko");
    mail.href = "mailto:customaimodels@gmail.com";
    footer.appendChild(mail);

    win.appendChild(header);
    win.appendChild(messages);
    win.appendChild(questions);
    win.appendChild(footer);
    root.appendChild(win);

    document.body.appendChild(root);

    // Behavior
    function toggleWindow(open) {
      win.classList.toggle("cai-chat-window-open", open);
      launcher.classList.toggle("cai-launcher-hidden", open);
      if (open) (questions.querySelector(".cai-chat-q") || closeBtn).focus();
    }

    launcher.addEventListener("click", () => toggleWindow(true));
    closeBtn.addEventListener("click", () => toggleWindow(false));
    document.addEventListener("keydown", (evt) => {
      if (evt.key === "Escape") toggleWindow(false);
    });

    // Any page element with [data-open-chat] opens the widget
    // (e.g. the "Describe Your Use Case" CTAs).
    document.addEventListener("click", (evt) => {
      const trigger = evt.target.closest("[data-open-chat]");
      if (trigger) {
        evt.preventDefault();
        toggleWindow(true);
      }
    });

    function scrollDown() {
      messages.scrollTop = messages.scrollHeight;
    }

    function appendBubble(role, text) {
      const bubble = createElement(
        "div",
        "cai-chat-bubble " + (role === "user" ? "cai-chat-bubble-user" : "cai-chat-bubble-bot"),
        text
      );
      messages.appendChild(bubble);
      scrollDown();
      return bubble;
    }

    let busy = false;

    function ask(item, btn) {
      if (busy) return;
      busy = true;
      btn.classList.add("is-asked");
      appendBubble("user", item.q);

      const typing = createElement("div", "cai-chat-bubble cai-chat-bubble-bot cai-chat-typing");
      typing.innerHTML = "<i></i><i></i><i></i>";
      typing.setAttribute("aria-label", "typing");
      messages.appendChild(typing);
      scrollDown();

      setTimeout(() => {
        typing.remove();
        const bubble = appendBubble("bot", item.a);
        if (item.cta) {
          const link = createElement("a", "cai-chat-cta", item.cta.label + " →");
          link.href = item.cta.href;
          bubble.appendChild(link);
        }
        scrollDown();
        busy = false;
      }, 650);
    }

    appendBubble("bot", GREETING);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildChatUI);
  } else {
    buildChatUI();
  }
})();
