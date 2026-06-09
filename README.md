# SyncSnake 🐍

**SyncSnake** is an autonomous multi-agent research tool that hunts sync licensing opportunities for independent musicians — scraping agencies, music supervisors, brief platforms, grants, festivals, ad agencies, production music libraries, and songwriting competitions in real time.

It is one of **Medusa's snakes** — a standalone module of the larger [Medusa](https://github.com/TheLazyAI) music intelligence platform, which gives independent artists everything they need to know about their song and where to take it.

---

## How It Works

SyncSnake runs a two-tier multi-agent pipeline powered by **Google Gemini** and built using the code-first **Google Cloud Agent Development Kit (ADK)** (part of the Google Cloud Agent Builder ecosystem) with live **Google Search grounding**:

```
Orchestrator Scout (ADK LlmAgent)
  └─ Google Search grounding (real-time music industry landscape)
  └─ Arize Phoenix: query historical sub-agent performance
  └─ Planner LLM: generate 5 targeted queries + viability gate
        └─ Sub-Agent 1: search → scrape → extract (ADK extractor) → faithfulness
        └─ Sub-Agent 2: search → scrape → extract (ADK extractor) → faithfulness
        └─ Sub-Agent N: ...
  └─ Merge & deduplicate (w/ Faithfulness Gate) → catalogue.json / catalogue.md / dashboard.html
```

### The Viability Gate

Before spawning any sub-agent, the orchestrator's planner evaluates whether each planned search is worth running — using both the live scout results and **Arize Phoenix trace data** from past runs. Topics the planner marks `viable: false` are skipped entirely, saving API calls on dead-end searches.

### Arize Phoenix Integration

Every LLM call, grounding query, and sub-agent run is traced to **Arize Phoenix** with full OpenInference attributes. The orchestrator also *reads back* from Phoenix via the `arize-phoenix-client` — sub-agent performance history feeds directly into the planning step, creating a self-improving feedback loop.

Run with `--trace` to launch the Phoenix UI alongside the agent:
```bash
python scrape_agent_adk.py --trace
```

---

## Output Categories

| Category | Description |
|---|---|
| Sync Licensing Agencies | Reps, submission guidelines, contacts |
| Music Supervisors | Film/TV/ad supervisors, submission policies |
| Brief & Pitch Platforms | Open brief boards (Musicbed, Marmoset, etc.) |
| Music Grants & Funding | FACTOR, Canada Council, regional programs |
| Showcase Festivals | Application windows, fees, requirements |
| Indie Video Game Projects | Studios seeking composers |
| Advertising Agencies | Creative directors, music contacts |
| Production Music Libraries | Contributor submission status, payout models |
| Songwriting Competitions | Deadlines, entry fees, prizes |
| Restricted Resources | Paid/gated sources worth investigating |

Results are saved to `catalogue.json`, `catalogue.md`, and an interactive `dashboard.html`.

---

## Setup

**Requirements:** Python 3.12+, a Gemini API key.

```bash
# Clone and enter
git clone https://github.com/TheLazyAI/syncsnake.git
cd syncsnake

# Create a venv and install dependencies
python -m venv venv
source venv/bin/activate
pip install arize-phoenix arize-phoenix-client opentelemetry-sdk opentelemetry-exporter-otlp

# Add your Gemini key
echo "GEMINI_API_KEY=your_key_here" > .env
```

---

## Usage

```bash
# Automatic run (scout & plan)
python scrape_agent_adk.py

# Custom focus (e.g. genre or location)
python scrape_agent_adk.py -q "lo-fi hip hop indie electronic"

# With Arize Phoenix tracing UI
python scrape_agent_adk.py --trace

# Scheduled background runner (every N hours)
python periodic_runner.py --daemon 6
```

Open `dashboard.html` in a browser to explore results.

---

## Part of Medusa

SyncSnake is designed to plug into **Medusa**, a larger music analysis platform for independent artists. Once Medusa knows everything about a track, SyncSnake finds where to place it.

---

*Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com) · Arize Track*
