// The reader bridge + card (2026-10-20, v2). LinkedIn readers only (utm/src linkedin, linkedin.com/lnkd.in referrer,
// LinkedIn app). No page in between, nothing pushy:
//   1 FRAME  a quiet line above the article: who it is written for (FRAMES below, default = COO / CFO data warehouse).
//   2 CARD   after 45% read or 25 s: name · company · team size · the data problem · work email · consent.
//            -> POST /r-cai/api/reader -> R-CAI inbox (kind=reader) + admin mail. The beacon's anonymous id (vid)
//            rides along so __Ysrc/11_inbound.py can join what they read before they wrote.
// Never on first paint, never twice in 14 days, never a modal. ?ask=1 forces both (testing).
(() => {
  // one row per article slug; any slug not here gets "default". Edit freely: words only, no logic.
  const FRAMES = {
    "default": { who: "For COOs and CFOs", line: "Your data lives in five places and nobody trusts the totals. This is where the fix starts.",
                 q: "What's the one data problem you'd fix first?" },
    "rag-production-architecture": { who: "For CTOs and engineering leads", line: "Your RAG demo worked. Production is where it breaks.",
                 q: "Where does your retrieval break today?" },
    "python-ai-agent-pipelines": { who: "For operators running AI tools by hand", line: "Twelve tools, one Python pipeline you own.",
                 q: "Which manual step would you hand to a pipeline first?" },
  };
  const q = new URLSearchParams(location.search), ua = navigator.userAgent.toLowerCase();
  const src = (q.get("utm_source") || q.get("src") || "").toLowerCase();
  const ref = document.referrer.toLowerCase();
  const li = src.includes("linkedin") || src === "li" || /linkedin\.com|lnkd\.in/.test(ref) || ua.includes("linkedinapp");
  const force = q.get("ask") === "1";
  if (!force && !li) return;
  const slug = (location.pathname.match(/\/articles\/([^/]+)\//) || [])[1] || "";
  const fr = FRAMES[slug] || FRAMES["default"];
  const frameKey = FRAMES[slug] ? slug : "default";

  // 1 FRAME: one line under the article head, every LinkedIn visit (it is context, not an ask)
  const head = document.querySelector(".art-head") || document.querySelector("article");
  if (head) {
    const s = document.createElement("p");
    s.className = "reader-frame";
    s.innerHTML = `<span class="rf-k"></span> <span class="rf-l"></span>`;
    s.querySelector(".rf-k").textContent = fr.who;
    s.querySelector(".rf-l").textContent = fr.line;
    head.insertAdjacentElement(head.matches(".art-head") ? "afterend" : "afterbegin", s);
  }

  // 2 CARD: once in 14 days
  const KEY = "cai_reader";
  let seen = 0; try { seen = +localStorage.getItem(KEY) || 0; } catch (e) {}
  if (!force && Date.now() - seen < 14 * 864e5) return;

  const box = document.createElement("aside");
  box.className = "reader-card"; box.setAttribute("aria-label", "One question from Custom AI Models");
  box.innerHTML = `
    <button class="rc-x" type="button" aria-label="Close">×</button>
    <p class="rc-k">ONE QUESTION · FROM YERIKO</p>
    <h3 class="rc-q"></h3>
    <form class="rc-f" novalidate>
      <input name="name" type="text" autocomplete="name" placeholder="Your name" maxlength="120">
      <div class="rc-row">
        <input name="company" type="text" autocomplete="organization" placeholder="Company" maxlength="120">
        <select name="scale" aria-label="Team size">
          <option value="">Team size</option>
          <option>1 – 10 employees</option><option>11 – 50 employees</option>
          <option>51 – 200 employees</option><option>201+ enterprise scale</option>
        </select>
      </div>
      <textarea name="answer" rows="2" maxlength="1200" placeholder="The data problem. One line is enough: the tool, the mess, the hours it eats."></textarea>
      <input name="email" type="email" autocomplete="email" placeholder="Work email" maxlength="160">
      <input name="hp" type="text" tabindex="-1" autocomplete="off" class="rc-hp" aria-hidden="true">
      <label class="rc-ok"><input name="consent" type="checkbox"> Write back to me about this. Nothing else.</label>
      <button class="rc-go" type="submit">Send →</button>
      <p class="rc-msg" role="status"></p>
    </form>`;
  box.querySelector(".rc-q").textContent = fr.q;
  const close = () => { box.classList.remove("in"); try { localStorage.setItem(KEY, Date.now()); } catch (e) {} setTimeout(() => box.remove(), 500); };
  box.querySelector(".rc-x").onclick = close;
  box.querySelector("form").onsubmit = async (ev) => {
    ev.preventDefault();
    const f = ev.target, msg = f.querySelector(".rc-msg"), go = f.querySelector(".rc-go");
    let vid = ""; try { vid = localStorage.getItem("cai_v") || ""; } catch (e) {}
    const body = { name: f.name.value, company: f.company.value, scale: f.scale.value, answer: f.answer.value,
                   email: f.email.value, consent: f.consent.checked, hp: f.hp.value, vid, frame: frameKey,
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
