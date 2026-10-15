// The bar gets its rule once the page moves. Blocks enter once, then stay still. ?still = no entrance (captures).
(() => {
  const bar = document.getElementById("bar");
  const set = () => bar && bar.classList.toggle("solid", scrollY > 8);
  addEventListener("scroll", set, { passive: true });
  set();
  // In-page links glide only once the page has settled; before that, restore / #anchor landing must be instant.
  addEventListener("load", () => requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.add("glide"))));
  if (/[?&]still\b/.test(location.search) || !("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("js");
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".belt .grp li, .belt .cai, .hub-ops li").forEach((li, k) => li.style.setProperty("--k", li.closest(".hub-ops") ? [...li.parentNode.children].indexOf(li) : k));   // belt marks 25ms · hub rows 40ms
  document.querySelectorAll(".urail .ut").forEach((t, k) => t.style.setProperty("--k", k));   // gallery 35ms, left to right
  document.querySelectorAll(".rv").forEach((el) => io.observe(el));
})();

/* bar: the phone menu (Esc closes, a link closes, focus goes in and comes back) + Solutions marked while #build is on screen */
(()=>{const bar=document.getElementById("bar"),b=bar&&bar.querySelector(".mnu"),s=document.getElementById("mnu");if(!b||!s)return;
 const set=o=>{s.hidden=!o;b.setAttribute("aria-expanded",String(o));b.setAttribute("aria-label",o?"Close menu":"Open menu");
  if(o)s.querySelector("a").focus({preventScroll:true})};
 b.addEventListener("click",()=>set(s.hidden));
 s.addEventListener("click",e=>{if(e.target.closest("a"))set(false)});
 addEventListener("keydown",e=>{if(e.key==="Escape"&&!s.hidden){set(false);b.focus()}});
 matchMedia("(min-width:981px)").addEventListener("change",e=>{if(e.matches)set(false)});
 const sol=bar.querySelector('.nv a[href="#build"]'),blk=document.getElementById("build");
 if(sol&&blk&&"IntersectionObserver" in window)new IntersectionObserver(([e])=>sol.classList.toggle("on",e.isIntersecting),{rootMargin:"-40% 0px -50% 0px"}).observe(blk)})();

/* footer key + Y_VAULT button: 0000 = straight into the vault; empty = the vault's own PIN gate */
(()=>{const f=document.getElementById("vkey");if(!f)return;const i=f.querySelector("input");
 f.addEventListener("submit",async e=>{e.preventDefault();const pin=i.value.trim();if(!pin){location.href="/y-vault/";return}f.classList.remove("no");
  try{const r=await fetch("/y-vault/api/login",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({pin})});
   if(r.ok){location.href="/y-vault/";return}}catch(_){}
  i.value="";f.classList.add("no")})})();

/* build: hovering a supporting card lights its station in the big card's map (pointer only; the map reads fine without it) */
(()=>{const b=document.getElementById("build");if(!b||!matchMedia("(hover:hover)").matches)return;
 b.querySelectorAll("[data-cap]").forEach(t=>{const n=b.querySelector('[data-node="'+t.dataset.cap+'"]');if(!n)return;
  t.addEventListener("pointerenter",()=>n.classList.add("on"));t.addEventListener("pointerleave",()=>n.classList.remove("on"))})})();
