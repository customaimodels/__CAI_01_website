// The bar gets its rule once the page moves. Blocks enter once, then stay still. ?still = no entrance (captures).
(() => {
  const bar = document.getElementById("bar");
  const set = () => bar && bar.classList.toggle("solid", scrollY > 8);
  addEventListener("scroll", set, { passive: true });
  set();
  if (/[?&]still\b/.test(location.search) || !("IntersectionObserver" in window)) return;
  document.documentElement.classList.add("js");
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".rv").forEach((el) => io.observe(el));
})();

/* footer key: the vault's own gate checks it; in = open the vault */
(()=>{const f=document.getElementById("vkey");if(!f)return;const i=f.querySelector("input");
 f.addEventListener("submit",async e=>{e.preventDefault();const pin=i.value.trim();if(!pin)return;f.classList.remove("no");
  try{const r=await fetch("/y-vault/api/login",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({pin})});
   if(r.ok){location.href="/y-vault/";return}}catch(_){}
  i.value="";f.classList.add("no")})})();
