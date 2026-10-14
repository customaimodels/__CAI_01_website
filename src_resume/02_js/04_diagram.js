// The how-it-works diagram: 140 small rings (the knot's own motif, not arrows) reading
// disorder -> compression -> order, left to right. Generated so the page stays light.
(() => {
  const svg = document.getElementById("hiw-svg");
  if (!svg) return;
  const NS = "http://www.w3.org/2000/svg";
  const W = 1200, H = 260, N = 140;
  const rng = (seed => () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; })(7);
  const ring = (cx, cy, r, color, op) => {
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", cx); c.setAttribute("cy", cy); c.setAttribute("r", r);
    c.setAttribute("fill", "none"); c.setAttribute("stroke", color);
    c.setAttribute("stroke-width", 2); c.setAttribute("opacity", op);
    svg.appendChild(c);
  };
  const pale1 = "#c9cdd6", pale2 = "#9aa1ad", ribbon = "#0f172a", order = "#d9a62c";

  for (let i = 0; i < N; i++) {
    const t = i / N;
    let cx, cy, col, op, r = 6;
    if (t < 0.34) {
      // scatter: loose, two pale tones, left third
      cx = 20 + rng() * (W * 0.30);
      cy = 20 + rng() * (H - 40);
      col = i % 2 ? pale1 : pale2; op = 0.8;
    } else if (t < 0.64) {
      // ribbon: tight horizontal band, three rings high, middle third
      const col3 = Math.floor((i - N * 0.34) / ((N * 0.30) / 40));
      cx = W * 0.34 + (col3 % 40) * ((W * 0.30) / 40) + rng() * 4;
      cy = H / 2 + ((i % 3) - 1) * 16 + rng() * 3;
      col = ribbon; op = 0.9; r = 7;
    } else {
      // ordered rows, fan out evenly, right third, accent colour
      const idx = i - Math.floor(N * 0.64);
      const perRow = 12, row = Math.floor(idx / perRow), colN = idx % perRow;
      cx = W * 0.68 + colN * ((W * 0.30) / perRow);
      cy = 30 + row * 26;
      col = order; op = 0.9; r = 6;
    }
    ring(cx, cy, r, col, op);
  }
})();
