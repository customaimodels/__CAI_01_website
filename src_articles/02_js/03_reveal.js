// Entrance motion: the hero's masked headline, then a staggered reveal per section. Nothing else performs.
// `.in` is toggled directly on each moving element (never on a parent only) so the transition is
// unambiguously tied to the element whose property actually changes.
(() => {
  const spans = document.querySelectorAll(".hero-title .line span");
  const heroExtra = document.querySelectorAll(".standfirst, .hero-actions");
  requestAnimationFrame(() => {
    spans.forEach(s => s.classList.add("in"));
    setTimeout(() => heroExtra.forEach(e => e.classList.add("in")), 700);
  });

  const singles = document.querySelectorAll(".reveal");
  const groups = document.querySelectorAll(".reveal-stagger");
  if (!("IntersectionObserver" in window)) {
    singles.forEach(t => t.classList.add("in"));
    groups.forEach(g => [...g.children].forEach(c => c.classList.add("in")));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      if (e.target.classList.contains("reveal-stagger")) {
        [...e.target.children].forEach(c => c.classList.add("in"));
      } else {
        e.target.classList.add("in");
      }
      io.unobserve(e.target);
    });
  }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });
  // threshold 0, not a fraction: the whole article body is one .reveal, and 18% of a tall body
  // never fits a short window, so it stayed invisible (article 05, 2026-10-17).
  singles.forEach(t => io.observe(t));
  groups.forEach(t => io.observe(t));
})();
