// The header turns paper once the dark hero has scrolled past. Nothing else moves.
(() => {
  const bar = document.getElementById("bar");
  const hero = document.querySelector(".hero");
  if (!bar || !hero) return;
  const set = () => bar.classList.toggle("light", hero.getBoundingClientRect().bottom <= bar.offsetHeight);
  addEventListener("scroll", set, { passive: true });
  set();
})();
