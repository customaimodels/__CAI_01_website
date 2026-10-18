/* INTRO (2026-10-18): ghost9, once per visit. The head script sets html.intro only when
   sessionStorage has no cai_intro; this mounts the clip, opens the page as the white leaves,
   and never holds the page longer than 1.8 s (autoplay blocked, slow network, error). */
(() => {
  const H = document.documentElement;
  if (!H.classList.contains("intro")) return;
  const box = document.createElement("div");
  box.id = "intro";
  box.className = "intro-layer";
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = '<video muted autoplay playsinline preload="auto" src="03_img/10_intro.mp4"></video>';
  const iris = document.createElement("div");
  iris.id = "intro-iris";
  iris.className = "intro-layer";
  document.body.append(iris, box);
  const v = box.querySelector("video");
  let done = false;
  const open = () => {
    if (done) return;
    done = true;
    try { sessionStorage.setItem("cai_intro", "1"); } catch (e) {}
    H.classList.add("intro-open");
    setTimeout(() => { box.remove(); iris.remove(); H.classList.remove("intro", "intro-play", "intro-open"); }, 3200);
  };
  v.addEventListener("playing", () => H.classList.add("intro-play"));
  v.addEventListener("timeupdate", () => { if (v.currentTime >= 0.12) open(); });
  v.addEventListener("ended", open);
  v.addEventListener("error", open);
  box.addEventListener("click", open);
  addEventListener("keydown", open, { once: true });
  setTimeout(open, 1800);
  const p = v.play();
  if (p && p.catch) p.catch(open);
})();
