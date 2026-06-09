# SyncSnake — ADK / Agent Builder Migration Handoff (2026-06-09)

> Supersedes the older `HANDOFF.md` (which predates the Agent Builder pivot).
> Local reference, untracked. Deadline: **June 11, 2026, 2pm PDT.**

---
## ✅ SESSION 3 (2026-06-09 later pm) — Option B END-TO-END VERIFIED + first full traced run

**The integrated MCP loop now works end to end, and the full traced pipeline ran clean.**

**Bug found & fixed — `get-prompt` returned a JSON wrapper, not the template.** Old
`load_faithfulness_prompt_via_phoenix_mcp()` asked the LLM to *echo* the ~1500-char template
verbatim ("return ONLY that text"); the model re-serialized it lossily, `json.loads` in
`_extract_prompt_text` failed, and the whole `{"description":...}` blob fell through as the
"instruction" (test asserted `startswith("SYNCSNAKE FAITHFULNESS EVALUATOR")` → FAIL).
**Fix (3 surgical edits in `scrape_agent_adk.py`):**
- `_mcp_text_payload(response)` — pulls text out of an MCP `function_response`
  (`{'content':[{'type':'text','text':...}],'isError':...}`).
- `_run_capturing_tool(agent, prompt, tool_name)` — sibling of `_run`; iterates the event
  stream and returns the **named tool's `function_response` text** (the genuine, byte-exact MCP
  output) instead of the LLM's final text. Agent still issues the call → still a traced span.
- `load_faithfulness_prompt_via_phoenix_mcp()` rewired to use it; agent instruction simplified to
  "call get-prompt … then reply 'done'." Result: template now arrives byte-exact (1095 chars,
  starts with the sentinel) and drives the eval.

**Verified this session:**
- `/tmp/test_mcp_loop.py` → **ALL PASS**: `mcp_sourced=True`, instruction starts with sentinel,
  GROUNDED case→1.0, FABRICATED case→0.0, writeback ok.
- **Full guarded run `scrape_agent_adk.py -q "North America" --trace` (exit 0, 14 ADK calls).**
  Validator✓ → traced MCP seed+fetch✓ → scout → planner approved 5 NA sub-agents → all 5
  scraped/extracted/scored → merge → **5 faithfulness scores written back**. Faithfulness eval is
  doing real work: scores 0.83/0.40/0.33/0.28/0.11, correctly flagging fabricated entries
  (Soundstripe, Music Xray, Bank Robber Music…). **Advisory only — still does NOT gate the merge**
  (open decision from Session-1 DATA NOTE stands).
- **Phoenix UI evidence confirmed** in project `sync-licensing-agent`: `execute_tool get-prompt`
  span (the partner-MCP runtime call), `agent_run [phoenix_mcp/validator/scout/planner]`,
  `agent_run [extractor]`×5, `agent_run [faithfulness]`×5, `invocation [syncsnake-adk]`×14, plus
  `call_llm`/`GenerateContent`. Dataset `syncsnake_faithfulness` grew 1→**6** examples.
- **`--trace` gotcha:** its embedded `px.launch_app()` can't bind `:4317` when a Phoenix is
  already running (logs a scary `RuntimeError: Failed to bind to address [::]:4317` + a wall of
  `FD from fork parent` lines). **Harmless** — spans still export to the existing collector and
  land in the UI. Verified.

**Data safety:** catalogue + search_history were snapshotted pre-run to
`/tmp/syncsnake_prerun_20260609_164802`, the NA run output saved to `/tmp/syncsnake_NArun_output`,
then the working tree **restored to the clean baseline** (catalogue.json == catalogue.backup.json
again). The NA run absorbed mostly-ungrounded entries (esp. agencies 0.11) — the one well-grounded
gain was **music_libraries (+17, scored 0.83)**, worth cherry-picking if a real broadening is wanted.

