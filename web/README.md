# Slang Playground (web)

The browser playground behind **https://slang-playground.vercel.app**.

- `index.html` — static UI (no build step): editor, example programs, mode
  selector, output pane.
- `api/run.py` — a Vercel Python serverless function. `POST {source, mode}` →
  `{ok, text}`, where `mode` is `run` (bytecode VM), `bytecode`, `ast`, or `c`.
  Guards: 20k-char source limit, 2M-instruction limit, no file/network access.
- `slang/` — a vendored snapshot of the package (kept in sync with the repo
  root) so the function has zero install step and a fast cold start.

Deploy: `cd web && vercel deploy --prod`.
