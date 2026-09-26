// Railway entrypoint. Landing page only, for now.
//
// static/ is the web root. Same URL rules as 01_CAI_website, so links carry
// over when the other routes move in:
//   /foo serves foo.html, /foo.html redirects to /foo, /foo/ redirects to /foo
//
// Not mounted yet — each comes in as its own app.use(), one at a time:
//   /cascades   Cascade Arana
//   /rcai       R-CAI client hub
//   /api/chat   "Describe your use case" (needs ANTHROPIC_API_KEY + retrieval)
//   /articles, /deal-execution-copilot

import express from "express";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";

const here = dirname(fileURLToPath(import.meta.url));
const STATIC_DIR = join(here, "static");
const PORT = process.env.PORT || 3000;

const app = express();
app.disable("x-powered-by");

app.use((req, res, next) => {
  const p = req.path;
  if (p.length > 1 && p.endsWith("/")) return res.redirect(301, p.slice(0, -1));
  if (p.endsWith(".html") && p !== "/index.html") return res.redirect(301, p.slice(0, -5));
  if (!p.includes(".") && p !== "/" && existsSync(join(STATIC_DIR, `${p}.html`))) {
    req.url = `${p}.html`;
  }
  next();
});

app.use(express.static(STATIC_DIR));

app.use((_req, res) => res.status(404).send("Not found"));

app.listen(PORT, () => console.log(`[server] listening on ${PORT}`));