**Next steps unchanged from here:** submission essentials — README ADK framing + documented
entrypoint, demo video (<3 min, show the ADK run + the Phoenix spans above + dashboard),
merge branch → main, Devpost form (Arize track). `requirements.txt` already fixed (Session-1).

---
## ⏩ SESSION 2 ADDENDUM (2026-06-09 pm) — Option B is BUILT (code complete, end-to-end run still pending)

User's steer this session: *"we don't want MCP to be decorative — I want whatever gives me a real chance at winning."* So Option B was implemented in full. **All edits are in `scrape_agent_adk.py`; it compiles, imports, and all new symbols resolve.** The detailed design sketch lower down ("NEXT UP — Option B") is now the *as-built* record, not a TODO.

**What was built (the decorative Mintlify docs-MCP is GONE; replaced by the real `@arizeai/phoenix-mcp` runtime server, stdio/npx, `--baseUrl :6006`):**
- `FAITHFULNESS_TEMPLATE` — real grounded-hallucination eval prompt, sentinel first line `SYNCSNAKE FAITHFULNESS EVALUATOR (v1)` (used to validate the registry returned *our* text). It's the canonical copy: seeded into Phoenix **and** the in-code degradation fallback.
- `_seed_faithfulness_prompt()` — raw `mcp` ClientSession `upsert-prompt` (idempotent provisioning; deterministic, no LLM round-trip).
- `load_faithfulness_prompt_via_phoenix_mcp()` — **THE traced runtime MCP call**: ADK `LlmAgent` + `MCPToolset(StdioConnectionParams(...))` does `get-prompt`. Agent-mediated *on purpose* — a raw `mcp` call would NOT be captured by `GoogleADKInstrumentor`.
- `_extract_prompt_text()` — digs the verbatim template out of get-prompt's chat-message JSON (`template.messages[0].content[0].text`) or returns inner text.
- `load_faithfulness_instruction()` — reachability-gated: `:6006` up → seed → fetch → use (returns `mcp_sourced=True`); else built-in fallback. **Load-bearing:** the fetched text becomes the eval agent's `instruction` via the new `make_faithfulness_agent()` factory — no more 500-char decorative prefix.
- **Truncation bug fixed:** eval source window `combined[:2000]` → `combined[:12000]`; every sub-agent now also records `_faithfulness` {topic,query,score,explanation,source_chars}. Still **advisory only — never gates merges.**
- `record_faithfulness_examples_via_phoenix_mcp()` — writes each score back to a `syncsnake_faithfulness` Phoenix dataset via `add-dataset-examples` (closes the loop). Raw `mcp` for reliable structured writes.
- Module docstring + `--trace` banner updated (agent spawns phoenix-mcp itself; no separate terminal).

