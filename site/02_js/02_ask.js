// The assistant (#ask). Talks to __ss2_ChatBot (POST /api/chat). Honest when it is down: says so, offers the email.
(() => {
  const root = document.getElementById("ask");
  if (!root) return;
  const local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  const API = window.CAI_CHAT_API || (local ? "http://127.0.0.1:8190/api/chat" : "/api/chat");
  const MAIL = "customaimodels@gmail.com";

  const log = root.querySelector(".ai-log");
  const form = root.querySelector(".ai-form");
  const box = form.querySelector("textarea");
  const send = form.querySelector("button");
  const st = root.querySelector(".ai-st");
  const docs = root.querySelector("[data-docs]");
  let sid = sessionStorage.getItem("cai-chat-sid") || "";
  let busy = false;

  const esc = s => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>");

  // Small markdown: paragraphs, - / * bullets, 1. lists, **bold**. Everything escaped first.
  function md(text) {
    const out = []; let list = null;
    const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
    for (const raw of text.replace(/\r/g, "").split("\n")) {
      const line = raw.trim();
      const ul = line.match(/^[-*•]\s+(.*)/), ol = line.match(/^\d+[.)]\s+(.*)/);
      if (ul || ol) {
        const kind = ul ? "ul" : "ol";
        if (list !== kind) { close(); out.push(`<${kind}>`); list = kind; }
        out.push(`<li>${inline((ul || ol)[1])}</li>`);
      } else if (!line) { close(); }
      else { close(); out.push(`<p>${inline(line)}</p>`); }
    }
    close();
    return out.join("");
  }

  function entry(who, cls, html) {
    const el = document.createElement("div");
    el.className = `ai-msg ${cls}`;
    el.innerHTML = `<span class="ai-who">${who}</span><div class="ai-txt">${html}</div>`;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function status(live, text) {
    st.className = "ai-st " + (live ? "live" : "off");
    st.textContent = text;
  }

  async function ping() {
    try {
      const r = await fetch(API + "/status", { cache: "no-store" });
      const j = await r.json();
      if (docs && j.docs) docs.textContent = j.docs;
      status(j.live, j.live ? `Live · ${j.model}` : "Script only · model resting");
    } catch { status(false, "Offline"); }
  }

  async function ask(q) {
    q = q.trim();
    if (!q || busy) return;
    busy = true; send.disabled = true; box.value = ""; fit();
    entry("You", "you", md(q));
    const work = entry("CAI", "bot ai-work", `Reading the record<div class="ai-scan"></div>`);
    try {
      const r = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: q }) });
      const j = await r.json();
      if (j.session_id) { sid = j.session_id; sessionStorage.setItem("cai-chat-sid", sid); }
      let html = md(j.reply || "");
      const src = (j.sources || []).map(s => `<span class="s">${esc(s)}</span>`).join("");
      if (src || j.live === false)
        html += `<div class="ai-src"><span>Grounded in</span>${src}${j.live === false ? `<span class="s fb">${j.mode === "record" ? "From the record" : "Script reply"}</span>` : ""}</div>`;
      if (j.lead_captured) html += `<div class="ai-stamp">✓ Received · a reply comes by email</div>`;
      work.className = "ai-msg bot"; work.querySelector(".ai-txt").innerHTML = html;
    } catch {
      work.className = "ai-msg bot";
      work.querySelector(".ai-txt").innerHTML = md(`The assistant isn't answering right now. Write to **${MAIL}** and the reply comes from a person.`);
      status(false, "Offline");
    }
    log.scrollTop = log.scrollHeight;
    busy = false; send.disabled = false; box.focus();
  }

  function fit() { box.style.height = "auto"; box.style.height = Math.min(box.scrollHeight, 160) + "px"; }

  form.addEventListener("submit", e => { e.preventDefault(); ask(box.value); });
  box.addEventListener("input", fit);
  box.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(box.value); } });
  root.querySelectorAll(".ai-try button").forEach(b => b.addEventListener("click", () => ask(b.dataset.q)));

  // The launcher steps away while the console is on screen.
  const fab = document.querySelector(".ai-fab");
  if (fab) {
    new IntersectionObserver(([e]) => fab.classList.toggle("away", e.isIntersecting), { threshold: 0.25 }).observe(root);
    fab.addEventListener("click", e => { e.preventDefault(); root.scrollIntoView({ behavior: "smooth" }); setTimeout(() => box.focus({ preventScroll: true }), 500); });
  }

  ping();
})();
