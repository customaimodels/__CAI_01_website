// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
// The hub: two small keys top right (credits · deploy) with corner badges, the bell for every notice,
// and a scope card (Accept · Ask changes · Deny) on any project with a scope waiting.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const MAIL = "customaimodels@gmail.com";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const WHERE = { live: ["i-globe", "Live"], git: ["i-branch", "Git"], railway: ["i-cloud", "Railway"], email: ["i-mail", "Account email"] };
  const LANES = {
    credits: { title: "Add credits", ph: "How many hours, and for what?" },
    deploy: { title: "Deploy changes", ph: "What should change? Pages, wording, a bug, a new screen…" },
  };
  let view = null, lane = null;

  const icon = (id) => `<svg class="ico"><use href="#${id}"/></svg>`;

  function where(w) {
    const v = esc(w.v), [ic, label] = WHERE[w.k];
    const text = `<span>${v.replace(/^https?:\/\//, "")}</span>`;
    const val = w.k === "live" ? `<a href="${v}" target="_blank" rel="noopener">${text}</a>` : text;
    return `<div>${icon(ic)}<span style="min-width:0"><small>${label}</small>${val}</span></div>`;
  }

  // a scope waiting on the client: its lines + three answers. Each answer opens a filled-in email.
  function scope(p) {
    if (!p.scope) return "";
    const items = p.scope.items.map((t) => `<li>${esc(t)}</li>`).join("");
    const key = (a, label) => `<button type="button" class="sk ${a}" data-ans="${a}" data-p="${esc(p.code || p.name)}" data-s="${esc(p.scope.name)}">${label}</button>`;
    return `<div class="scope"><div class="sh"><span class="cap">${esc(p.scope.name)} · scope</span><span class="wait">Waiting on you</span></div>
      <ul>${items}</ul>
      <div class="sks">${key("accept", "Accept")}${key("change", "Ask changes")}${key("deny", "Deny")}</div></div>`;
  }

  function card(p, stages) {
    p.where = p.where || []; p.notices = p.notices || [];
    const track = stages.map((_, i) => `<i class="${i < p.stage ? "on" : i === p.stage ? "now" : ""}"></i>`).join("");
    const tag = `<span class="tag ${p.stage >= 3 ? "ok" : ""}">${esc(p.stage_label)}</span>`;
    return `<article class="proj">
      <div class="top"><div><h3>${esc(p.name)}</h3><span class="co">${esc(p.company)}${p.code ? " · " + esc(p.code) : ""}</span></div>${tag}</div>
      <div class="track" title="${esc(stages[p.stage] || "")}">${track}</div>
      ${p.where.length ? `<div class="where">${p.where.map(where).join("")}</div>` : ""}
      ${scope(p)}
    </article>`;
  }

  function badges(v) {
    const all = v.projects.flatMap((p) => (p.notices || []).map((n) => ({ ...n, p })));
    const set = (el, n) => { el.dataset.n = n; el.textContent = n || ""; };
    set($(".bell .badge"), all.length);
    set($('.tk[data-lane="credits"] .badge'), all.filter((n) => n.lane === "credits").length);
    set($('.tk[data-lane="deploy"] .badge'), all.filter((n) => n.lane === "deploy").length);
    $(".pop").innerHTML = all.length
      ? all.map((n) => `<div class="row">${icon(n.lane === "credits" ? "i-credits" : n.lane === "deploy" ? "i-deploy" : n.lane === "scope" ? "i-doc" : "i-bell")}<div>${esc(n.text)}<small>${esc(n.p.name)}</small></div></div>`).join("")
      : `<div class="none">Nothing new.</div>`;
  }

  function hub(v) {
    view = v;
    $("#gate").hidden = true; $("#hub").hidden = false;
    $(".co").textContent = v.owner ? "Owner view · every hub" : v.company || "";
    $(".greet").innerHTML = `Good ${part}, <em>${esc(v.name)}</em>.`;
    const n = v.projects.length;
    $(".sub").textContent = v.owner ? `${n} projects across ${v.clients} clients.` : `${n} project${n === 1 ? "" : "s"} on your hub.`;
    $("#cards").innerHTML = n ? v.projects.map((p) => card(p, v.stages)).join("") : `<div class="empty">No projects on your hub yet. Write to ${MAIL}.</div>`;
    $(".ask select").innerHTML = v.projects.map((p) => `<option value="${esc(p.code || p.name)}">${esc(p.name)}</option>`).join("");
    badges(v);
  }

  function open(which) {
    const form = $(".ask");
    const same = lane === which && !form.hidden;
    document.querySelectorAll(".tk").forEach((b) => b.setAttribute("aria-expanded", String(!same && b.dataset.lane === which)));
    if (same) { form.hidden = true; lane = null; return; }
    lane = which;
    form.hidden = false;
    form.msg.placeholder = LANES[which].ph;
    form.msg.focus({ preventScroll: true });
  }

  document.querySelectorAll(".tk").forEach((b) => b.addEventListener("click", () => open(b.dataset.lane)));

  const ANSWER = { accept: "Accept", change: "Ask changes", deny: "Deny" };
  $("#cards").addEventListener("click", (e) => {
    const b = e.target.closest(".sk");
    if (!b) return;
    const lead = { accept: "We accept this scope.", deny: "We decline this scope.", change: "We'd like these changes to the scope:\n\n" }[b.dataset.ans];
    const subject = `[R-CAI] ${b.dataset.s} scope · ${ANSWER[b.dataset.ans]} · ${b.dataset.p}`;
    const body = `${lead}\n\n— ${view ? view.full || view.name : ""}${view && view.company ? ", " + view.company : ""}`;
    location.href = `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  $(".ask").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const subject = `[R-CAI] ${LANES[lane].title} · ${f.project.value}`;
    const body = `${f.msg.value.trim()}\n\n— ${view ? view.full || view.name : ""}${view && view.company ? ", " + view.company : ""}`;
    location.href = `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });

  $(".bell").addEventListener("click", (e) => {
    const pop = $(".pop"), on = pop.hidden;
    pop.hidden = !on; e.currentTarget.setAttribute("aria-expanded", String(on));
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".bell, .pop")) { $(".pop").hidden = true; $(".bell").setAttribute("aria-expanded", "false"); }
  });

  // the gate has three faces: login · signup · sent. #signup in the URL (the landing's Get started) opens sign up.
  function face(which) {
    ["login", "signup", "sent"].forEach((id) => ($("#" + id).hidden = id !== which));
    document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.face === (which === "sent" ? "signup" : which))));
    const first = $(`#${which} input`);
    if (first) first.focus({ preventScroll: true });
    history.replaceState(null, "", which === "signup" ? "#signup" : location.pathname);
  }
  document.querySelectorAll("[data-face]").forEach((el) => el.addEventListener("click", (e) => { e.preventDefault(); face(el.dataset.face); }));

  $("#signup").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const subject = `[R-CAI] Sign up · ${f.company.value.trim() || f.name.value.trim()}`;
    const body = `Name: ${f.name.value.trim()}\nCompany: ${f.company.value.trim()}\nEmail: ${f.email.value.trim()}\n\nWhat we need:\n${f.need.value.trim()}`;
    location.href = `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    face("sent");
  });

  function gate() { $("#hub").hidden = true; $("#gate").hidden = false; face(location.hash === "#signup" ? "signup" : "login"); }

  async function me() {
    try {
      const r = await fetch("api/me", { credentials: "same-origin" });
      return r.ok ? r.json() : null;
    } catch { return null; }
  }

  $("#login").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget, btn = $("button", f), err = $(".err", f);
    btn.disabled = true; err.textContent = "";
    try {
      const r = await fetch("api/login", {
        method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: f.email.value, code: f.code.value }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { err.textContent = j.error || "That didn't open a hub."; f.code.value = ""; return; }
      const v = await me();
      v ? hub(v) : (err.textContent = "Signed in, but the hub didn't load. Try again.");
    } catch { err.textContent = "The portal is offline. Try again in a minute."; }
    finally { btn.disabled = false; }
  });

  $(".out").addEventListener("click", async () => {
    await fetch("api/logout", { method: "POST", credentials: "same-origin" }).catch(() => {});
    $("#login").reset(); gate();
  });

  me().then((v) => (v ? hub(v) : gate()));
})();