**Gotchas discovered this session (don't re-derive):**
- **Phoenix strips hyphens from prompt names** → the name MUST be `syncsnake_faithfulness_evaluator` (underscores). A hyphenated `get-prompt` 404s.
- `get-prompt` returns the template nested inside chat-message JSON (not a bare string).
- ADK 1.33 exports both `MCPToolset` and `McpToolset` (aliases); `StdioConnectionParams(server_params=StdioServerParameters(...), timeout=...)`.

**Verified so far:** ✓ compile/import; ✓ phoenix-mcp lists 27 tools; ✓ raw `upsert-prompt`→`get-prompt` round-trip (the `syncsnake_faithfulness_evaluator` prompt is already seeded in the running Phoenix). **NOT yet run:** the integrated `load_faithfulness_instruction()` (agent-mediated fetch → eval-driving → writeback) and the full `-q "Berlin" --trace` pipeline. The isolated loop test was written + queued but the run was paused before spending Gemini calls.

**Live environment state for next session:**
- **Phoenix is RUNNING in background on :6006** (nohup, log `/tmp/phoenix_serve.log`). Stop with `lsof -ti:6006 | xargs kill`.
- **Catalogue is UNMUTATED** — still the clean baseline (`catalogue.json` == `catalogue.backup.json`). Extra safety copy at `catalogue.optionb.bak.json`.
- Ready-to-run isolated test: `/Users/maryann/sonic/.venv/bin/python /tmp/test_mcp_loop.py` (~2 Gemini calls, no catalogue mutation — confirms seed→traced fetch→eval drives→writeback). Probes: `/tmp/mcp_probe.py`, `/tmp/mcp_roundtrip2.py`.

**Next steps, in order:** (1) run `/tmp/test_mcp_loop.py` to confirm the integrated loop; (2) guarded full run — back up catalogue, `scrape_agent_adk.py -q "Berlin" --trace`, confirm in the Phoenix UI: the `get-prompt` MCP span, the eval spans, AND the `syncsnake_faithfulness` dataset, then restore catalogue; (3) submission essentials (README/entrypoint, merge→main, demo video, Devpost).

---

## Why this work exists (the eligibility gap)
The Rapid Agent Hackathon requires the agent be **powered by Gemini AND built within
Google Cloud Agent Builder AND integrate a partner MCP** (Arize, our track).
SyncSnake had Gemini ✓ and the Arize Phoenix MCP ✓ but used a **hand-rolled asyncio
orchestrator on the raw `google-genai` SDK — NOT Agent Builder.** That was the gap.

**Organizer ruling (confirmed 2026-06-09):** code-first **ADK** (Agent Development Kit)
is an explicitly valid Agent Builder path — no visual console needed. For the Arize
track specifically they said code-first ADK satisfies BOTH the tracing requirement AND
the Agent Builder requirement at once. So: **port the orchestrator onto ADK.** (The
Vertex AI Search / Discovery Engine idea is OUT as the satisfier — it's a search
product, not an agent runtime; fine as an optional ADK tool later.)

## What was built this session
**`scrape_agent_adk.py`** — a new module ALONGSIDE the untouched, known-good
`scrape_agent.py` (keep the fallback). It re-platforms the orchestration onto ADK
1.33.0 while reusing the proven web layer + writers:
- Reuses unchanged: `google_search_grounding`, `fetch_url` (scrape_utils); `EMPTY_CATALOGUE`,
  `write_markdown_catalogue`, `write_html_dashboard`, `query_phoenix_performance` (scrape_agent).
- ADK agents (Gemini `gemini-2.5-flash`), each run via `Runner`:
  - `validator` (output_schema) — input gate.
  - `scout` (tools=[`google_search`]) — live landscape survey via the ADK Google Search tool.
  - `planner` (output_schema `QueryPlan`) — 5 gated sub-agent queries + viability gate, fed scout text + Phoenix history.
  - `extractor` (output_schema `Catalogue`) — structures scraped text into the 10-category catalogue.
  - `faithfulness` (output_schema) — grounding/hallucination score per sub-agent.
  - `phoenix_mcp` (tools=[`MCPToolset`→Arize MCP]) — **the partner MCP, integrated THROUGH ADK**, fetches the faithfulness template at runtime (`fetch_faithfulness_template_via_mcp`).
- Pydantic schemas mirror `CATALOGUE_SCHEMA` (ADK `output_schema` needs Pydantic, not raw dicts).
- Sub-agent flow preserved: grounding → scrape top 3 URLs → ADK extractor → faithfulness.
  Sub-agents run concurrently via `asyncio.gather`. Merge/dedup + search_history identical to the original.
- `--trace` instruments BOTH `GoogleADKInstrumentor` + `GoogleGenAIInstrumentor` → Phoenix.

## STATUS: VERIFIED WORKING (2026-06-09)
`scrape_agent_adk.py` compiles, imports, and runs the full pipeline end to end on ADK.

1. **Compile + import** ✓ — both pass (only an `[EXPERIMENTAL] PLUGGABLE_AUTH` UserWarning, harmless).
2. **Auth bug found + fixed** ✓ — ADK's `LlmAgent` builds its **own** `google.genai` client,
   which reads the key from `os.environ`; the web layer (`make_client`) passed the key
   explicitly so it never needed env vars, and the `.env` key was never exported. Every ADK
   call failed `No API key was provided`. **Fix:** a bootstrap block near the top of
   `scrape_agent_adk.py` calls `get_api_key()` and `os.environ.setdefault`s `GOOGLE_API_KEY`/
   `GEMINI_API_KEY` + pins `GOOGLE_GENAI_USE_VERTEXAI=FALSE` (Developer-API path, no GCP project).
3. **Small live test** `-q "Berlin"` ✓ — validator classified, **Arize MCP fired through ADK**
   ("Faithfulness template loaded from Arize MCP"; a `function_call` part confirms the tool was
   invoked), ADK scout surfaced real venues, planner approved 5 viable sub-agents, all 5 ran
   concurrently → scraped → ADK extractor → faithfulness scored, merge/dedup + writes succeeded.
   (Catalogue was restored from `catalogue.backup.json` afterward — see DATA NOTE below.)
4. **`requirements.txt` fixed** ✓ — now lists `google-genai`, `google-adk`, `pydantic`, both
   openinference instrumentors, and the phoenix/otel lines.

### DATA NOTE — faithfulness is advisory, does NOT gate the merge
The Berlin run's faithfulness agent scored most extracted entries 0.0–0.2 (heavy fabrication:
"Kick The Flame", "Phiture", "Mirage" flagged invented), but the merge loop appends items
regardless of score (it only attaches a `_faithfulness_warning`, mirroring the original
`scrape_agent.py`). So a live run can absorb low-quality entries. The test data was rolled
back from backup. **Open decision:** gate merges on a faithfulness threshold (e.g. drop sub-agent
output below ~0.5) before any real data-broadening run — ties into the [syncsnake-data-quality]
"broad but shallow" finding.

