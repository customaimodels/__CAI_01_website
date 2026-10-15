// The assistant (#ask). Talks to __ss2_ChatBot (POST /api/chat). Honest when it is down: says so, keeps the visitor's words.
// v2 (2026-10-14, Task 03): status names a model only when /status says mode=model · text survives a failed send ·
// scroll follows only if the reader is already at the bottom · IME-safe Enter · touch keyboards never send on ↵.
(() => {
  const root = document.getElementById("ask");
  if (!root) return;
  const local = /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  const API = window.CAI_CHAT_API || (local ? "http://127.0.0.1:8190/api/chat" : "/api/chat");
  const MAIL = "customaimodels@gmail.com";

  const log = root.querySelector(".ai-log");
  const form = root.querySelector(".ai-form");
  const box = form.querySelector("textarea");
  const send = form.querySelector(".ai-send");
  const st = root.querySelector(".ai-st");
  const tries = [...root.querySelectorAll(".ai-try button")];
  const human = root.querySelector(".ai-human");
  const touch = matchMedia("(hover: none)").matches;
  if (innerWidth < 520) box.placeholder = "e.g. Sales into Excel, by hand";   // one line on a phone, never clipped
  const HINT = box.placeholder;
  let sid = sessionStorage.getItem("cai-chat-sid") || "";
  let busy = false;

  const esc = s => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>");

  // Small markdown: paragraphs, - / * bullets, 1. lists, **bold**, `code`. Everything escaped first.
  function md(text) {
    const out = []; let list = null;
    const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
    for (const raw of String(text).replace(/\r/g, "").split("\n")) {
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

  const atBottom = () => log.scrollHeight - log.scrollTop - log.clientHeight < 48;
  function follow(was) { if (was) log.scrollTop = log.scrollHeight; }

  function entry(who, cls, html) {
    const was = atBottom();
    const el = document.createElement("div");
    el.className = `ai-msg ${cls}`;
    el.innerHTML = `<span class="ai-who">${who}</span><div class="ai-txt">${html}</div>`;
    log.appendChild(el);
    follow(was);
    return el;
  }

  // live = a model answers · rec = the best matching passage from our notes, verbatim · off = nothing answers.
  function status(kind, text) { st.className = "ai-st " + kind; st.textContent = text; }

  async function ping() {
    try {
      const r = await fetch(API + "/status", { cache: "no-store" });
      const j = await r.json();
      if (j.mode === "model") status("live", `Online · ${j.model}`);
      else if (j.mode === "record") status("rec", "From our notes");
      else status("off", "Offline");
    } catch { status("off", "Offline"); }
  }

  function lock(on) {
    busy = on;
    send.disabled = on;
    send.querySelector("span").textContent = on ? "Asking" : "Ask";
    tries.forEach(b => (b.disabled = on));
  }

  async function ask(q) {
    q = (q || "").trim();
    if (!q || busy) return;
    lock(true);
    const typed = box.value;
    box.value = ""; fit();
    log.scrollTop = log.scrollHeight;            // your own question always lands in view
    entry("You", "you", md(q));
    const work = entry("CAI", "bot", `<span class="ai-wait"><i></i>Reading our notes</span>`);
    let html, err = false;
    try {
      const r = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid, message: q }) });
      if (r.status === 429) throw new Error("busy");
      if (!r.ok) throw new Error("http");
      const j = await r.json();
      if (j.session_id) { sid = j.session_id; sessionStorage.setItem("cai-chat-sid", sid); }
      if (!j.reply) throw new Error("empty");
      html = md(j.reply);
      const src = (j.sources || []).map(s => `<span class="s">${esc(String(s))}</span>`).join("");
      if (src) html += `<div class="ai-src"><span>${j.live ? "Grounded in" : "From our notes"}</span>${src}</div>`;
      if (j.lead_captured) html += `<div class="ai-stamp">✓ Received · a person replies by email</div>`;
    } catch (e) {
      err = true;
      html = md(e.message === "busy"
        ? "A lot of questions at once. Give it a minute and ask again; your words are back in the box."
        : `The assistant isn't answering right now. Your words are back in the box. Or write to **${MAIL}** and a person replies.`);
      if (!box.value) { box.value = typed || q; fit(); }
      if (e.message !== "busy") status("off", "Offline");
    }
    const was = atBottom();
    work.className = "ai-msg bot" + (err ? " err" : "");
    work.querySelector(".ai-txt").innerHTML = html;
    if (was) log.scrollTop = Math.min(work.offsetTop - log.offsetTop - 16, log.scrollHeight);   // a long answer opens at its first line
    if (!err && st.classList.contains("off")) ping();
    lock(false);
    if (!touch) box.focus({ preventScroll: true });
  }

  function fit() { box.style.height = "auto"; box.style.height = Math.min(box.scrollHeight, 160) + "px"; }

  form.addEventListener("submit", e => { e.preventDefault(); ask(box.value); });
  box.addEventListener("input", fit);
  box.addEventListener("keydown", e => {
    if (e.key !== "Enter" || e.shiftKey || e.isComposing || e.keyCode === 229 || touch) return;
    e.preventDefault(); ask(box.value);
  });
  tries.forEach(b => b.addEventListener("click", () => ask(b.dataset.q)));

  // A person: the chatbot already turns a Name / Email / Project reply into a lead (src/08_leads.py).
  human?.addEventListener("click", () => {
    box.value = "Name: \nEmail: \nProject: ";
    box.placeholder = HINT;
    fit();
    box.focus();
    box.setSelectionRange(6, 6);
  });

  // The quiet invitation: scroll to the console and put the cursor in the box. The conversation is never reset.
  const inv = document.querySelector(".ai-invite");
  if (inv) inv.addEventListener("click", e => {
    e.preventDefault();
    root.querySelector(".ai-con").scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => box.focus({ preventScroll: true }), 500);
  });
  // The launcher steps away while the console is on screen.
  const fab = document.querySelector(".ai-fab");
  if (fab) {
    new IntersectionObserver(([e]) => fab.classList.toggle("away", e.isIntersecting), { threshold: 0.25 }).observe(root);
    fab.addEventListener("click", e => { e.preventDefault(); root.scrollIntoView({ behavior: "smooth" }); setTimeout(() => box.focus({ preventScroll: true }), 500); });
  }

  ping();
})();
