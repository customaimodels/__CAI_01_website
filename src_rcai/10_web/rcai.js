// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
// The hub: one small key top right (request build) + the bell for every notice. Top of the body: logo · Hi, John · ⚙ (details · change password · sign out; owners + master table).
// Phase 1 edits: a small ✎ key on the square (only when signed or paid, can_change from 02_records) → one box, answered within 24 h.
// Phase 2 changes are scope changes, asked on its own page: a comment per deliverable + new capabilities, pushed twice to be specific.
// Ghost keys beside the titles: "+ New project or phase" (Your projects) · "Request a demo" (Your demos), same window.
// Body: projects as small squares (+ a quiet Phase 2 square when a scope waits → its proposal: logo · deliverables · timeline · pay · Accept · Ask changes · Deny) · preferences (survey + review) · feedback.
// Every send opens a filled-in email: there is no request queue yet.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const MAIL = "customaimodels@gmail.com";
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

  const icon = (id) => `<svg class="ico"><use href="#${id}"/></svg>`;
  const sign = () => `\n\n— ${view ? view.full || view.name : ""}${view && view.company ? ", " + view.company : ""}`;
  const mail = (subject, body) => { location.href = `mailto:${MAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`; };

  // a phase 2 proposal waiting on the client: their logo, then 01 deliverables · 02 timeline · 03 start the build
  // (the amount), then Accept now, pay later · Pay deposit through Stripe (delivery.yml invoice:) · Decline, and in small
  // letters "Ask to change the scope": a comment per deliverable + new capabilities. Each answer opens a filled-in email.
  function scope(p) {
    const s = p.scope;
    const part = (n, title, body) => `<div class="part"><b><i>0${n}</i>${title}</b><div>${body}</div></div>`;
    const items = `<ul>${s.items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
    const tl = (s.timeline || []).length
      ? `<ul class="tl">${s.timeline.map((t) => `<li><span>${esc(t.when)}</span>${esc(t.what)}</li>`).join("")}</ul>` : `<p class="mute">Set together on the first call.</p>`;
    const pay = `<div class="payrow">${s.pay ? `<strong>${esc(s.pay.amount)}</strong><p>${esc(s.pay.what)}</p>` : ""}</div>`;
    const key = (a, label) => `<button type="button" class="sk ${a}" data-ans="${a}" data-p="${esc(p.code || p.name)}" data-s="${esc(s.name)}">${label}</button>`;
    // add-ons FIRST (delivery.yml addon:): not in the build, small on the bill. Picked before any price shows;
    // the page never carries their price -- it is quoted on its own small invoice, approved before anything is billed.
    // Sold as ONE package (all ticked by default); small letters let them take a few instead.
    const ad = s.addons || [], picked = addPicked(ad.length);
    const adds = ad.length ? `<div class="adds"><div class="adh"><b>The package · not in the build</b><span>${ad.length > 1 ? `All ${ad.length}, small on the bill.` : "Small on the bill."}</span>
          ${ad.length > 1 ? `<small class="few">or select a few · tap one to take it out</small>` : ""}</div>
        <div class="adg pkg">${ad.map((a, j) => `<button type="button" class="ad" data-a="${j}" aria-pressed="${picked.includes(j)}">
          <i class="tick">${icon("i-check")}</i><strong>${esc(a.title)}</strong><small>${esc(a.why)}</small></button>`).join("")}</div>
        <div class="adk"><button type="button" class="adgo">${addLabel(picked, ad.length)}</button>
          <span class="adn">Quoted on its own small invoice. Nothing is billed until you approve it.</span></div></div>` : "";
    return `<div class="scope"><div class="sh">${p.logo ? `<img class="logo" src="${esc(p.logo)}" alt="${esc(p.company || "")}">` : ""}
        <span class="cap">${esc(p.name)} · ${esc(s.name)}</span><span class="wait">Waiting on you</span></div>
      ${adds}${part(1, "Deliverables", items)}${part(2, "Timeline", tl)}${part(3, "Start the build", pay)}
      <div class="sks">${key("accept", "Accept now, pay later")}
        ${s.pay_link ? `<a class="sk stripe" href="${esc(s.pay_link)}" target="_blank" rel="noopener">Pay deposit through Stripe →</a>` : `<span class="sk stripe off">Pay deposit through Stripe · link on its way</span>`}
        ${key("deny", "Decline")}</div>
      <button type="button" class="scx" aria-expanded="false">Ask to change the scope of the project</button>
      <form class="scf" hidden>
        <ol class="steps"><li data-w="1">Write</li><li data-w="2">Review</li><li data-w="3">Questions</li><li data-w="4">Sent</li></ol>
        <div class="w" data-w="1">
          <p class="lede">Comment on any deliverable, or add a capability. Every note saves on this device as you type, so nothing is lost.
            When you press Save, a first reader checks each note is specific enough to build from: what, where, for whom.</p>
          <ol class="its">${s.items.map((t, j) => `<li><span>${esc(t)}</span><textarea name="c${j}" rows="1" maxlength="800" placeholder="Comment on this one (optional)"></textarea></li>`).join("")}</ol>
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
          <p class="lede">Sent. Your notes and answers are in your email, addressed to us. A person reads them and replies within 24 hours with the updated scope.</p>
        </div>
      </form></div>`;
  }

  // one project = one small square: state, name, company, the stage track, and two small keys: git · railway.
  // The square itself does nothing on click. A git value "github.com/o/r · main" links to the repo; railway opens the dashboard.
  // Owned by <name> · <role> (delivery.yml owner:), set like a signature line on the square.
  const owned = (o) => o && o.name ? `<span class="own"><i>Owned by</i><b>${esc(o.name)}</b>${o.role ? `<small>${esc(o.role)}</small>` : ""}</span>` : "";
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

  // add-ons: a pick is kept on this device per client + project; "Add … to my build" sends the picks (the filled-in email).
  // Accept carries them too, so a fast yes still lands them in the build.
  const ADDKEY = () => `rcai.addons.${view?.email || ""}.${+location.hash.slice(4)}`;
  // nothing stored yet = the whole package is in.
  function addPicked(n) {
    try { const v = localStorage.getItem(ADDKEY()); if (v) return JSON.parse(v); } catch {}
    return [...Array(n || $$(".ad").length).keys()];
  }
  const addLabel = (picked, n) => picked.length === n && n > 1 ? "Add the package to my build →"
    : picked.length ? `Add ${picked.length === 1 ? "this one" : picked.length} to my build →` : "Add the package to my build →";
  const addNames = (s, idx) => idx.map((j) => (s.addons || [])[j]?.title).filter(Boolean);

  const ANSWER = { accept: "Accept now, pay later", deny: "Decline" };
  $("#scopes").addEventListener("click", (e) => {
    const a = e.target.closest("button.ad");
    if (a) {
      const j = +a.dataset.a, set = new Set(addPicked());
      set.has(j) ? set.delete(j) : set.add(j);
      const picked = [...set].sort();
      localStorage.setItem(ADDKEY(), JSON.stringify(picked));
      a.setAttribute("aria-pressed", String(set.has(j)));
      $(".adgo").innerHTML = addLabel(picked, $$(".ad").length);
      return;
    }
    if (e.target.closest(".adgo")) {
      const p = view.projects[+location.hash.slice(4)], s = p.scope;
      let picked = addPicked();
      if (!picked.length) picked = (s.addons || []).map((_, j) => j);
      localStorage.setItem(ADDKEY(), JSON.stringify(picked));
      $$(".ad").forEach((b) => b.setAttribute("aria-pressed", String(picked.includes(+b.dataset.a))));
      $(".adgo").innerHTML = `Added ✓ · ${picked.length} in your build`;
      $(".adgo").classList.add("done");
      mail(`[R-CAI] ${s.name} · Add to my build · ${p.name}`,
        `Please add to ${s.name}:\n${addNames(s, picked).map((t) => "· " + t).join("\n")}\n\nSend me the small invoice for these to approve.` + sign());
      return;
    }
    const x = e.target.closest(".scx");
    if (x) {
      const f = $(".scf"), on = f.hidden;
      f.hidden = !on; x.setAttribute("aria-expanded", String(on)); tries = 0;
      f.querySelectorAll(".push").forEach((m) => (m.textContent = ""));
      if (on) { step(f, 1); restore(f); f.querySelector("textarea").focus(); }
      return;
    }
    const b = e.target.closest("button.sk");
    if (!b) return;
    const lead = { accept: "We accept this proposal. We'll pay the deposit later.", deny: "We decline this proposal." }[b.dataset.ans];
    const p = view.projects[+location.hash.slice(4)], adn = b.dataset.ans === "accept" && p ? addNames(p.scope, addPicked()) : [];
    const plus = adn.length ? `\n\nAlso in the build:\n${adn.map((t) => "· " + t).join("\n")}` : "";
    mail(`[R-CAI] Phase 2 · ${b.dataset.s} · ${ANSWER[b.dataset.ans]} · ${b.dataset.p}`, lead + plus + sign());
  });

  // scope change, four faces: 1 Write (autosaves on this device) → Save = the cheap reader (api/scope check, mock today)
  // marks thin notes, pushes back twice at most → 2 Review (exactly what we'll read) → Send to review = the second
  // reader (api/scope review) ALWAYS comes back with 2-3 questions → 3 Questions → Send = the filled-in email → 4 Sent.
  let tries = 0, qs = [], saveT = 0;
  const P2 = () => +location.hash.slice(4);
  const KEY = () => `rcai.scope.${view?.email || ""}.${P2()}`;
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
        const ns = notesOf(f);
        $(".sum", f).innerHTML = Object.entries(ns.items).map(([j, v]) => `<dt>${esc(s.items[j])}</dt><dd>${esc(v)}</dd>`).join("")
          + (ns.add ? `<dt class="nw">New capability</dt><dd>${esc(ns.add)}</dd>` : "");
        step(f, 2);
      } else if (n === 2) {
        qs = (await ask("review", f)).questions || [];
        $(".qs", f).innerHTML = qs.map((q, j) => `<li><span>${esc(q)}</span><textarea name="q${j}" rows="2" maxlength="800" placeholder="Your answer"></textarea></li>`).join("");
        step(f, 3);
        f.q0?.focus();
      } else if (n === 3) {
        if (qs.some((_, j) => !f["q" + j].value.trim())) { msg.textContent = "Answer each one, even briefly. \"Not needed\" is an answer."; return; }
        const ns = notesOf(f);
        const body = Object.entries(ns.items).map(([j, v]) => `• ${s.items[j]}\n  → ${v}`).join("\n\n");
        const qa = qs.map((q, j) => `Q: ${q}\nA: ${f["q" + j].value.trim()}`).join("\n\n");
        mail(`[R-CAI] Phase 2 · ${s.name} · Change the scope · ${p.name}`,
          `Comments on the deliverables:\n\n${body || "-"}\n\nNew capabilities:\n${ns.add || "-"}\n\nReview questions:\n\n${qa}` + sign());
        try { localStorage.removeItem(KEY()); } catch {}
        step(f, 4);
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
    mail(`[R-CAI] ${LANES[lane].title}${lane === "plug" ? " · " + plug : LANES[lane].free ? "" : " · " + f.project.value}`, f.msg.value.trim() + sign());
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
    $(".gpop").hidden = true; $(".pwf").hidden = true; $("#login").reset(); gate();
  });

  me().then((v) => (v ? hub(v) : gate()));
})();
