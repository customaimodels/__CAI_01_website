// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
// The hub: two actions (credits · deploy), each with a corner badge; the bell holds every notice.
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

  function card(p, stages) {
    p.where = p.where || []; p.notices = p.notices || [];
    const track = stages.map((_, i) => `<i class="${i < p.stage ? "on" : i === p.stage ? "now" : ""}"></i>`).join("");
    const names = stages.map((s, i) => `<span class="${i === p.stage ? "now" : ""}">${esc(s)}</span>`).join("");
    const tag = `<span class="tag ${p.stage >= 3 ? "ok" : p.notices.some((n) => n.lane === "general") ? "wait" : ""}">${esc(p.stage_label)}</span>`;
    return `<article class="proj">
      <div class="top"><div><span class="code">${esc(p.code)}</span><h3>${esc(p.name)}</h3>
        <span class="co">${esc(p.company)}${p.phase ? " · " + esc(p.phase) : ""}</span></div>${tag}</div>
      ${p.note ? `<p class="note">${esc(p.note)}</p>` : ""}
      <div class="track">${track}</div><div class="steps">${names}</div>
      ${p.where.length ? `<div class="where">${p.where.map(where).join("")}</div>` : ""}
      ${p.notices.map((n) => `<div class="ntc">${icon("i-bell")}${esc(n.text)}</div>`).join("")}
    </article>`;
  }

  function badges(v) {
    const all = v.projects.flatMap((p) => (p.notices || []).map((n) => ({ ...n, p })));
    const set = (el, n) => { el.dataset.n = n; el.textContent = n || ""; };
    set($(".bell .badge"), all.length);
    set($(".act.credits .badge"), all.filter((n) => n.lane === "credits").length);
    set($(".act.deploy .badge"), all.filter((n) => n.lane === "deploy").length);
    $(".pop").innerHTML = all.length
      ? all.map((n) => `<div class="row">${icon(n.lane === "credits" ? "i-credits" : n.lane === "deploy" ? "i-deploy" : "i-bell")}<div>${esc(n.text)}<small>${esc(n.p.name)}</small></div></div>`).join("")
      : `<div class="none">Nothing new.</div>`;
  }

  function hub(v) {
    view = v;
    $("#gate").hidden = true; $("#hub").hidden = false;
    $(".who").innerHTML = `<b>${esc(v.full || v.name)}</b><br>${esc(v.role || "")}${v.company ? " · " + esc(v.company) : ""}`;
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
    document.querySelectorAll(".act").forEach((b) => b.setAttribute("aria-expanded", String(!same && b.dataset.lane === which)));
    if (same) { form.hidden = true; lane = null; return; }
    lane = which;
    form.hidden = false;
    $(".ttl", form).textContent = LANES[which].title;
    $("h3 use", form).setAttribute("href", which === "credits" ? "#i-credits" : "#i-deploy");
    form.msg.placeholder = LANES[which].ph;
    form.msg.focus({ preventScroll: true });
  }

  document.querySelectorAll(".act").forEach((b) => b.addEventListener("click", () => open(b.dataset.lane)));

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

  function gate() { $("#hub").hidden = true; $("#gate").hidden = false; $("#login [name=email]").focus(); }

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
