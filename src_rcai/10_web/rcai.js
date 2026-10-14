// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
// The hub: one small key top right (request build) + the bell for every notice. Top of the body: logo · Hi, John · ⚙ (email · sign out).
// Request changes sits on each project square, only when that project is signed or paid (can_change from 02_records).
// Ghost keys beside the titles: "+ New project or phase" (Your projects) · "Request a demo" (Your demos), same window.
// Body: projects as small squares (+ a quiet Phase 2 square when a scope waits → its proposal: logo · deliverables · timeline · pay · Accept · Ask changes · Deny) · preferences (survey + review) · feedback.
// Every send opens a filled-in email: there is no request queue yet.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const MAIL = "customaimodels@gmail.com";
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const WHERE = { live: ["i-globe", "Live"], git: ["i-branch", "Git"], railway: ["i-cloud", "Railway"], email: ["i-mail", "Account email"] };
  const LANES = {
    changes: { title: "Request changes", ph: "What should change? Pages, wording, a bug…" },
    build: { title: "Request build", ph: "What should we build next?" },
    next: { title: "New project or phase", ph: "A new project, or the next phase of one you have. What should it do?", free: true },
    demo: { title: "Request a demo", ph: "What would you like to see working? Your data, your process…", free: true },
  };
  // the records still tag notices deploy / credits: they land on the matching key.
  const LANE_OF = { deploy: "changes", changes: "changes", credits: "build", build: "build" };
  let view = null, lane = null;

  const icon = (id) => `<svg class="ico"><use href="#${id}"/></svg>`;
  const sign = () => `\n\n— ${view ? view.full || view.name : ""}${view && view.company ? ", " + view.company : ""}`;
  const mail = (subject, body) => { location.href = `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; };

  // a phase 2 proposal waiting on the client: their logo, then 01 deliverables · 02 timeline · 03 start the build
  // (pay the invoice), then Accept · Ask changes · Deny. Each answer opens a filled-in email. No pay link = a quiet "on its way".
  function scope(p) {
    const s = p.scope;
    const part = (n, title, body) => `<div class="part"><b><i>0${n}</i>${title}</b><div>${body}</div></div>`;
    const items = `<ul>${s.items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
    const tl = (s.timeline || []).length
      ? `<ul class="tl">${s.timeline.map((t) => `<li><span>${esc(t.when)}</span>${esc(t.what)}</li>`).join("")}</ul>` : `<p class="mute">Set together on the first call.</p>`;
    const pay = `<div class="payrow">${s.pay ? `<strong>${esc(s.pay.amount)}</strong><p>${esc(s.pay.what)}</p>` : ""}
      ${s.pay_link ? `<a class="paygo" href="${esc(s.pay_link)}" target="_blank" rel="noopener">Pay invoice →</a>` : `<span class="paygo off">Invoice on its way</span>`}</div>`;
    const key = (a, label) => `<button type="button" class="sk ${a}" data-ans="${a}" data-p="${esc(p.code || p.name)}" data-s="${esc(s.name)}">${label}</button>`;
    return `<div class="scope"><div class="sh">${p.logo ? `<img class="logo" src="${esc(p.logo)}" alt="${esc(p.company || "")}">` : ""}
        <span class="cap">${esc(p.name)} · ${esc(s.name)}</span><span class="wait">Waiting on you</span></div>
      ${part(1, "Deliverables", items)}${part(2, "Timeline", tl)}${part(3, "Start the build", pay)}
      <div class="sks">${key("accept", "Accept")}${key("change", "Ask changes")}${key("deny", "Deny")}</div></div>`;
  }

  // one project = one small square: state, name, company, the stage track, and two small keys: git · railway.
  // The square itself does nothing on click. A git value "github.com/o/r · main" links to the repo; railway opens the dashboard.
  const href = (k, v) => k === "git" ? "https://" + v.split(" ")[0].replace(/^https?:\/\//, "") : "https://railway.com/dashboard";
  function card(p, stages, i) {
    p.where = p.where || []; p.notices = p.notices || [];
    const track = stages.map((_, j) => `<i class="${j < p.stage ? "on" : j === p.stage ? "now" : ""}"></i>`).join("");
    const keys = p.where.filter((w) => w.k === "git" || w.k === "railway")
      .map((w) => `<a class="sq" href="${esc(href(w.k, w.v))}" target="_blank" rel="noopener" title="${esc(WHERE[w.k][1])}: ${esc(w.v)}">${icon(WHERE[w.k][0])}</a>`).join("");
    const sq = `<article class="proj">
      <div class="top"><span class="tag ${p.stage >= 3 ? "ok" : ""}">${esc(p.stage_label)}</span>${p.logo ? `<img class="plogo" src="${esc(p.logo)}" alt="">` : ""}</div>
      <h3>${esc(p.name)}</h3><span class="co">${esc(p.company)}</span>
      <div class="track" title="${esc(stages[p.stage] || "")}">${track}</div>
      <div class="foot">${keys}${p.can_change ? `<button type="button" class="rc" data-p="${esc(p.code || p.name)}">${icon("i-pen")}Request changes${p.notices.some((n) => LANE_OF[n.lane] === "changes") ? `<i class="dot"></i>` : ""}</button>` : ""}</div>
    </article>`;
    // a real phase 2 scope = ONE wide square, the same website: phase 1 left, phase 2 right (its key opens its own page).
    if (!p.scope) return sq;
    const inner = sq.slice(sq.indexOf(">") + 1, sq.lastIndexOf("</article>"))
      .replace(/<h3>.*?<\/h3><span class="co">.*?<\/span>/, `<h3>Phase 1</h3>`).replace(/<img class="plogo"[^>]*>/, "");
    return `<article class="proj duo">
      <div class="dh">${p.logo ? `<img class="plogo" src="${esc(p.logo)}" alt="${esc(p.company || "")}">` : ""}<h3>${esc(p.name)}</h3><span class="co">${esc(p.company)}</span></div>
      <div class="pane">${inner}</div>
      <div class="pane p2">
        <span class="tag bad">${esc(p.scope.name)} awaits</span>
        <h3>${esc(p.scope.name)}</h3><span class="co">New build · ${p.scope.items.length} items</span>
        <button type="button" class="p2go" data-i="${i}">Review ${esc(p.scope.name)} →</button>
      </div>
    </article>`;
  }

  function badges(v) {
    const all = v.projects.flatMap((p) => (p.notices || []).map((n) => ({ ...n, p })));
    const set = (el, n) => { el.dataset.n = n; el.textContent = n || ""; };
    set($(".bell .badge"), all.length);
    set($('.tk[data-lane="build"] .badge'), all.filter((n) => LANE_OF[n.lane] === "build").length);
    $(".pop").innerHTML = all.length
      ? all.map((n) => `<div class="row">${icon(LANE_OF[n.lane] === "changes" ? "i-pen" : LANE_OF[n.lane] === "build" ? "i-code" : n.lane === "scope" ? "i-doc" : "i-bell")}<div>${esc(n.text)}<small>${esc(n.p.name)}</small></div></div>`).join("")
      : `<div class="none">Nothing new.</div>`;
  }

  function hub(v) {
    view = v;
    $("#gate").hidden = true; $("#hub").hidden = false;
    const n = v.projects.length;
    // top of the hub: their logo · Hi, <first name> · the settings key (who is signed in · sign out).
    $(".hi .nm").textContent = v.name || "";
    const lg = $(".hi .clogo");
    lg.hidden = !v.logo; if (v.logo) { lg.src = v.logo; lg.alt = v.company || ""; }
    $(".gpop .cn").textContent = v.owner ? "Owner" : v.company || "";
    $(".gpop .em").textContent = v.email || "";
    $(".co").textContent = v.owner ? `Owner view · ${n} projects · ${v.clients} clients` : v.company || "";
    // status demo_sent lives under Your demos, the rest under Your projects. i stays the index in v.projects (the #p2-<i> page).
    const all = v.projects.map((p, i) => [p, i]);
    const real = all.filter(([p]) => !p.demo), demos = all.filter(([p]) => p.demo);
    $("#cards").innerHTML = real.length ? real.map(([p, i]) => card(p, v.stages, i)).join("") : `<div class="empty">No projects yet.</div>`;
    $("#demos").innerHTML = demos.length ? demos.map(([p, i]) => card(p, v.stages, i)).join("") : `<div class="empty">No demos yet. Ask for one, built on your own data.</div>`;
    $(".ask select").innerHTML = v.projects.map((p) => `<option value="${esc(p.code || p.name)}">${esc(p.name)}</option>`).join("");
    badges(v);
    route();
  }

  // #p2-<i> = that project's phase 2 page; anything else = the hub. Browser back works.
  function route() {
    const m = location.hash.match(/^#p2-(\d+)$/), p = m && view && view.projects[+m[1]];
    const on = !!(p && p.scope);
    $("#home").hidden = on; $("#p2page").hidden = !on;
    $("#scopes").innerHTML = on ? scope(p) : "";
    window.scrollTo({ top: 0 });
  }
  window.addEventListener("hashchange", () => { if (view && !$("#hub").hidden) route(); });

  function open(which, proj) {
    const form = $(".ask");
    const same = lane === which && !form.hidden && (!proj || form.project.value === proj);
    document.querySelectorAll(".tk").forEach((b) => b.setAttribute("aria-expanded", String(!same && b.dataset.lane === which)));
    if (same) { form.hidden = true; lane = null; return; }
    lane = which;
    form.hidden = false;
    form.project.hidden = !!LANES[which].free;
    form.msg.placeholder = LANES[which].ph;
    if (proj) form.project.value = proj;
    form.msg.focus({ preventScroll: true });
  }

  document.querySelectorAll(".tk").forEach((b) => b.addEventListener("click", () => open(b.dataset.lane)));
  // the ghost keys beside a section title open the same one message window, at the top.
  document.querySelectorAll(".gk").forEach((b) => b.addEventListener("click", () => { open(b.dataset.lane); window.scrollTo({ top: 0 }); }));

  // Request changes on a square → the window with that project picked; Review Phase 2 → its own page.
  const onCards = (e) => {
    const rc = e.target.closest(".rc");
    if (rc) { open("changes", rc.dataset.p); window.scrollTo({ top: 0 }); return; }
    const b = e.target.closest(".p2go");
    if (b) location.hash = "p2-" + b.dataset.i;
  };
  $("#cards").addEventListener("click", onCards);
  $("#demos").addEventListener("click", onCards);

  const ANSWER = { accept: "Accept", change: "Ask changes", deny: "Deny" };
  $("#scopes").addEventListener("click", (e) => {
    const b = e.target.closest(".sk");
    if (!b) return;
    const lead = { accept: "We accept this proposal.", deny: "We decline this proposal.", change: "We'd like these changes to the proposal:\n\n" }[b.dataset.ans];
    mail(`[R-CAI] Phase 2 · ${b.dataset.s} · ${ANSWER[b.dataset.ans]} · ${b.dataset.p}`, lead + sign());
  });

  // preferences: one chip per question (tap again to clear), a review if they want, one send.
  document.querySelectorAll(".chips").forEach((g) => g.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const on = b.getAttribute("aria-pressed") !== "true";
    g.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b && on)));
  }));
  $("#prefs").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const pick = (q) => $(`.chips[data-q="${q}"] [aria-pressed="true"]`, f)?.textContent || "-";
    const body = `Rating: ${pick("rating")}/5\nUpdates: ${pick("updates")}\nRecommend: ${pick("recommend")}\n\nReview:\n${f.review.value.trim() || "-"}`;
    mail(`[R-CAI] Preferences · ${view?.company || view?.name || ""}`, body + sign());
  });
  $("#fb").addEventListener("submit", (e) => {
    e.preventDefault();
    mail(`[R-CAI] Feedback · ${view?.company || view?.name || ""}`, e.currentTarget.msg.value.trim() + sign());
  });

  $(".ask").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    mail(`[R-CAI] ${LANES[lane].title}${LANES[lane].free ? "" : " · " + f.project.value}`, f.msg.value.trim() + sign());
  });

  $(".gear").addEventListener("click", (e) => {
    const pop = $(".gpop"), on = pop.hidden;
    pop.hidden = !on; e.currentTarget.setAttribute("aria-expanded", String(on));
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".gear, .gpop")) { $(".gpop").hidden = true; $(".gear").setAttribute("aria-expanded", "false"); }
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
    $(".gpop").hidden = true; $("#login").reset(); gate();
  });

  me().then((v) => (v ? hub(v) : gate()));
})();
