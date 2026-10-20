// The reader card (2026-10-20). A LinkedIn reader gets ONE question, once, after they have actually read.
// Answer + email + consent tick -> POST /r-cai/api/reader -> R-CAI inbox (kind=reader) + admin mail.
// Never on first paint, never twice in 14 days, never a modal. ?ask=1 forces it (testing).
(() => {
  const q = new URLSearchParams(location.search), ua = navigator.userAgent.toLowerCase();
  const src = (q.get("utm_source") || q.get("src") || "").toLowerCase();
  const ref = document.referrer.toLowerCase();
  const li = src.includes("linkedin") || src === "li" || /linkedin\.com|lnkd\.in/.test(ref) || ua.includes("linkedinapp");
  const force = q.get("ask") === "1";
  const KEY = "cai_reader";
  let seen = 0; try { seen = +localStorage.getItem(KEY) || 0; } catch (e) {}
  if (!force && (!li || Date.now() - seen < 14 * 864e5)) return;

  const box = document.createElement("aside");
  box.className = "reader-card"; box.setAttribute("aria-label", "One question from Custom AI Models");
  box.innerHTML = `
    <button class="rc-x" type="button" aria-label="Close">×</button>
    <p class="rc-k">ONE QUESTION · FROM YERIKO</p>
    <h3 class="rc-q">What's the one data problem you'd fix first?</h3>
    <form class="rc-f" novalidate>
      <textarea name="answer" rows="2" maxlength="1200" placeholder="One line is enough. The tool, the mess, the hours it eats."></textarea>
      <input name="email" type="email" autocomplete="email" placeholder="Work email" maxlength="160">
      <input name="hp" type="text" tabindex="-1" autocomplete="off" class="rc-hp" aria-hidden="true">
      <label class="rc-ok"><input name="consent" type="checkbox"> Write back to me about this. Nothing else.</label>
      <button class="rc-go" type="submit">Send →</button>
      <p class="rc-msg" role="status"></p>
    </form>`;
  const close = () => { box.classList.remove("in"); try { localStorage.setItem(KEY, Date.now()); } catch (e) {} setTimeout(() => box.remove(), 500); };
  box.querySelector(".rc-x").onclick = close;
  box.querySelector("form").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = ev.target, msg = f.querySelector(".rc-msg"), go = f.querySelector(".rc-go");
    const body = { answer: f.answer.value, email: f.email.value, consent: f.consent.checked, hp: f.hp.value,
                   page: location.pathname, src: src || (li ? "linkedin" : "direct") };
    go.disabled = true; msg.textContent = "";
    try {
      const r = await fetch("/r-cai/api/reader", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json().catch(() => ({}));
      if (r.ok) {
        box.querySelector(".rc-q").textContent = "Got it. Yeriko writes back within 24 hours.";
        f.remove(); try { localStorage.setItem(KEY, Date.now() + 365 * 864e5); } catch (e) {}
        setTimeout(close, 4000);
      } else { msg.textContent = j.error || "That didn't send. Try again."; go.disabled = false; }
    } catch (e) { msg.textContent = "That didn't send. Try again."; go.disabled = false; }
  };

  let shown = false;
  const show = () => { if (shown) return; shown = true; document.body.appendChild(box); requestAnimationFrame(() => requestAnimationFrame(() => box.classList.add("in"))); };
  if (force) { setTimeout(show, 600); return; }
  setTimeout(show, 25000);                                  // 25 s on the page
  addEventListener("scroll", () => {                        // or 45% read, whichever comes first
    const h = document.documentElement;
    if ((h.scrollTop + innerHeight) / h.scrollHeight > 0.45) show();
  }, { passive: true });
})();