### Remaining verification step (not yet run — has side effects)
**`--trace` run** confirms ADK spans land in Phoenix (the Arize-track demo evidence). It
launches a local Phoenix server on :6006 AND costs another full paid run that re-mutates the
catalogue, so run it deliberately (back up + restore around it):
```bash
/Users/maryann/sonic/.venv/bin/python scrape_agent_adk.py -q "Berlin" --trace
```

## Known risk points to watch (debug here first if it breaks)
- **output_schema parsing:** `_parse()` expects the agent's final text to be JSON; it has a
  regex salvage pass. If empty/malformed, inspect the raw `final` text in `_run()`.
- **Arize MCP via MCPToolset:** the HTTP MCP (`ARIZE_MCP_URL`) tool name/availability is
  assumed; on failure it degrades to the built-in template (run still succeeds). Verify it
  actually FIRES in the demo run (the rules require the MCP called at runtime, not just named).
- **`google_search` ADK tool** with the AI Studio key — should work; falls back to direct grounding if not.
- **Concurrency:** multiple `Runner`s share one `InMemorySessionService` (distinct session ids). Fine at our scale; reduce if flaky.

## ADK 1.33.0 API cheat-sheet (already introspected — don't re-derive)
- `from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent`
- `from google.adk.runners import Runner` · `from google.adk.sessions import InMemorySessionService`
- `from google.adk.tools import google_search, FunctionTool, AgentTool` (also `VertexAiSearchTool`, `DiscoveryEngineSearchTool`)
- `from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams, SseConnectionParams, StdioConnectionParams, StdioServerParameters`
- `LlmAgent(name=, model=, instruction=, tools=[...] , output_schema=Pydantic, output_key=, disallow_transfer_to_parent/peers=)` — **output_schema XOR tools** (can't set both).
- `Runner(app_name=, agent=, session_service=)`; `await session_service.create_session(app_name=, user_id=, session_id=)` (async);
  `async for ev in runner.run_async(user_id=, session_id=, new_message=types.Content(...))` → use `ev.is_final_response()`.
- `StreamableHTTPConnectionParams(url=, headers=, timeout=, ...)`.

## Option B: replace the decorative MCP with the real Phoenix runtime MCP — ✅ BUILT 2026-06-09 (see Session-2 addendum at top). Below is the original design sketch, kept as the as-built reference.

**Why:** the current `fetch_faithfulness_template_via_mcp()` hits the Mintlify **docs-search**
MCP (`https://arizeai-433a7140.mintlify.app/mcp`). Verified at runtime it returns a 759-char
*note* saying "the verbatim template is NOT available here" + a generic definition — which is
then injected as a 500-char "guidance" prefix into the faithfulness agent (which already knows
how to score). So the MCP fires (satisfies the literal rule) but is **decorative** and touches
nothing in the data/fabrication path. User chose to make it **substantive**.

**Decision:** swap to the **`@arizeai/phoenix-mcp` runtime server** (talks to the live Phoenix
at :6006), wired via ADK `McpToolset` over **stdio/npx**, and make it **load-bearing**: host the
faithfulness evaluator prompt in Phoenix's **prompt registry**, fetch it at runtime via the MCP,
and use the fetched template as the faithfulness agent's actual instruction (not decoration).

**Feasibility — all verified this session:**
- node v24.11.1 / npx 11.6.2 present; `@arizeai/phoenix-mcp@4.0.13` on npm.
- ADK connect that works (lists 27 tools):
  ```python
  from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
  from mcp import StdioServerParameters
  McpToolset(connection_params=StdioConnectionParams(
      server_params=StdioServerParameters(command="npx",
          args=["-y","@arizeai/phoenix-mcp@latest","--baseUrl","http://localhost:6006"]),
      timeout=60))
  ```
- Tool objects are `google.adk.tools.mcp_tool.mcp_tool.MCPTool` with
  `run_async(*, args: dict, tool_context: ToolContext)` (direct calls need a ToolContext, which
  is awkward to build standalone — easiest to call tools via an `LlmAgent`, or seed via the raw
  `mcp` ClientSession `call_tool`).
- **CONSTRAINT:** phoenix-mcp needs a live Phoenix at :6006 → this is only active under `--trace`
  (or launch Phoenix separately). Gate on reachability (`curl :6006`); else fall back to the
  built-in template (today's graceful behavior). Phoenix wasn't run this session.

**Exact tool schemas (introspected — don't re-derive):**
- `upsert-prompt`  req `{name, template}`; opt `{description, model_provider∈[OPENAI,AZURE_OPENAI,ANTHROPIC,GOOGLE] dflt OPENAI, model_name dflt gpt-4, temperature dflt .7}`
- `get-prompt`     req `{prompt_identifier}`; opt `{tag, version_id}` → returns version w/ template
- `add-dataset-examples` req `{dataset_name, examples:[{input:obj, output:obj, metadata?:obj}]}` (no separate create-dataset tool — this appears to create-on-first-add)
- `get-dataset-examples` `{dataset_id|dataset_name, version_id?, splits?}`
- `get-spans` `{project_identifier, names?[], span_kinds?[], limit≤1000, include_annotations?}`; also `list-projects, list-datasets, get-dataset, get-span-annotations, list-traces`.

**Implementation sketch (scrape_agent_adk.py):**
1. Add a real `FAITHFULNESS_TEMPLATE` constant (grounded-hallucination eval prompt).
2. Replace `ARIZE_MCP_URL`/`StreamableHTTPConnectionParams` with the stdio phoenix-mcp McpToolset above.
3. `_seed_faithfulness_prompt()` — idempotent `upsert-prompt` (name `syncsnake-faithfulness-evaluator`,
   template=FAITHFULNESS_TEMPLATE, model_provider="GOOGLE", model_name=MODEL). Provisioning; do via raw
   `mcp` ClientSession for determinism (don't round-trip the long template through an LLM).
4. Rewrite `fetch_faithfulness_template_via_mcp()` → `load_faithfulness_prompt_via_phoenix_mcp()`:
   ADK `LlmAgent` + phoenix McpToolset, instruction "call get-prompt for 'syncsnake-faithfulness-evaluator',
   return ONLY the template text." (This is THE runtime, agent-mediated, traced MCP call.)
5. **Actually use** the returned template as the faithfulness agent's instruction (build it dynamically
   or thread it in), replacing the 500-char `guidance` prefix.
6. Fix the misleading `"Faithfulness template loaded from Arize MCP."` log.
7. **Stretch (close the loop):** after each run, `add-dataset-examples` to a `syncsnake-faithfulness`
   dataset (input=source+output sample, output=score, metadata=topic); `get-dataset-examples` at
   startup to feed prior faithfulness into the planner.

## DATA-QUALITY FINDINGS from the faithfulness probe (2026-06-09) — carry forward
Probed one Berlin sub-agent end-to-end (artifacts were in `probe_out/`, since removed). Conclusions:
- **Entities are REAL, not invented** (Better Things Berlin, GL Music, Steam Music, Musicbed, Taxi,
  Songtradr, Terrorbird…). Earlier "entirely fabricated names" verdicts overstated it.
- **The faithfulness eval has a truncation bug:** it scores grounding against only `combined[:2000]`
  in `run_subagent`. Proven false-positive: GL Music's "Hansi Hinterseer/Justin Bieber/Johnny Cash/
  Drake" roster was flagged "fabricated" but is **verbatim in the source at ~char 3000**. → **Widen the
  eval source window to the full scraped text.** Eval is also noisy (0.7 vs 0.4 on identical data) →
  **do NOT gate merges on the raw score.**
- **Real root cause of thin data = the scraper:** grounding links resolve to
  `vertexaisearch.cloud.google.com/grounding-api-redirect/...` URLs that `fetch_url` barely expands
  (got 648 / 7166 / **182** chars from the 3 pages; the 182 was a cookie banner). With no real page
  text the extractor leans on training knowledge → ungrounded detail (e.g. Steam Music's invented
  contact block). **Fix = resolve the redirects / scrape the real destination domains.** Highest-
  leverage data fix, ties to [memory: syncsnake-data-quality].

## Then the remaining hackathon checklist (see [memory: syncsnake-hackathon-requirements])
4. **Fix `requirements.txt`** — it's missing the deps the code imports. Add at least:
   `google-genai`, `google-adk`, `openinference-instrumentation-google-genai`,
   `openinference-instrumentation-google-adk` (+ existing arize-phoenix lines).
5. **Update README** — add the ADK run commands + a short "built on Google Cloud Agent
   Builder (ADK)" + Arize-track framing.
6. **Make `scrape_agent_adk.py` the documented entrypoint** (keep `scrape_agent.py` as fallback).
7. **Demo video** <3 min, YouTube/Vimeo public (hard req, not started) — show the ADK agent
   running + Phoenix traces + the dashboard.
8. **Merge branch → `main`** to deploy the updated dashboard (Pages serves main; currently old).
9. **Devpost form** — repo URL, hosted URL, video URL, select Arize track, list yourself.
   (AI-assisted coding is allowed — Google's own ADK docs list Claude Code as a build tool;
   the "no competing AI" rule is about the agent's model/cloud, which is Gemini+GCP ✓.)

## Deferred (post-eligibility, only if time): the "Tinder deck" UI
The swipe-deck prototype in `/Users/maryann/syncsnake_deck/app.html` (see [memory:
syncsnake-handoff]) is the chosen UI direction but is NOT wired into the product. Lower
priority than eligibility + the video. Do not reopen the abandoned `rolodex_prototypes/`.
