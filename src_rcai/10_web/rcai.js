// R-CAI: one call decides which face shows. Signed in → the hub; not → the gate.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const day = (iso) => { const d = new Date(iso + "T12:00:00"); return isNaN(d) ? iso : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  function card(p, stages) {
    // the gold line runs from Seed to the bean; Runs sits past the line's end (80%)
    const pct = (p.stage / (stages.length - 1)) * 80;
    const track = stages.map((s, i) => i === p.stage
      ? `<div class="st now"><img src="bean.svg" alt="">${s}</div>`
      : `<div class="st ${i < p.stage ? "on" : ""}">${s}</div>`).join("");
    const tag = `<span class="tag ${p.demo ? "pending" : p.stage >= 3 ? "gold" : ""}">${esc(p.stage_label)}</span>`;
    const dates = p.dates.map((d) => `<dt>${esc(d.k)}</dt><dd>${esc(day(d.v))}</dd>`).join("");
    const ask = `mailto:customaimodels@gmail.com?subject=${encodeURIComponent((p.code || p.name) + " — next phase")}`;
    return `<article class="row">
      <div><span class="code">${esc(p.code)}</span><h3>${esc(p.name)}</h3>
        <span class="kind">${esc(p.company)}${p.kind ? " · " + esc(p.kind) : ""}</span>
        ${p.note ? `<p>${esc(p.note)}</p>` : ""}</div>
      <div><div class="state">${tag}${p.phase ? `<span class="phase">${esc(p.phase)}</span>` : ""}</div>
        <div class="track" aria-label="Stage ${p.stage + 1} of ${stages.length}: ${esc(stages[p.stage])}">
          <span class="fill" style="width:${pct}%"></span>${track}</div></div>
      <div class="side">${dates ? `<dl>${dates}</dl>` : ""}
        <div class="go">${p.link ? `<a class="live" href="${esc(p.link)}" target="_blank" rel="noopener">Open live ↗</a>` : ""}<a href="${ask}">Ask about the next phase →</a></div></div>
    </article>`;
  }

  function hub(v) {
    $("#gate").hidden = true; $("#hub").hidden = false;
    $(".who").innerHTML = `<b>${esc(v.full || v.name)}</b><br>${esc(v.role || "")}${v.company ? " · " + esc(v.company) : ""}`;
    $(".co").textContent = v.owner ? "Owner view · every hub" : v.company || "";
    $(".greet").innerHTML = `Good ${part}, <em>${esc(v.name)}</em>.`;
    const n = v.projects.length;
    $(".sub").textContent = v.owner
      ? `${n} projects across ${v.clients} clients. What each client sees, all in one place.`
      : `${n} project${n === 1 ? "" : "s"} on record, read straight from our ledger and updated as we work.`;
    const building = v.projects.filter((p) => p.stage >= 1 && p.stage <= 2).length;
    const done = v.projects.filter((p) => p.stage >= 3).length;
    $(".tiles").innerHTML = `<div><span>Projects</span><b>${n}</b></div><div><span>In build</span><b>${building}</b></div><div><span>Delivered</span><b>${done}</b></div>`;
    const groups = {};
    v.projects.forEach((p) => (groups[p.company] ??= []).push(p));
    const order = Object.keys(groups);
    $("#cards").innerHTML = n
      ? order.map((co) => `<div class="group"><div class="ghead"><h2>${esc(co)}</h2><span>${groups[co].length} project${groups[co].length === 1 ? "" : "s"}</span></div>
          ${groups[co].map((p) => card(p, v.stages)).join("")}</div>`).join("")
      : `<div class="empty">No projects on your hub yet. Write to customaimodels@gmail.com.</div>`;
  }

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
