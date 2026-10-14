// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
// The hub: one small key top right (request build) + the bell for every notice. Top of the body: logo · Hi, John · ⚙ (details · change password · sign out; owners + master table).
// Phase 1 edits: a small ✎ key on the square (only when signed or paid, can_change from 02_records) → one box, answered within 24 h.
// Phase 2 changes are scope changes, asked on its own page: a comment per deliverable + new capabilities, pushed twice to be specific.
// Ghost keys beside the titles: "+ New project or phase" (Your projects) · "Request a demo" (Your demos), same window.
// Body: projects as small squares (+ a quiet Phase 2 square when a scope waits → its proposal: logo · deliverables · timeline · pay · Accept · Ask changes · Deny) · preferences (survey + review) · feedback.
// Every send goes to api/request (08_inbox: saved for him to read), then every request key pauses 24 h: we write back in that window.
// Stripe never pauses. The server holds the pause too (429), so a reload or another device doesn't reopen it.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const WHERE = { live: ["i-globe", "Live"], git: ["i-branch", "Git"], railway: ["i-cloud", "Railway"], email: ["i-mail", "Account email"] };
  const LANES = {
    changes: { title: "Edits", ph: "Changes, edits or concerns. All of it, in one place.", note: "We're back to you within 24 hours." },
    build: { title: "Request build", ph: "What should we build next?" },
    next: { title: "New project or phase", ph: "A new project, or the next phase of one you have. What should it do?", free: true },
    demo: { title: "Request a demo", ph: "What would you like to see working? Your data, your process…", free: true },
    plug: { title: "Plug-in", ph: "What should it do for you?", free: true },
  };
  // the records still tag notices deploy / credits: they land on the matching key.
  const LANE_OF = { deploy: "changes", changes: "changes", credits: "build", build: "build" };
  let view = null, lane = null;

  // every step on a Phase 2 page goes to api/event (07_activity): run.py --activity says where the client stands.
  // sendBeacon survives a page change; it carries pointers only (which step, picks, total), never note text.
  function track(act, i = +location.hash.slice(4)) {
    const p = view && view.projects[i], s = p && p.scope;
    if (!s) return;
    const picked = added(), bl = bill(s, picked);
    const body = JSON.stringify({ i, act, picked, ...(bl ? { total: bl.tot, deposit: bl.dep } : {}) });
    try { if (navigator.sendBeacon && navigator.sendBeacon("api/event", body)) return; } catch {}
    fetch("api/event", { method: "POST", credentials: "same-origin", keepalive: true, body }).catch(() => {});
  }

  // ?fresh wipes this device's test state (add-on picks, scope notes, the 24 h hold) and opens clean. Device only, nothing server-side.
  if (new URLSearchParams(location.search).has("fresh")) {
    try { Object.keys(localStorage).filter((k) => k.startsWith("rcai.")).forEach((k) => localStorage.removeItem(k)); } catch {}
    history.replaceState(null, "", location.pathname + location.hash);
  }

  const icon = (id) => `<svg class="ico"><use href="#${id}"/></svg>`;
  const sign = () => `\n\n— ${view ? view.full || view.name : ""}${view && view.company ? ", " + view.company : ""}`;
  // send = one request to us. ok → the 24 h pause starts; inside a pause → false, and the bar says when we write back.
  const paused = () => (view?.wait_until || 0) * 1000 > Date.now();
  const toTop = () => window.scrollTo({ top: 0, behavior: "smooth" });
  function pause(until) {
    if (view && until) view.wait_until = until;
    const on = paused(), bar = $(".waitbar");
    $("#hub").classList.toggle("paused", on);
    bar.hidden = !on;
    if (!on) return;
    const t = new Date(view.wait_until * 1000);
    $("span", bar).innerHTML = `<b>Sent. We write back within 24 hours.</b> New requests open again ${t.toLocaleDateString("en-US", { weekday: "short" })} ${t.toTimeString().slice(0, 5)}. Paying the deposit stays open.`;
    $(".ask").hidden = true; lane = null;
  }
  async function send(kind, text, project = "", extra = {}) {
    const money = kind === "ship" || kind === "invoice";          // accepting or paying never waits behind the 24 h hold
    if (paused() && !money) { pause(); toTop(); return false; }
    try {
      const r = await fetch("api/request", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, text, project, ...extra }) });
      const j = await r.json().catch(() => ({}));
      if (r.status === 429 && money) { alert("We already have this from you today. We write back within 24 hours."); return false; }
      if (r.status === 429) { pause(j.until); toTop(); return false; }
      if (!r.ok) { alert(j.error || "That didn't reach us. Try again."); return false; }
      pause(j.until); if (!money) toTop();
      return true;
    } catch { alert("Offline. Nothing was sent; try again."); return false; }
  }

  // a phase 2 proposal waiting on the client: their logo, then 01 deliverables · 02 timeline · 03 start the build
  // (the amount), then Accept now, pay later · Pay deposit through Stripe (delivery.yml invoice:, always live) · Request invoice
  // (any payment method), and in small
  // letters "Ask to change the scope": a comment per deliverable + new capabilities. Each answer is one request (send).
  // every section folds, set as a ledger row (the resume's read: number + title in a fixed column, the peek beside it,
  // hairlines between). No pills: an unread row nudges once as it scrolls in; opening it marks it read (this device).
  // The Required follow up bar counts what's been read.
  // device keys follow the project id, not its place in the list: a list that grows or reorders never moves a pick.
  const PK = () => `${view?.email || ""}.${view?.projects[+location.hash.slice(4)]?.id ?? location.hash.slice(4)}`;
  const SEENKEY = () => `rcai.seen.${PK()}`;
  const itSplit = (t) => { const [a, ...b] = String(t).split(" | "); return [a, b.join(" | ")]; };
  const flat = (t) => itSplit(t).filter(Boolean).join(": ");
  const dcard = (a, b, cls = "") => `<li${cls ? ` class="${cls}"` : ""}><b>${esc(a)}</b>${b ? `<span>${esc(b)}</span>` : ""}</li>`;
  const seen = () => { try { return JSON.parse(localStorage.getItem(SEENKEY()) || "[]"); } catch { return []; } };
  const fold = (k, n, title, peek, body) => { const r = seen().includes(k);
    return `<details class="part fold${r ? " read" : ""}" data-k="${k}"><summary><b><i>${String(n).padStart(2, "0")}</i>${title}</b><span class="pv">${peek}</span>
      <span class="cv" aria-hidden="true"></span></summary><div class="pb">${body}</div></details>`; };
  // Infrastructure and tools (2026-10-14, "simpler, more powerful"): one big $0, then `Name · Tag · note` as one quiet row each.
  const toolsHTML = (lines) => `<div class="infra"><div class="zero"><b>$0</b><small>to run, today</small></div>
    <ul>${lines.map((l) => { const [n, t = "", w = ""] = l.split(" · ");
      return `<li><b>${esc(n)}</b><em class="${/free/i.test(t) ? "free" : "up"}">${esc(t)}</em><small>${esc(w)}</small></li>`; }).join("")}</ul></div>`;
  // Ongoing support plans: custom to their needs. One question (AI agent or not?), three answers, one optional line, Send.
  const SUP = [["human", "Human support only", "A person answers, always"], ["hybrid", "Hybrid", "A person, with Y-chat taking the first pass"],
    ["agent", "Trained agent · Y-chat", "Y-chat, trained on your Hub, a person behind it"]];
  const supportHTML = (lines) => `${lines.map((l) => `<p class="supl">${esc(l)}</p>`).join("")}
    <form class="qcf"><p class="supq">Start by scoping your plan. Are you open to plans that include an AI agent, <b>Y-chat</b>?</p>
      <div class="supk">${SUP.map(([k, a, b]) => `<button type="button" class="sup" data-sup="${k}" aria-pressed="false"><b>${a}</b><small>${b}</small></button>`).join("")}</div>
      <textarea name="m" rows="2" maxlength="1500" placeholder="Anything we should know? Hours, response time, who should be covered (optional)"></textarea>
      <div class="ra-row"><button type="submit" class="ra-s">Scope my plan →</button></div></form>`;
  const isTools = (t) => /tool|infrastructure/i.test(t.title), isSup = (t) => /support/i.test(t.title);
  const termBody = (t) => isTools(t) ? toolsHTML(t.lines) : isSup(t) ? supportHTML(t.lines) : `<ul class="dl">${t.lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul>`;
  const termPeek = (t) => isTools(t) ? "$0 to run today" : isSup(t) ? "Custom to your needs" : /meeting|session/i.test(t.title) ? "Recommended 3–5 hours · $42 an hour"
    : /pricing/i.test(t.title) ? "Priced by feature · 13–15 deliverables a phase" : `${t.lines.length} points`;

  function scope(p) {
    const s = p.scope;
    const tl = (s.timeline || []).length
      ? `<ul class="tl">${s.timeline.map((t) => `<li><span>${esc(t.when)}</span>${esc(t.what)}</li>`).join("")}</ul>` : `<p class="mute">Set together on the first call.</p>`;
    const key = (a, label, off) => `<button type="button" class="sk ${a}"${off ? " disabled" : ""} data-ans="${a}" data-p="${esc(p.code || p.name)}" data-s="${esc(s.name)}">${label}</button>`;
    const ad = s.addons || [], picked = added();
    const secs = [
      ["scope", "Scope of work", `${s.items.length + picked.length} deliverables · add or modify them below`, `<ul class="dl sow">${delivHTML(s, picked)}</ul>
        <button type="button" class="modk"${lock() ? " disabled" : ""}>Add or modify deliverables →</button>`],
      // the picture in two halves, side by side (top · bottom of the same file); either half opens it full size
      ...(p.visual ? [["how", "How it works", "The diagram, start to finish", `<figure class="vis two">${["top", "bottom"].map((h, j) => `<a class="half" href="api/visual/${encodeURIComponent(p.id)}" target="_blank" rel="noopener"><img class="${h}" src="api/visual/${encodeURIComponent(p.id)}" alt="${esc(s.name)}: how it works, part ${j + 1}" loading="lazy"><i>${j + 1}</i></a>`).join("")}<figcaption><a href="api/visual/${encodeURIComponent(p.id)}" target="_blank" rel="noopener">Open full size</a></figcaption></figure>`]] : []),
      ["time", "Schedule", (s.timeline || []).length ? "3–4 weeks" : "", tl],
      ...(s.terms || []).map((t, j) => ["t" + j, esc(t.title), termPeek(t), termBody(t)]),
      ["pay", "Payment plan", payPeek(s, picked), `<div class="payrow">${payHTML(s, picked)}</div>`],
    ];
    const read = secs.filter(([k]) => seen().includes(k)).length;
    return `<div class="scope" data-n="${secs.length}"><div class="sh">${p.logo ? `<img class="logo" src="${esc(p.logo)}" alt="${esc(p.company || "")}">` : ""}
        <span class="cap">${esc(p.name)} · ${esc(s.name)}</span><span class="wait">Required follow up</span></div>
      <div class="actreq"><b>Required follow up</b><span>Phase 2 is ready. Take a look and pick what fits.</span><small class="rd">${read} of ${secs.length} sections read</small></div>
      <div class="adslot">${addsHTML(s, picked)}</div>
      ${secs.map(([k, t, pk, body], j) => fold(k, j + 1, t, pk, body)).join("")}
      <div class="holdslot">${holdHTML()}</div>
      <label class="ack${acked() ? " on" : ""}"><input type="checkbox"${acked() ? " checked" : ""}${lock() ? " disabled" : ""}>
        <span>I understand the pricing: the final cost may vary by ±15–20% of the estimated total.</span></label>
      <p class="actlbl"><i></i>Ready? Pick one</p>
      <div class="sks${lock() ? " frozen" : ""}">${key("accept", shipped() ? "Accepted · shipping" : closed() ? "Scope archived" : "Accept now, pay later", lock() || !acked())}<span class="stslot">${stripeHTML(s)}</span>${shipped() ? key("inv", "Request invoice") : ""}</div>
      <div class="shipslot"></div>
      <div class="endrow"><button type="button" class="scx" aria-expanded="false"${lock() ? " disabled" : ""}>${held() ? "Scope change in review" : shipped() ? "Scope locked · the build is shipping" : closed() ? "Scope archived · a different build is on its way" : "Ask to change the scope of the project"}</button>
        ${key("rebuild", "Request a different build · archive this scope", lock())}</div>
      <div class="rbslot"></div>
      <form class="scf" hidden>
        <ol class="steps"><li data-w="1">Write</li><li data-w="2">Review</li><li data-w="3">Questions</li><li data-w="4">Sent</li></ol>
        <div class="w" data-w="1">
          ${ad.length ? `<div class="swpk"><div class="adh"><b>The package</b><small class="few">only these switch on and off</small></div>
            <div class="adg">${ad.map((a, j) => `<button type="button" class="ad sw" data-a="${j}" aria-pressed="${picked.includes(j)}"${lock() ? " disabled" : ""}>
              <i class="tick">${icon("i-check")}</i><strong>${esc(a.title)}</strong><small>${esc(a.why)}</small></button>`).join("")}</div></div>` : ""}
          <p class="lede">Comment on any deliverable, or add a capability. Every note saves on this device as you type, so nothing is lost.
            When you press Save, a first reader checks each note is specific enough to build from: what, where, for whom.</p>
          <ol class="its">${s.items.map((t, j) => `<li><span>${esc(flat(t))}</span><textarea name="c${j}" rows="1" maxlength="800" placeholder="Comment on this one (optional)"></textarea></li>`).join("")}</ol>
          <label class="add"><span>+ Add a new capability</span><textarea name="add" rows="2" maxlength="1500" placeholder="What should it also do? Who uses it, when, and what do they see?"></textarea></label>
          <p class="stamp"></p>
          <p class="push" role="alert"></p>
          <button class="send2" type="submit">Save and continue<svg class="ico"><use href="#i-arrow"/></svg></button>
        </div>
        <div class="w" data-w="2" hidden>
          <p class="lede">Saved. This is exactly what we'll read. Check it once: when you send it to review, a second reader goes through it and comes back with a few questions before it reaches us.</p>
          <dl class="sum"></dl>
          <p class="push" role="alert"></p>
          <div class="row2"><button class="back" type="button" data-to="1">← Edit</button>
            <button class="send2" type="submit">Send to review<svg class="ico"><use href="#i-arrow"/></svg></button></div>
        </div>
        <div class="w" data-w="3" hidden>
          <p class="lede">Before it reaches us, a few questions. Short answers are fine. They turn your notes into something we can price and build.</p>
          <ol class="qs"></ol>
          <p class="push" role="alert"></p>
          <div class="row2"><button class="back" type="button" data-to="2">← Back</button>
            <button class="send2" type="submit">Send scope change<svg class="ico"><use href="#i-arrow"/></svg></button></div>
        </div>
        <div class="w" data-w="4" hidden>
          <p class="lede">Sent. We have your notes and answers. A person reads them and writes back within 24 hours with the updated scope.</p>
        </div>
      </form></div>`;
  }

  // one project = one small square: state, name, company, the stage track, and two small keys: git · railway.
  // The square itself does nothing on click. A git value "github.com/o/r · main" links to the repo; railway opens the dashboard.
  // Owned by <name> · <role> (delivery.yml owner:), set like a signature line on the square.
  const owned = (o) => o && o.name ? `<span class="own"><i>Owned by</i><b>${esc(o.name)}</b>${o.role ? `<small>${esc(o.role)}</small>` : ""}</span>` : "";
  // the project's HANDBOOK: one PDF (delivery.yml handbook:), behind login. It no longer sits on the square:
  // one small key pinned low right (#hbfab). Several handbooks (owner view) = the key opens a tiny list.
  const bookUrl = (p) => `api/handbook/${encodeURIComponent(p.id)}`;
  function fab(v) {
    const el = $("#hbfab"), bs = v.projects.filter((p) => p.handbook);
    el.hidden = !bs.length;
    if (!bs.length) { el.innerHTML = ""; return; }
    const face = `${icon("i-doc")}<span>Handbook</span>`;
    el.innerHTML = bs.length === 1
      ? `<a class="hbk" href="${bookUrl(bs[0])}" target="_blank" rel="noopener" title="${esc(bs[0].name)} · how your Hub works, start to finish">${face}</a>`
      : `<button type="button" class="hbk" aria-expanded="false">${face}</button><div class="hbl" hidden>${bs.map((p) =>
          `<a href="${bookUrl(p)}" target="_blank" rel="noopener">${esc(p.name)}</a>`).join("")}</div>`;
  }
  document.addEventListener("click", (e) => {
    const k = e.target.closest("#hbfab button.hbk"), l = $("#hbfab .hbl");
    if (!l) return;
    if (k) { l.hidden = !l.hidden; k.setAttribute("aria-expanded", String(!l.hidden)); }
    else if (!e.target.closest("#hbfab")) l.hidden = true;
  });
  const href = (k, v) => k === "git" ? "https://" + v.split(" ")[0].replace(/^https?:\/\//, "") : "https://railway.com/dashboard";
  function card(p, stages, i) {
    p.where = p.where || []; p.notices = p.notices || [];
    const track = stages.map((_, j) => `<i class="${j < p.stage ? "on" : j === p.stage ? "now" : ""}"></i>`).join("");
    const keys = p.where.filter((w) => w.k === "git" || w.k === "railway")
      .map((w) => `<a class="sq" href="${esc(href(w.k, w.v))}" target="_blank" rel="noopener" title="${esc(WHERE[w.k][1])}: ${esc(w.v)}">${icon(WHERE[w.k][0])}</a>`).join("");
    const sq = `<article class="proj">
      <div class="top"><span class="tag ${p.stage >= 3 ? "ok" : ""}">${esc(p.stage_label)}</span>${p.logo ? `<img class="plogo" src="${esc(p.logo)}" alt="">` : ""}</div>
      <h3>${esc(p.name)}</h3><span class="co">${esc(p.company)}</span>${owned(p.owner)}
      <div class="track" title="${esc(stages[p.stage] || "")}">${track}</div>
      <div class="foot">${keys}${p.can_change ? `<button type="button" class="sq ed" data-p="${esc(p.code || p.name)}" title="Edits, changes or concerns · back to you in 24 h">${icon("i-pen")}${p.notices.some((n) => LANE_OF[n.lane] === "changes") ? `<i class="dot"></i>` : ""}</button>` : ""}</div>
    </article>`;
    // a real phase 2 scope = ONE wide square, the same website: phase 1 left, phase 2 right (its key opens its own page).
    if (!p.scope) return sq;
    const inner = sq.slice(sq.indexOf(">") + 1, sq.lastIndexOf("</article>"))
      .replace(/<h3>.*?<\/h3><span class="co">.*?<\/span>(<span class="own">.*?<\/span>)?/, `<h3>Phase 1</h3>`).replace(/<img class="plogo"[^>]*>/, "");
    return `<article class="proj duo">
      <div class="dh">${p.logo ? `<img class="plogo" src="${esc(p.logo)}" alt="${esc(p.company || "")}">` : ""}<h3>${esc(p.name)}</h3><span class="co">${esc(p.company)}</span>${owned(p.owner)}</div>
      <div class="pane">${inner}</div>
      <div class="pane p2">
        <span class="tag bad">Ready for you</span>
        <h3>${esc(p.scope.name)}</h3><span class="co">New build · ${p.scope.items.length} items</span>
        <button type="button" class="p2go" data-i="${i}">See what's next →</button>
        <p class="dec">Your next build is waiting. One look, one click.</p>
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

  // the server's state_epoch (config.yml) outranks this device: a new epoch wipes every rcai.* key once.
  function epoch(e) {
    try {
      if (e && localStorage.getItem("rcai.epoch") !== String(e)) {
        Object.keys(localStorage).filter((k) => k.startsWith("rcai.")).forEach((k) => localStorage.removeItem(k));
        localStorage.setItem("rcai.epoch", String(e));
      }
    } catch {}
  }

  function hub(v) {
    epoch(v.epoch);
    view = v;
    $("#gate").hidden = true; $("#hub").hidden = false;
    const n = v.projects.length;
    // top of the hub: Hi, <first name>. The logo lives only on the project square; ⚙ sits beside the bell.
    $(".hi .nm").textContent = v.name || "";
    $(".gpop .cn").textContent = v.owner ? "Owner" : v.company || "";
    $(".gpop .em").textContent = v.email || "";
    $(".gpop .pwstate").textContent = v.own_pw ? "Your own password is set." : "Signed in with the shared code word.";
    $(".pwf [name=username]").value = v.email || "";
    $(".gpop .master").hidden = !v.owner;
    $('.opt[data-opt="pw"]').hidden = !v.pw_on;
    // the caption beside Your projects: owners only (a client's company is already on its square).
    $(".sh .co").textContent = v.owner ? `Owner view · ${n} projects · ${v.clients} clients` : "";
    // p.demo (demo_sent · pending_signature, set in 02_records.DEMO) lives under Your demos, the rest under Your projects. i stays the index in v.projects (the #p2-<i> page).
    const all = v.projects.map((p, i) => [p, i]);
    const real = all.filter(([p]) => !p.demo), demos = all.filter(([p]) => p.demo);
    $("#cards").innerHTML = real.length ? real.map(([p, i]) => card(p, v.stages, i)).join("") : `<div class="empty">No projects yet.</div>`;
    drawDemos();
    $(".ask select").innerHTML = v.projects.map((p) => `<option value="${esc(p.code || p.name)}">${esc(p.name)}</option>`).join("");
    badges(v);
    fab(v);
    route();
    pause();
  }

  // #p2-<i> = that project's phase 2 page; anything else = the hub. Browser back works.
  function route() {
    const m = location.hash.match(/^#p2-(\d+)$/), p = m && view && view.projects[+m[1]];
    const on = !!(p && p.scope);
    $("#home").hidden = on; $("#p2page").hidden = !on;
    $("#scopes").innerHTML = on ? scope(p) : "";
    if (on) { track("open", +m[1]); nudge(); }
    window.scrollTo({ top: 0 });
  }
  window.addEventListener("hashchange", () => { if (view && !$("#hub").hidden) route(); });

  function open(which, proj) {
    if (paused()) { pause(); return; }
    const form = $(".ask");
    const same = lane === which && !form.hidden && (!proj || form.project.value === proj);
    document.querySelectorAll(".tk").forEach((b) => b.setAttribute("aria-expanded", String(!same && b.dataset.lane === which)));
    if (same) { form.hidden = true; lane = null; return; }
    lane = which;
    form.hidden = false;
    form.project.hidden = !!LANES[which].free;
    form.msg.placeholder = LANES[which].ph;
    $("small", form).textContent = LANES[which].note || "Opens your email, filled in. A person replies.";
    if (proj) form.project.value = proj;
    form.msg.focus({ preventScroll: true });
  }

  document.querySelectorAll(".tk").forEach((b) => b.addEventListener("click", () => open(b.dataset.lane)));
  // the ghost keys beside a section title open the same one message window, at the top.
  document.querySelectorAll(".gk").forEach((b) => b.addEventListener("click", () => { open(b.dataset.lane); window.scrollTo({ top: 0 }); }));

  // ✎ on a square → the edits box with that project picked; Review Phase 2 → its own page.
  const onCards = (e) => {
    const rc = e.target.closest(".ed");
    if (rc) { open("changes", rc.dataset.p); window.scrollTo({ top: 0 }); return; }
    const b = e.target.closest(".p2go");
    if (b) location.hash = "p2-" + b.dataset.i;
  };
  $("#cards").addEventListener("click", onCards);
  $("#demos").addEventListener("click", onCards);

  // a demo square's own key: Request action → a box inside the square → Send (kind "action", that demo named)
  // → the key becomes "Give us 24 hours". Inside any 24 h pause every demo square shows the same quiet line.
  // Smart keys (5, pick any): one tap says the common ask; the box is for the rest. Either one is enough to send.
  const RA_KEYS = {
    demo: ["Open the scope", "Notify me with details", "Request changes", "Alternate build", "Book a walkthrough"],
    sign: ["Ready to sign", "Open the scope", "Request changes", "Alternate build", "Notify me with details"],
  };
  // Archive (device only, keyed by project id): the square leaves Your demos and joins ONE "Archived" square; Restore brings it back.
  const ARCKEY = "rcai.archived";
  const archived = () => { try { return JSON.parse(localStorage.getItem(ARCKEY) || "[]"); } catch { return []; } };
  const pid = (p) => String(p.id || p.code || p.name);
  let arcOpen = false;
  function drawDemos() {
    const v = view, arc = archived();
    const all = v.projects.map((p, i) => [p, i]).filter(([p]) => p.demo);
    const live = all.filter(([p]) => !arc.includes(pid(p))), gone = all.filter(([p]) => arc.includes(pid(p)));
    const arcKey = (p) => `<button type="button" class="ar-go" data-a="${esc(pid(p))}">Archive</button>`;
    let h = live.map(([p, i]) => card(p, v.stages, i).replace(/<\/article>\s*$/, `${raHTML(p, arcKey(p))}</article>`)).join("");
    if (gone.length) h += `<article class="arc"><button type="button" class="arc-t" aria-expanded="${arcOpen}"><span class="arc-l">Archived</span><span class="arc-n">${gone.length}</span></button>
      <ul class="arc-list"${arcOpen ? "" : " hidden"}>${gone.map(([p]) => `<li><span>${esc(p.name)}</span><button type="button" class="ar-back" data-a="${esc(pid(p))}">Restore</button></li>`).join("")}</ul></article>`;
    $("#demos").innerHTML = h || `<div class="empty">No demos yet. Ask for one, built on your own data.</div>`;
  }
  $("#demos").addEventListener("click", (e) => {
    const t = e.target.closest(".arc-t");
    if (t) { arcOpen = !arcOpen; drawDemos(); return; }
    const a = e.target.closest(".ar-go, .ar-back");
    if (!a) return;
    const id = a.dataset.a, arc = archived().filter((x) => x !== id);
    if (a.classList.contains("ar-go")) arc.push(id);
    try { localStorage.setItem(ARCKEY, JSON.stringify(arc)); } catch {}
    drawDemos();
  });
  const raHTML = (p, ar = "") => paused()
    ? `<div class="ra"><span class="ra-wait">Sent · give us 24 hours</span>${ar}</div>`
    : `<div class="ra"><button type="button" class="ra-go" data-p="${esc(p.code || p.name)}">Request action</button>${ar}
        <form class="ra-f" hidden><div class="ra-keys">${RA_KEYS[/signature/i.test(p.stage_label || "") ? "sign" : "demo"]
          .map((k) => `<button type="button" class="ra-k" aria-pressed="false">${esc(k)}</button>`).join("")}</div>
        <textarea name="m" rows="2" maxlength="1500" placeholder="Anything else? (optional)"></textarea>
        <div class="ra-row"><button type="button" class="ra-x">Cancel</button><button type="submit" class="ra-s">Send</button></div></form></div>`;
  $("#demos").addEventListener("click", (e) => {
    const k = e.target.closest(".ra-k");
    if (k) { k.setAttribute("aria-pressed", k.getAttribute("aria-pressed") === "true" ? "false" : "true"); return; }
    const go = e.target.closest(".ra-go"), x = e.target.closest(".ra-x");
    if (!go && !x) return;
    const ra = e.target.closest(".ra"), f = $(".ra-f", ra);
    f.hidden = !!x; $(".ra-go", ra).hidden = !x;
    if (go) f.m.focus({ preventScroll: true });
  });
  $("#demos").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, ra = f.closest(".ra"), p = $(".ra-go", ra).dataset.p;
    const picks = $$(".ra-k[aria-pressed=true]", f).map((b) => "• " + b.textContent);
    const t = [picks.join("\n"), f.m.value.trim()].filter(Boolean).join("\n\n");
    if (!t) { f.m.placeholder = "Pick a key or write a line."; f.m.focus(); return; }
    $(".ra-s", f).disabled = true;
    await send("action", t + sign(), p);
    if (paused()) drawDemos();
    if (!paused()) $(".ra-s", f).disabled = false;
  });

  // R-CAI plug-ins (under Your preferences): a square opens the one window, that plug-in named in the subject.
  let plug = "";
  $("#plugs").addEventListener("click", (e) => {
    const b = e.target.closest(".plug");
    if (!b) return;
    plug = b.dataset.plug;
    open("plug");
    $(".ask").msg.placeholder = `${plug}: what should it do for you?`;
    window.scrollTo({ top: 0 });
  });

  // add-ons (delivery.yml addon:, 3-5): FIRST on the page, NOT in the build, sold as one package. One key adds all of them:
  // they join the deliverables and the total moves (base + each add-on's price; the page never says what one costs).
  // Only "Ask to change the scope" switches them off and on, one by one. Kept on this device per client + project.
  const ADDKEY = () => `rcai.added.${PK()}`;
  function added() { try { return JSON.parse(localStorage.getItem(ADDKEY()) || "[]"); } catch { return []; } }
  const addNames = (s, idx) => idx.map((j) => (s.addons || [])[j]?.title).filter(Boolean);
  const money = (n) => "$" + n.toLocaleString("en-US");
  function bill(s, picked) {
    if (!s.price) return null;
    // the deposit is fixed (pct of the base build, never moves); only the total moves with the package
    // tax (delivery.yml tax:) is on the full phase and rides the second invoice; tot = the estimated total, tax in.
    const sub = s.price.base + picked.reduce((a, j) => a + ((s.addons || [])[j]?.p || 0), 0), dep = Math.round(s.price.base * s.price.pct / 100);
    const tax = Math.round(sub * (s.tax || 0) / 100), tot = sub + tax;
    return { sub, tax, tot, dep, rest: tot - dep };
  }
  const payPeek = (s, picked) => { const b = bill(s, picked); return b ? `${money(b.dep)} to start · estimated total ${money(b.tot)}` : ""; };
  function addsHTML(s, picked) {
    const ad = s.addons || [];
    if (!ad.length) return "";
    const h = lock(), why = held() ? "locked while your scope change is in review" : "locked · the build is shipping";
    if (picked.length) return `<div class="adds in"><span class="ok">${icon("i-check")}</span><b>In your build</b>
      <span>${addNames(s, picked).map(esc).join(" · ")}</span><small class="few">${h ? why : "change it in Ask to change the scope"}</small></div>`;
    return `<div class="adds${h ? " frozen" : ""}"><div class="adh"><b>The package · not in the build</b><span>All ${ad.length}, small on the bill.</span>
        <small class="few">${h ? why : "or select a few when you ask to change the scope"}</small></div>
      <div class="adg pkg">${ad.map((a) => `<div class="ad"><strong>${esc(a.title)}</strong><small>${esc(a.why)}</small></div>`).join("")}</div>
      <div class="adk"><button type="button" class="adgo"${h ? " disabled" : ""}>Add the package to my build →</button></div></div>`;
  }
  // a deliverable is `Title | one line` (delivery.yml): a card on the page, `Title: line` everywhere else (forms, emails)
  const delivHTML = (s, picked) => s.items.map((t) => dcard(...itSplit(t))).join("")
    + picked.map((j) => (s.addons || [])[j]).filter(Boolean).map((a) => dcard(a.title, a.why, "plus")).join("");
  function payHTML(s, picked) {
    const b = bill(s, picked);
    // the payment plan, start to finish: two invoices whatever is picked, then the estimated total, then his notes (payplan:)
    if (b) return `<ol class="pplan">
        <li><i>1</i><span><b>Deposit</b><small>Invoice 1 · fixed · due within 7 days of confirming</small></span><strong>${money(b.dep)}</strong></li>
        <li><i>2</i><span><b>Balance at go-live</b><small>Invoice 2 · the rest of the build, any add-ons${s.tax ? `, and ${s.tax}% tax on the full phase (${money(b.tax)})` : ""}</small></span><strong>${money(b.rest)}</strong></li>
        <li class="est"><i></i><span><b>Estimated total</b><small>Follows what is in your build</small></span><strong>${money(b.tot)}</strong></li></ol>
      ${(s.payplan || []).map((l) => `<p class="ppn${/^recommended/i.test(l) ? " rec" : ""}">${esc(l)}</p>`).join("")}`;
    return s.pay ? `<strong>${esc(s.pay.amount)}</strong><p>${esc(s.pay.what)}</p>` : "";
  }
  // the deposit never moves, so one invoice serves every build: delivery.yml `invoice: <link>`. ALWAYS live: never frozen.
  function stripeHTML(s) {
    const pl = s.pay_links || {}, link = pl["0"] || Object.values(pl)[0];
    if (link) return `<a class="sk stripe" href="${esc(link)}" target="_blank" rel="noopener">Pay deposit through Stripe →</a>`;
    return `<span class="sk stripe off">Pay deposit through Stripe${link ? "" : " · link on its way"}</span>`;
  }
  // a scope change sent to review holds the answer keys for 24 h: Accept now and Stripe freeze until we come back.
  const HOLDKEY = () => `rcai.hold.${PK()}`;
  function held() { const t = +(localStorage.getItem(HOLDKEY()) || 0); return t && Date.now() - t < 864e5 ? t : 0; }
  // Accept now, pay later → a second press, SHIP TODAY, confirms the build is OK. Then everything on the page locks
  // for good, except the two ways to pay (Stripe · Request invoice).
  const SHIPKEY = () => `rcai.ship.${PK()}`;
  const shipped = () => +(localStorage.getItem(SHIPKEY()) || 0);
  // Request a different build → a pre-prompt (close this proposal, ask for a new demo) → sent: the proposal closes for good. Paying stays open.
  const CLOSEKEY = () => `rcai.closed.${PK()}`;
  const closed = () => +(localStorage.getItem(CLOSEKEY()) || 0);
  const lock = () => held() || shipped() || closed();
  // "I understand the pricing" (±15–20%): Accept stays off until it is ticked. Stripe never waits on it.
  const ACKKEY = () => `rcai.ack.${PK()}`;
  const acked = () => +(localStorage.getItem(ACKKEY()) || 0);
  function holdHTML() {
    if (closed()) return `<div class="hold"><i></i><span><b>Scope archived. A different build is on its way.</b> We write back within 24 hours with a new demo.</span></div>`;
    if (shipped()) return `<div class="hold ok"><i></i><span><b>Accepted. The build is shipping.</b> The deposit is due before go-live: Stripe, or ask for an invoice by another method.</span></div>`;
    return held() ? `<div class="hold"><i></i><span><b>Scope change in review.</b> We're back to you within 24 hours. Accept opens again with the updated scope. Paying the deposit stays open.</span></div>` : "";
  }
  function freeze(label) {
    $(".holdslot").innerHTML = holdHTML();
    $(".shipslot").innerHTML = ""; $(".rbslot").innerHTML = "";
    $(".sks").classList.add("frozen");
    const a = $(".sks .sk.accept"); a.disabled = true; a.classList.remove("shipgo", "armed");
    if (shipped()) a.textContent = "Accepted · shipping"; if (closed()) a.textContent = "Scope archived";
    const ck = $(".ack input"); if (ck) ck.disabled = true;
    $$(".modk").forEach((m) => (m.disabled = true));
    // once shipped, Request invoice joins the row for good: the second way to pay
    if (shipped() && !$(".sks .sk.inv")) $(".sks").insertAdjacentHTML("beforeend", `<button type="button" class="sk inv" data-ans="inv">Request invoice</button>`);
    const rb = $(".sk.rebuild"); if (rb) rb.disabled = true;
    const s = view.projects[+location.hash.slice(4)].scope;
    // the package locks with the answer key: no adding, no switching, no scope change. Paying stays open.
    $(".adslot").innerHTML = addsHTML(s, added());
    $$(".ad.sw").forEach((b) => (b.disabled = true));
    const x = $(".scx"); x.disabled = true; x.textContent = label;
    const f = $(".scf"); if (f && shipped()) f.hidden = true;
  }
  function setHold() {
    try { localStorage.setItem(HOLDKEY(), String(Date.now())); } catch {}
    freeze("Scope change in review");
  }
  const rebuildHTML = () => `<div class="ship rb"><p><b>Archive this scope and request a different build?</b> Phase 2 as written is set aside. We come back within 24 hours with a new demo.</p>
    <textarea rows="2" maxlength="1500" placeholder="What should the new build do instead?"></textarea>
    <div class="row2"><button type="button" class="sk back0">Keep this scope</button><button type="button" class="rbgo">Archive it and request a new demo →</button></div></div>`;
  // Accept now, pay later is ONE key, pressed twice: the first press turns it into SHIP TODAY with Request invoice beside it.
  const shipHTML = () => `<div class="ship"><p><b>Is the build OK as it stands?</b> Press <b>Ship today</b> and we start this week; the deposit is due within 7 days. Or ask for an invoice first.</p>
    <div class="row2"><button type="button" class="sk back0">Not yet</button></div></div>`;
  function arm(on) {
    const a = $(".sks .sk.accept");
    a.classList.toggle("shipgo", on); a.classList.toggle("armed", on);
    a.textContent = on ? "Ship today →" : "Accept now, pay later";
    $(".sks .sk.inv:not(.keep)")?.remove();
    if (on) a.insertAdjacentHTML("afterend", `<button type="button" class="sk inv" data-ans="inv">Request invoice</button>`);
    $(".shipslot").innerHTML = on ? shipHTML() : "";
  }
  function setAdded(picked) {
    const s = view.projects[+location.hash.slice(4)].scope;
    picked = [...new Set(picked)].sort();
    localStorage.setItem(ADDKEY(), JSON.stringify(picked));
    $(".adslot").innerHTML = addsHTML(s, picked);
    $(".dl.sow").innerHTML = delivHTML(s, picked);
    const pv = $('details.fold[data-k="scope"] .pv'); if (pv) pv.textContent = `${s.items.length + picked.length} deliverables · add or modify them below`;
    const pp = $('details.fold[data-k="pay"] .pv'); if (pp) pp.textContent = payPeek(s, picked);
    $(".payrow").innerHTML = payHTML(s, picked);
    $(".stslot").innerHTML = stripeHTML(s);
    $$(".ad.sw").forEach((b) => b.setAttribute("aria-pressed", String(picked.includes(+b.dataset.a))));
  }

  $("#scopes").addEventListener("click", async (e) => {
    if (lock() && e.target.closest(".adgo, button.ad.sw, .scx, .sk.accept, .sk.rebuild, .shipgo, .rbgo, .modk")) return;
    if (paused() && e.target.closest(".scx, .modk, button.sk:not(.back0):not(.accept):not(.inv), .rbgo")) { pause(); toTop(); return; }
    if (e.target.closest(".modk")) { $(".scx").click(); $(".scf").scrollIntoView({ behavior: "smooth", block: "start" }); return; }
    const sp = e.target.closest(".sup");
    if (sp) { $$(".sup").forEach((x) => x.setAttribute("aria-pressed", String(x === sp && sp.getAttribute("aria-pressed") !== "true"))); return; }
    if (e.target.closest(".stripe:not(.off)")) { track("stripe"); return; }
    if (e.target.closest(".adgo")) { track("add_pkg"); setAdded((view.projects[+location.hash.slice(4)].scope.addons || []).map((_, j) => j)); return; }
    const a = e.target.closest("button.ad.sw");
    if (a) {
      const j = +a.dataset.a, set = new Set(added());
      track(set.has(j) ? "addon_off" : "addon_on");
      set.has(j) ? set.delete(j) : set.add(j);
      setAdded([...set]);
      return;
    }
    const x = e.target.closest(".scx");
    if (x) {
      const f = $(".scf"), on = f.hidden;
      f.hidden = !on; x.setAttribute("aria-expanded", String(on)); tries = 0;
      f.querySelectorAll(".push").forEach((m) => (m.textContent = ""));
      if (on) { track("scope_open"); step(f, 1); restore(f); f.querySelector("textarea").focus(); }
      return;
    }
    if (e.target.closest(".back0")) { track("not_yet"); if (!lock()) arm(false); $(".rbslot").innerHTML = ""; return; }
    const b = e.target.closest("button.sk, .shipgo, .rbgo");
    if (!b || b.disabled) return;
    // first press on Accept only asks; the same key, now SHIP TODAY, is the yes
    if (b.dataset.ans === "rebuild") { track("rebuild_ask"); if (!lock()) arm(false); $(".rbslot").innerHTML = rebuildHTML(); $(".rbslot textarea").focus({ preventScroll: true }); return; }
    if (b.classList.contains("rbgo")) {
      const ta = $(".rbslot textarea"), t = ta.value.trim();
      if (!t) { ta.placeholder = "One line is enough: what should the new build do instead?"; ta.focus(); return; }
      const pp = view.projects[+location.hash.slice(4)];
      if (!(await send("rebuild", `${pp.scope.name} · ${pp.code || pp.name}\n\nClose this proposal and send us a new demo.\n\nWhat the new build should do instead:\n${t}` + sign(), pp.code || pp.name))) return;
      track("rebuild");
      try { localStorage.setItem(CLOSEKEY(), String(Date.now())); } catch {}
      freeze("Scope archived · a different build is on its way");
      return;
    }
    if (b.dataset.ans === "accept" && !b.classList.contains("armed")) { if (!acked()) return; track("accept"); $(".rbslot").innerHTML = ""; arm(true); return; }
    const p = view.projects[+location.hash.slice(4)], s = p.scope, pk = added(), bl = bill(s, pk), adn = addNames(s, pk);
    const plus = (adn.length ? `\n\nAlso in the build:\n${adn.map((t) => "· " + t).join("\n")}` : "")
      + (bl ? `\n\nEstimated total ${money(bl.tot)}${s.tax ? ` (incl. ${s.tax}% tax)` : ""} · deposit ${money(bl.dep)}.` : "")
      + (acked() ? "\nPricing understood: the final cost may vary by ±15–20% of the estimated total." : "");
    const tag = `${s.name} · ${p.code || p.name}`;
    if (b.classList.contains("shipgo")) {
      if (!(await send("ship", `${tag}\n\nWe accept this proposal and the build is OK as it stands. Ship today. We'll pay the deposit within 7 days.` + plus + sign(),
        p.code || p.name, bl ? { total: bl.tot, deposit: bl.dep } : {}))) return;
      track("ship");
      try { localStorage.setItem(SHIPKEY(), String(Date.now())); } catch {}
      freeze("Scope locked · the build is shipping");
      return;
    }
    if (b.dataset.ans === "inv" && await send("invoice", `${tag}\n\n` +
      `Please send us an invoice for the deposit${bl ? ` (${money(bl.dep)})` : ""}.\n\nWe'd like to pay by (keep one):\n· Bank transfer / ACH\n· Card\n· Check\n· Other: \n\nBilling name and address:\n` + plus + sign(), p.code || p.name)) track("invoice");
  });

  $("#scopes").addEventListener("submit", async (e) => {
    if (!e.target.classList.contains("qcf")) return;
    e.preventDefault(); e.stopImmediatePropagation();
    const f = e.target, t = f.m.value.trim(), pp = view.projects[+location.hash.slice(4)];
    const pick = $(".sup[aria-pressed=true] b", f)?.textContent || "";
    if (!pick && !t) { f.m.placeholder = "Pick one of the three, or write a line."; return f.m.focus(); }
    if (await send("support", `Support plan · ${pp.name}\n\nOpen to: ${pick || "not picked"}\n\n${t || "-"}` + sign(), pp.code || pp.name)) {
      track("support"); f.reset(); $$(".sup", f).forEach((x) => x.setAttribute("aria-pressed", "false"));
      $(".ra-s", f).textContent = "Sent · give us 24 hours"; $(".ra-s", f).disabled = true;
    }
  }, true);
  $("#scopes").addEventListener("change", (e) => {
    if (!e.target.closest(".ack input")) return;
    const on = e.target.checked;
    try { on ? localStorage.setItem(ACKKEY(), String(Date.now())) : localStorage.removeItem(ACKKEY()); } catch {}
    track(on ? "ack" : "ack_off");
    $(".ack").classList.toggle("on", on);
    const a = $(".sks .sk.accept"); if (!lock()) { a.disabled = !on; if (!on) arm(false); }
  });
  $("#scopes").addEventListener("toggle", (e) => {
    const d = e.target;
    if (!d.matches?.("details.fold") || !d.open || d.classList.contains("read")) return;
    const k = d.dataset.k, all = new Set(seen()); all.add(k);
    try { localStorage.setItem(SEENKEY(), JSON.stringify([...all])); } catch {}
    d.classList.add("read");
    track("read");
    const sc = $(".scope"); $(".rd", sc).textContent = `${$$("details.fold.read", sc).length} of ${sc.dataset.n} sections read`;
  }, true);
  let io = null;
  function nudge() {
    io?.disconnect();
    io = new IntersectionObserver((es) => es.forEach((x) => { if (x.isIntersecting) { x.target.classList.add("hey"); io.unobserve(x.target); } }), { threshold: .9 });
    $$("#scopes details.fold:not(.read)").forEach((d) => io.observe(d));
  }

  // scope change, four faces: 1 Write (autosaves on this device) → Save = the cheap reader (api/scope check, mock today)
  // marks thin notes, pushes back twice at most → 2 Review (exactly what we'll read) → Send to review = the second
  // reader (api/scope review) ALWAYS comes back with 2-3 questions → 3 Questions → Send = the filled-in email → 4 Sent.
  let tries = 0, qs = [], saveT = 0;
  const P2 = () => +location.hash.slice(4);
  const KEY = () => `rcai.scope.${PK()}`;
  const hhmm = () => new Date().toTimeString().slice(0, 5);
  const notesOf = (f) => ({ items: Object.fromEntries([...f.querySelectorAll(".its textarea")].map((t, j) => [j, t.value.trim()]).filter(([, v]) => v)), add: f.add.value.trim() });
  const stamp = (f, t) => { $(".stamp", f).textContent = t ? `✓ Saved on this device · ${t}` : ""; };
  const keep = (f) => { const at = hhmm(); try { localStorage.setItem(KEY(), JSON.stringify({ notes: notesOf(f), at })); } catch {} stamp(f, at); };
  function step(f, n) {
    f.querySelectorAll(".w").forEach((w) => (w.hidden = w.dataset.w !== String(n)));
    f.querySelectorAll(".steps li").forEach((li) => (li.className = +li.dataset.w < n ? "done" : +li.dataset.w === n ? "on" : ""));
    f.dataset.step = n;
  }
  function restore(f) {
    let d = null;
    try { d = JSON.parse(localStorage.getItem(KEY()) || "null"); } catch {}
    if (!d) return stamp(f, "");
    Object.entries(d.notes.items || {}).forEach(([j, v]) => { if (f["c" + j]) f["c" + j].value = v; });
    f.add.value = d.notes.add || ""; stamp(f, d.at);
  }
  $("#scopes").addEventListener("input", (e) => {
    const f = e.target.closest(".scf");
    if (!f || f.dataset.step !== "1") return;
    clearTimeout(saveT); saveT = setTimeout(() => keep(f), 400);
  });
  $("#scopes").addEventListener("click", (e) => {
    const b = e.target.closest(".back");
    if (b) step(b.closest(".scf"), +b.dataset.to);
  });
  const ask = async (stage, f) => {
    const r = await fetch("api/scope", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage, i: P2(), notes: notesOf(f), tries }) });
    if (!r.ok) throw new Error("offline");
    return r.json();
  };
  $("#scopes").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, n = +f.dataset.step, w = $(`.w[data-w="${n}"]`, f);
    const p = view.projects[P2()], s = p.scope, msg = $(".push", w), btn = $(".send2", w);
    btn.disabled = true; msg.textContent = "";
    try {
      if (n === 1) {
        const r = await ask("check", f);
        keep(f);
        f.querySelectorAll(".its textarea, [name=add]").forEach((t) => t.classList.toggle("weak", (r.weak || []).includes(t.name === "add" ? "add" : t.name.slice(1))));
        msg.textContent = r.say || "";
        if (!r.ok) { if (r.weak) tries++; f.querySelector("textarea.weak")?.focus(); return; }
        track("scope_saved");
        const ns = notesOf(f);
        $(".sum", f).innerHTML = Object.entries(ns.items).map(([j, v]) => `<dt>${esc(flat(s.items[j]))}</dt><dd>${esc(v)}</dd>`).join("")
          + (ns.add ? `<dt class="nw">New capability</dt><dd>${esc(ns.add)}</dd>` : "");
        step(f, 2);
      } else if (n === 2) {
        qs = (await ask("review", f)).questions || [];
        track("scope_check");
        $(".qs", f).innerHTML = qs.map((q, j) => `<li><span>${esc(q)}</span><textarea name="q${j}" rows="2" maxlength="800" placeholder="Your answer"></textarea></li>`).join("");
        step(f, 3);
        f.q0?.focus();
      } else if (n === 3) {
        if (qs.some((_, j) => !f["q" + j].value.trim())) { msg.textContent = "Answer each one, even briefly. \"Not needed\" is an answer."; return; }
        const ns = notesOf(f);
        const body = Object.entries(ns.items).map(([j, v]) => `• ${flat(s.items[j])}\n  → ${v}`).join("\n\n");
        const qa = qs.map((q, j) => `Q: ${q}\nA: ${f["q" + j].value.trim()}`).join("\n\n");
        const bl = bill(s, added());
        if (!(await send("scope", `${s.name} · ${p.name}\n\nThe package in the build: ${addNames(s, added()).join(" · ") || "none"}\n\nComments on the deliverables:\n\n${body || "-"}\n\nNew capabilities:\n${ns.add || "-"}\n\nReview questions:\n\n${qa}` + sign(),
          p.code || p.name, bl ? { total: bl.tot, deposit: bl.dep } : {}))) { msg.textContent = "Not sent. Your notes are still here."; return; }
        track("scope_sent");
        try { localStorage.removeItem(KEY()); } catch {}
        step(f, 4);
        setHold();
      }
    } catch { msg.textContent = "That didn't reach us. Your notes are saved on this device; try again."; }
    finally { btn.disabled = false; }
  });

  // preferences: one chip per question (tap again to clear), a review if they want, one send.
  document.querySelectorAll(".chips").forEach((g) => g.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const on = b.getAttribute("aria-pressed") !== "true";
    g.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b && on)));
  }));
  $("#prefs").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    const pick = (q) => $(`.chips[data-q="${q}"] [aria-pressed="true"]`, f)?.textContent || "-";
    const body = `Rating: ${pick("rating")}/5\nUpdates: ${pick("updates")}\nRecommend: ${pick("recommend")}\n\nReview:\n${f.review.value.trim() || "-"}`;
    if (await send("prefs", body + sign())) { f.reset(); $$("[aria-pressed]", f).forEach((x) => x.setAttribute("aria-pressed", "false")); }
  });
  $("#fb").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget;
    if (await send("feedback", f.msg.value.trim() + sign())) f.reset();
  });

  $(".ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget, k = lane, text = f.msg.value.trim();
    if (!text) return f.msg.focus();
    if (await send(k, (k === "plug" ? `Plug-in: ${plug}\n\n` : "") + text + sign(), LANES[k].free ? "" : f.project.value)) f.reset();
  });

  $(".gear").addEventListener("click", (e) => {
    const pop = $(".gpop"), on = pop.hidden;
    pop.hidden = !on; e.currentTarget.setAttribute("aria-expanded", String(on));
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".gear, .gpop")) { $(".gpop").hidden = true; $(".gear").setAttribute("aria-expanded", "false"); }
  });

  // change password: the current one (or the shared code word) + the new one twice. Saved = a new pw_N column
  // in users.csv (05_users); this tab stays signed in, every other session ends.
  $('.opt[data-opt="pw"]').addEventListener("click", (e) => {
    const f = $(".pwf"), on = f.hidden;
    f.hidden = !on; e.currentTarget.setAttribute("aria-expanded", String(on));
    if (on) { f.reset(); f.username.value = view?.email || ""; $(".msg", f).textContent = ""; f.current.focus(); }
  });
  $(".pwf").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget, msg = $(".msg", f), btn = $("button", f);
    const say = (text, cls) => { msg.textContent = text; msg.className = "msg " + cls; };
    if (f.new.value !== f.again.value) return say("The two new passwords don't match.", "bad");
    btn.disabled = true;
    try {
      const r = await fetch("api/password", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current: f.current.value, new: f.new.value }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) return say(j.error || "That didn't save.", "bad");
      f.reset(); f.username.value = view?.email || "";
      say("Saved. Use it next time you sign in.", "ok");
      $(".gpop .pwstate").textContent = "Your own password is set.";
    } catch { say("Offline. Try again.", "bad"); }
    finally { btn.disabled = false; }
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
    if (which === "signup") which = "login";  // sign up closed until its data pipeline exists (2026-10-14)
    ["login", "signup", "sent"].forEach((id) => ($("#" + id).hidden = id !== which));
    document.querySelectorAll(".seg button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.face === (which === "sent" ? "signup" : which))));
    const first = $(`#${which} input`);
    if (first) first.focus({ preventScroll: true });
    history.replaceState(null, "", which === "signup" ? "#signup" : location.pathname);
  }
  document.querySelectorAll("[data-face]").forEach((el) => el.addEventListener("click", (e) => { e.preventDefault(); face(el.dataset.face); }));

  $("#signup").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.currentTarget, btn = $("button[type=submit]", f);
    btn.disabled = true;
    try {
      const r = await fetch("api/signup", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: f.name.value, company: f.company.value, email: f.email.value, need: f.need.value }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok || r.status === 429) { f.reset(); face("sent"); }
      else alert(j.error || "That didn't reach us. Try again.");
    } catch { alert("Offline. Nothing was sent; try again."); }
    finally { btn.disabled = false; }
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
    $(".gpop").hidden = true; $(".pwf").hidden = true; $("#login").reset(); gate();
  });

  me().then((v) => (v ? hub(v) : gate()));
})();
