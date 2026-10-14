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
