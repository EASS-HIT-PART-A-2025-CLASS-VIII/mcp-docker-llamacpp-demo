# MCP YouTube Podcast Analyzer

This repo glues three things together so you can summarize YouTube podcasts from your laptop:

1. A local llama.cpp server (runs the LLM, no API keys needed)
2. Docker’s MCP gateway (gives you DuckDuckGo search + Playwright browsing + YouTube transcripts)
3. A single Python script (`script.py`) that searches for people, grabs transcripts, and prints a pretty Rich table

If you can follow a recipe, you can run this project.

---

## Quick Start (do this in order)

> Tip: all commands run from the repo root.

1. **Install the tools you need once**
   - [Docker Desktop 4.29+](https://docs.docker.com/desktop/) with the MCP extension: `docker extension install docker/mcp`
   - [uv](https://docs.astral.sh/uv/getting-started/installation/) (or Python 3.12+ if you insist)
2. **Start the local LLM (one terminal tab)**
   ```bash
   scripts/start_llm_server.sh
   ```
   Wait until you see the server listening on port 1234.
3. **Start the MCP gateway (second terminal tab)**
   ```bash
   scripts/start_mcp_gateway.sh
   ```
   This command enables DuckDuckGo, Playwright, and YouTube Transcript MCP servers if they’re not already on.
4. **Smoke-test the connections (third tab)**
   ```bash
   uv run python script.py --smoke-test
   ```
   You should see two green checkmarks (LLM + MCP). Fix anything red before moving on.
5. **Run the analyzer for real**
   ```bash
   uv run python script.py \
     --people "Lex Fridman" "Andrew Huberman" \
     --per-person 2
   ```
   The script prints a table with topics + insights for each video it managed to summarize.

That’s it. Change the names or bump `--per-person` whenever you want.

---

## How everything connects (picture!)

```mermaid
flowchart LR
    User[[You in a terminal]] -->|run scripts/run_analyzer.sh| Client[Python analyzer\n(script.py + uv)]
    subgraph Docker Containers
      LLM[llama.cpp server\n: port 1234]:::box -->|summaries back| Client
      Gateway[MCP gateway\n: port 8080]:::box --> Client
      Gateway --> Tools
      Tools[Built-in tools\nDuckDuckGo · Playwright · YouTube Transcript]:::box
    end

    classDef box fill:#e6f3ff,stroke:#0077cc,color:#111,rx:6,ry:6;
```

- The analyzer is just a Python script you run locally; it talks to two Docker containers over simple HTTP requests (think “send text → get text back”).
- Container #1 is the llama.cpp server (your local LLM). Container #2 is Docker’s MCP gateway, which bundles search/browsing/transcript tools.
- When the script runs, it asks the tools for YouTube transcripts, then hands that text to the local LLM for a summary, and finally prints a friendly table.

No fancy networking knowledge needed: every arrow above is “talk over localhost with text”.

---

## How the repo is organized

```
.
├── script.py                # Rich terminal client (now has helpful CLI flags)
├── pyproject.toml / uv.lock # uv metadata; run `uv run ...` and it "just works"
├── scripts/
│   ├── start_llm_server.sh  # llama.cpp Docker wrapper (Gemma 3 270M by default)
│   ├── start_mcp_gateway.sh # Enables DuckDuckGo + Playwright + YouTube MCP tools
│   └── run_analyzer.sh      # Convenience wrapper around `uv run python script.py`
├── docs/                    # Drop diagrams or notes here if you make them
└── README.md                # What you’re reading
```

---

## Important Flags and Environment Variables

| What | Default | How to change |
| ---- | ------- | ------------- |
| LLM endpoint | `http://127.0.0.1:1234/v1` | `export LLM_ENDPOINT=...` or `--llm-endpoint URL` |
| MCP endpoint | `http://localhost:8080/mcp` | `export MCP_ENDPOINT=...` or `--mcp-endpoint URL` |
| People to search | `Sam Altman Elon Musk Donald Trump` | `--people "Name1" "Name2"` |
| Videos per person | `2` | `--per-person 3` |
| Search breadth | `15` | `--max-search-results 20` |
| Health check only | off | add `--smoke-test` |

Both helper scripts accept standard environment overrides (e.g., `PORT`, `MODEL_REPO`, `SERVERS`) if you want to tweak them.

---

## Troubleshooting Cheatsheet

| Symptom | Likely fix |
| ------- | ---------- |
| `✗ LLM connection failed` | Make sure `scripts/start_llm_server.sh` is still running; check Docker Desktop logs. |
| `✗ MCP gateway unreachable` | Rerun `scripts/start_mcp_gateway.sh`; confirm `docker mcp server ls` shows the three servers enabled. |
| `No podcasts were summarized` | Try different names, bump `--max-search-results`, or wait for DuckDuckGo to return fresher links. |
| Docker says the MCP command is unknown | Install/enable the MCP extension: `docker extension install docker/mcp`. |

Run `uv run python script.py --smoke-test` whenever you’re unsure if both services are alive.

---

## Why we like this setup

- 100% local inference — no OpenAI keys, just a llama.cpp container pulling the Gemma 3 270M model from Hugging Face.
- Docker MCP gateway gives you ready-made tools (search, headless browser, YouTube transcripts) through one HTTP endpoint.
- `script.py` is intentionally tiny, well-commented, and uses Rich so you can see exactly what’s happening.

If you build diagrams, save them under `docs/` so everyone can find them later.
