import os
import sys
import json
import asyncio
import urllib.request
from scrape_utils import google_search_grounding, fetch_url, get_api_key

# Setup optional OpenTelemetry tracing
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    HAS_OTEL = True
    tracer = trace.get_tracer("sync_licensing_agent")
except ImportError:
    HAS_OTEL = False
    class Status:
        def __init__(self, status_code, description=""): pass
    class StatusCode:
        ERROR = "ERROR"
        OK = "OK"
    class DummySpan:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def set_attribute(self, key, value): pass
        def set_status(self, status): pass
    class DummyTracer:
        def start_as_current_span(self, name, *args, **kwargs):
            return DummySpan()
    tracer = DummyTracer()

# Setup optional Arize Phoenix client (MCP integration for trace-based feedback)
try:
    from phoenix.client import Client as PhoenixClient
    HAS_PHOENIX_CLIENT = True
except ImportError:
    HAS_PHOENIX_CLIENT = False
    PhoenixClient = None

# Define JSON schema for structured output (Gemini REST format)
CATALOGUE_SCHEMA = {
  "type": "OBJECT",
  "properties": {
    "agencies": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the sync licensing agency"},
          "website": {"type": "STRING", "description": "Official website URL"},
          "location": {"type": "STRING", "description": "City and state/province or country, e.g., Montreal, QC or Toronto, ON"},
          "contact_info": {"type": "STRING", "description": "Email, phone, or specific contact form link"},
          "submission_guidelines": {"type": "STRING", "description": "Specific instructions on how to submit music"},
          "roster_genre_focus": {"type": "STRING", "description": "The genres or types of music they represent, or specific rosters"},
          "regions": {"type": "STRING", "description": "Regions served, e.g. USA, Canada, Global"}
        },
        "required": ["name", "website", "location", "contact_info", "submission_guidelines", "roster_genre_focus", "regions"]
      }
    },
    "supervisors": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the music supervisor"},
          "company": {"type": "STRING", "description": "Company name or agency they work for"},
          "location": {"type": "STRING", "description": "City and region"},
          "notable_projects": {"type": "STRING", "description": "Films, TV shows, or campaigns they worked on"},
          "contact_info": {"type": "STRING", "description": "Email or social media link (LinkedIn, etc.)"},
          "submission_policy": {"type": "STRING", "description": "Policy on unsolicited submissions"}
        },
        "required": ["name", "company", "location", "notable_projects", "contact_info", "submission_policy"]
      }
    },
    "platforms": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the platform posting briefs"},
          "url": {"type": "STRING", "description": "URL to the briefs section"},
          "description": {"type": "STRING", "description": "How to access briefs (e.g. open to public, requires membership)"},
          "requirements": {"type": "STRING", "description": "Key requirements for pitches"}
        },
        "required": ["name", "url", "description", "requirements"]
      }
    },
    "restricted_resources": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "source_name": {"type": "STRING", "description": "Name of the resource or platform"},
          "url": {"type": "STRING", "description": "URL of the platform"},
          "reason_for_restriction": {"type": "STRING", "description": "Why it is restricted (e.g. paid subscription, captcha)"},
          "expected_value": {"type": "STRING", "description": "Why this source would be useful to look into"}
        },
        "required": ["source_name", "url", "reason_for_restriction", "expected_value"]
      }
    },
    "grants": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the grant or funding program"},
          "organization": {"type": "STRING", "description": "Funding body or organization, e.g., FACTOR, Canada Council"},
          "eligibility_summary": {"type": "STRING", "description": "Who is eligible to apply"},
          "deadlines": {"type": "STRING", "description": "Upcoming application deadlines or 'rolling'"},
          "url": {"type": "STRING", "description": "Official URL for application guidelines"}
        },
        "required": ["name", "organization", "eligibility_summary", "deadlines", "url"]
      }
    },
    "festivals": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the festival or showcase opportunity"},
          "location": {"type": "STRING", "description": "City and country where it takes place"},
          "application_window": {"type": "STRING", "description": "Start and end dates for artist applications"},
          "requirements_fees": {"type": "STRING", "description": "Application fees, age requirements, or specific criteria"},
          "url": {"type": "STRING", "description": "Official artist application link"}
        },
        "required": ["name", "location", "application_window", "requirements_fees", "url"]
      }
    },
    "indie_games": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "project_name": {"type": "STRING", "description": "Name of the video game project"},
          "developer_studio": {"type": "STRING", "description": "Name of the developer or studio"},
          "status_or_needs": {"type": "STRING", "description": "Development status or music needs if mentioned"},
          "contact_info": {"type": "STRING", "description": "Contact email, social media, or campaign link"},
          "url": {"type": "STRING", "description": "Link to campaign or game page"}
        },
        "required": ["project_name", "developer_studio", "status_or_needs", "contact_info", "url"]
      }
    },
    "ad_agencies": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the advertising agency"},
          "location": {"type": "STRING", "description": "City and country"},
          "contact_info": {"type": "STRING", "description": "Contact email or submission page link"},
          "creative_director_or_leads": {"type": "STRING", "description": "Name of Creative Directors, Head of Production, or music contact names"},
          "website": {"type": "STRING", "description": "Official agency website"}
        },
        "required": ["name", "location", "contact_info", "creative_director_or_leads", "website"]
      }
    },
    "music_libraries": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the production music library (e.g. Artlist, Epidemic Sound)"},
          "submission_status": {"type": "STRING", "description": "Submissions status (e.g. 'Open', 'Closed', or 'Invite only')"},
          "requirements_genres": {"type": "STRING", "description": "Submission requirements, guidelines, and target genres"},
          "payout_model": {"type": "STRING", "description": "Royalty model if mentioned (e.g. buyout, royalty share, non-exclusive)"},
          "url": {"type": "STRING", "description": "Official contributor application or submission link"}
        },
        "required": ["name", "submission_status", "requirements_genres", "payout_model", "url"]
      }
    },
    "competitions": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "properties": {
          "name": {"type": "STRING", "description": "Name of the songwriting competition or award program"},
          "deadlines": {"type": "STRING", "description": "Upcoming submission deadlines"},
          "entry_fees_requirements": {"type": "STRING", "description": "Entry fees, age limit, or regional restrictions"},
          "prizes_categories": {"type": "STRING", "description": "Prizes, categories, or expected benefits"},
          "url": {"type": "STRING", "description": "Official submission page URL"}
        },
        "required": ["name", "deadlines", "entry_fees_requirements", "prizes_categories", "url"]
      }
    }
  },
  "required": ["agencies", "supervisors", "platforms", "restricted_resources", "grants", "festivals", "indie_games", "ad_agencies", "music_libraries", "competitions"]
}

def _get_span_attr(span, key: str) -> str:
    """Extract a string attribute value from a protobuf Span by key."""
    for kv in span.attributes:
        if kv.key == key:
            val = kv.value
            if val.HasField("string_value"):
                return val.string_value
            if val.HasField("int_value"):
                return str(val.int_value)
    return ""


def query_phoenix_performance(project_name: str = "sync-licensing-agent") -> dict:
    """Queries Arize Phoenix for historical sub-agent performance.

    Returns a dict mapping topic name → {runs, total_results, avg_results}
    so the planner can mark low-yield topics as non-viable before spending
    API calls on them.
    """
    if not HAS_PHOENIX_CLIENT:
        return {}
    try:
        client = PhoenixClient()  # defaults to http://localhost:6006
        spans = client.spans.get_spans(
            project_identifier=project_name,
            span_kind="AGENT",
            limit=500,
            timeout=5,
        )
        topic_stats: dict = {}
        for span in spans:
            name = span.name  # e.g. "subagent_GameAudio"
            if not name.startswith("subagent_"):
                continue
            topic = name[len("subagent_"):]
            output_val = _get_span_attr(span, "output.value")
            total = 0
            try:
                data = json.loads(output_val)
                total = sum(len(v) for v in data.values() if isinstance(v, list))
            except Exception:
                pass
            if topic not in topic_stats:
                topic_stats[topic] = {"runs": 0, "total_results": 0}
            topic_stats[topic]["runs"] += 1
            topic_stats[topic]["total_results"] += total
        for stats in topic_stats.values():
            runs = stats["runs"]
            stats["avg_results"] = round(stats["total_results"] / runs, 1) if runs else 0
        return topic_stats
    except Exception:
        return {}


async def scout_and_plan_queries(model: str = "gemini-2.5-flash", user_focus: str = None) -> dict:
    """Scouts active music hubs using Google Search grounding, then plans new unique search queries for sub-agents."""
    with tracer.start_as_current_span("scout_and_plan_queries") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        if user_focus:
            span.set_attribute("user_focus", user_focus)
        
        # 1. Load history to prevent duplicate searches
        history_file = "search_history.json"
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except Exception:
                pass
                
        # 2. Scout current music hotspots/trends using search grounding
        if user_focus:
            scout_query = f"top active music sync licensing hubs supervisors agencies festivals platforms ad agencies music libraries competitions for {user_focus} 2026 2027"
            print(f"Orchestrator: Scouting opportunities for custom focus '{user_focus}' via Google Search...")
        else:
            scout_query = "major active music sync licensing hubs upcoming showcase music festivals video game audio platforms ad agencies creative directors music contacts production music libraries submission windows songwriting competitions deadlines 2026 2027"
            print(f"Orchestrator: Scouting active music hotspots and opportunities via Google Search...")
            
        scout_res = await asyncio.to_thread(google_search_grounding, scout_query, model)

        # 3a. Query Arize Phoenix for historical sub-agent performance (MCP feedback loop)
        past_perf = await asyncio.to_thread(query_phoenix_performance)
        if past_perf:
            perf_lines = [
                f"  {topic}: {s['runs']} run(s), avg {s['avg_results']} results/run"
                for topic, s in sorted(past_perf.items(), key=lambda x: x[1]["avg_results"])
            ]
            phoenix_context = "=== ARIZE PHOENIX: HISTORICAL SUB-AGENT PERFORMANCE ===\n" + "\n".join(perf_lines)
            print(f"Orchestrator: Loaded performance data from Arize Phoenix for {len(past_perf)} past topics.")
        else:
            phoenix_context = "(Arize Phoenix not available or no prior runs recorded)"

        # 3b. Call Gemini to analyze the scout report and generate 5 new targeted search queries
        print(f"Orchestrator: Planning new search strategy based on scout findings...")
        api_key = get_api_key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        focus_instruction = ""
        if user_focus:
            focus_instruction = f"=== USER FOCUS GUIDANCE ===\nThe user has directed the research to focus specifically on: '{user_focus}'\n\n"
            
        prompt = (
            f"You are a music industry research planner. Based on the following real-time research of active music sync licensing hubs, "
            f"festivals, and platforms, plan exactly 5 new, highly targeted search queries for our worker sub-agents.\n\n"
            f"{focus_instruction}"
            f"=== REAL-TIME RESEARCH ===\n{scout_res.get('text', '')}\n\n"
            f"=== ALREADY RUN SEARCH QUERIES ===\n{json.dumps(history)}\n\n"
            f"{phoenix_context}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Generate exactly 5 search queries that are specific, detailed, and aimed at finding sync agencies, music supervisors, brief platforms, grants, showcase festivals, indie games, ad agencies, production music libraries, or songwriting competitions.\n"
        )
        if user_focus:
            prompt += f"2. Ensure all 5 queries specifically match the USER FOCUS GUIDANCE ('{user_focus}').\n"
        else:
            prompt += f"2. Do NOT generate queries that are identical or highly similar to the ALREADY RUN queries.\n"

        prompt += (
            f"3. For each query, set 'viable' to false if the scout results above suggest this topic area is currently sparse, "
            f"unavailable, or unlikely to yield actionable music opportunities — OR if the Arize Phoenix performance data shows "
            f"this topic has returned 0 or very few results across multiple past runs. Set it to true if the scout results indicate "
            f"active listings, open submissions, or real contacts exist. This gate prevents wasted API calls on dead-end searches.\n"
            f"4. Return the response as a JSON object with a single key 'queries' mapping topic name to an object with 'query' (string) and 'viable' (boolean).\n"
            f"Example JSON structure:\n"
            f'{{\n  "queries": {{\n    "Topic A": {{"query": "search query A...", "viable": true}},\n    "Topic B": {{"query": "search query B...", "viable": false}}\n  }}\n}}'
        )

        req_data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "queries": {
                            "type": "OBJECT",
                            "description": "A dictionary mapping a topic name to a query plan object.",
                            "additionalProperties": {
                                "type": "OBJECT",
                                "properties": {
                                    "query": {"type": "STRING", "description": "The search query string to run"},
                                    "viable": {"type": "BOOLEAN", "description": "True if scout results suggest useful data exists, False to skip this sub-agent"}
                                },
                                "required": ["query", "viable"]
                            }
                        }
                    },
                    "required": ["queries"]
                },
                "temperature": 0.2
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        def call_planner():
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                return "{}"
                
        try:
            with tracer.start_as_current_span("call_planner_llm") as llm_span:
                llm_span.set_attribute("openinference.span.kind", "LLM")
                llm_span.set_attribute("llm.model_name", model)
                llm_span.set_attribute("input.value", prompt)
                
                response_text = await asyncio.to_thread(call_planner)
                llm_span.set_attribute("output.value", response_text)
                
            data = json.loads(response_text)
            raw_queries = data.get("queries", {})
            if not raw_queries:
                raise ValueError("No queries returned in JSON.")

            # Gate: only pass through sub-agents the planner marked as viable
            viable = {topic: plan["query"] for topic, plan in raw_queries.items() if plan.get("viable", True)}
            skipped = [topic for topic, plan in raw_queries.items() if not plan.get("viable", True)]
            if skipped:
                print(f"Orchestrator: Gate blocked {len(skipped)} non-viable sub-agent(s): {skipped}")

            if not viable:
                raise ValueError("All planned queries were marked non-viable.")

            print(f"Orchestrator: Planner approved {len(viable)} sub-agent(s): {list(viable.keys())}")
            return viable
            
        except Exception as e:
            print(f"Orchestrator: Error during planning phase: {e}. Falling back to default queries.")
            # Fallback queries if planner fails
            if user_focus:
                return {
                    f"{user_focus} Agencies": f"music sync licensing agencies for {user_focus} contacts submission guidelines",
                    f"{user_focus} Supervisors": f"music supervisors who place music matching {user_focus} contact submission policy",
                    f"{user_focus} Ad Agencies": f"advertising agencies creative directors music contacts for {user_focus}",
                    f"{user_focus} Music Libraries": f"production music libraries Epidemic Artlist contributor submissions for {user_focus}",
                    f"{user_focus} Competitions": f"songwriting competitions and artist awards open for {user_focus} 2026"
                }
            return {
                "London": "music sync licensing agencies and music supervisors London UK contacts",
                "Ad Agencies": "top advertising agencies creative directors music production contacts submissions",
                "Music Libraries": "production music libraries contributor submission windows open Artlist Epidemic Musicbed",
                "Competitions": "major songwriting competitions artist award submissions deadlines 2026",
                "Game Audio": "indie game developers looking for composers custom music sound design contacts"
            }

async def run_subagent_research(topic: str, search_query: str, model: str = "gemini-2.5-flash") -> dict:
    """Sub-agent task: researches a specific region or topic, scrapes relevant pages, and returns structured data."""
    with tracer.start_as_current_span(f"subagent_{topic}") as span:
        span.set_attribute("openinference.span.kind", "AGENT")
        span.set_attribute("input.value", search_query)
        span.set_attribute("model", model)
        print(f"[Sub-Agent: {topic}] Starting research on query: '{search_query}'...")

        # 1. Perform search grounding
        search_res = await asyncio.to_thread(google_search_grounding, search_query, model)

        discovered_urls = []
        for link in search_res.get("links", []):
            uri = link["uri"]
            if "google.com/search" not in uri and "google.com/maps" not in uri and "duckduckgo.com" not in uri:
                discovered_urls.append(uri)

        discovered_urls = list(set(discovered_urls))
        print(f"[Sub-Agent: {topic}] Discovered {len(discovered_urls)} URLs. Deep scraping top 3...")

        if not discovered_urls:
            print(f"[Sub-Agent: {topic}] No grounded URLs returned. Skipping extraction.")
            span.set_attribute("output.value", "skipped: no grounded URLs")
            return {"agencies": [], "supervisors": [], "platforms": [], "restricted_resources": [], "grants": [], "festivals": [], "indie_games": [], "ad_agencies": [], "music_libraries": [], "competitions": []}

        # 2. Scrape top 3 websites concurrently
        async def fetch_one(url):
            print(f"[Sub-Agent: {topic}] Fetching: {url}...")
            text = await asyncio.to_thread(fetch_url, url)
            return url, text

        urls_to_fetch = discovered_urls[:3]
        fetch_tasks = [fetch_one(url) for url in urls_to_fetch]
        fetch_results = await asyncio.gather(*fetch_tasks)

        page_data = {}
        for url, cleaned_text in fetch_results:
            if cleaned_text and not cleaned_text.startswith("Error"):
                page_data[url] = cleaned_text[:3000]

        # 3. Compile context for this sub-agent
        context_parts = [f"=== SEARCH FINDINGS FOR {topic.upper()} ===", search_res.get("text", "")]
        context_parts.append("=== SCRAPED WEBPAGES ===")
        for url, text in page_data.items():
            context_parts.append(f"URL: {url}\nContent:\n{text}\n-------------------")

        full_context = "\n".join(context_parts)

        # 4. Use Gemini to structure findings
        print(f"[Sub-Agent: {topic}] Formatting results into structured schema...")
        api_key = get_api_key()

        prompt = (
            f"Extract all music opportunities (agencies, music supervisors, brief platforms, restricted resources, "
            f"grants/funding programs, showcase festivals/gigs, indie video game projects, advertising agencies, "
            f"production music libraries, and songwriting competitions) related to the topic '{topic}' "
            "from the following context. Return the results matching the requested ResearchCatalogue schema."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        req_data = {
            "contents": [
                {
                    "parts": [
                        {"text": full_context},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": CATALOGUE_SCHEMA,
                "temperature": 0.1
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        def call_gemini():
            with urllib.request.urlopen(req, timeout=60) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            return "{}"

        try:
            with tracer.start_as_current_span("call_gemini") as gemini_span:
                gemini_span.set_attribute("openinference.span.kind", "LLM")
                gemini_span.set_attribute("llm.model_name", model)
                gemini_span.set_attribute("input.value", prompt)

                response_text = await asyncio.to_thread(call_gemini)
                data = json.loads(response_text)

                gemini_span.set_attribute("output.value", response_text)

            print(f"[Sub-Agent: {topic}] Successfully compiled {len(data.get('agencies', []))} agencies, {len(data.get('supervisors', []))} supervisors.")
            span.set_attribute("output.value", response_text)
            return data
        except Exception as e:
            print(f"[Sub-Agent: {topic}] Error calling Gemini or parsing JSON: {e}")
            span.set_status(Status(StatusCode.ERROR, description=str(e)))
            return {"agencies": [], "supervisors": [], "platforms": [], "restricted_resources": [], "grants": [], "festivals": [], "indie_games": [], "ad_agencies": [], "music_libraries": [], "competitions": []}

async def main(model: str = "gemini-2.5-flash", interactive: bool = False, user_focus: str = None, non_interactive: bool = False):
    # Check if we should run in interactive dialogue mode
    is_interactive_terminal = sys.stdin.isatty() if hasattr(sys, "stdin") else False
    should_prompt = (interactive or (is_interactive_terminal and not non_interactive)) and not user_focus
    
    if should_prompt:
        print("\n=======================================================")
        print("         Sync Snake (by Medusa): Interactive Mode      ")
        print("=======================================================")
        print("Choose execution mode:")
        print("  [1] Automatic Scout & Plan (Default background crawler)")
        print("  [2] Custom Guided Search (Influence search direction)")
        try:
            choice = input("\nSelect option (1 or 2): ").strip()
            if choice == "2":
                user_focus = input("Enter focus details (e.g. genre, location, supervision focus): ").strip()
                if not user_focus:
                    print("No focus entered. Defaulting to Automatic Scout & Plan.")
            else:
                print("Defaulting to Automatic Scout & Plan.")
        except (KeyboardInterrupt, EOFError):
            print("\nInterrupted. Defaulting to Automatic Scout & Plan.")
        print("=======================================================\n")

    with tracer.start_as_current_span("orchestrator") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("model", model)
        if user_focus:
            span.set_attribute("user_focus", user_focus)

        # 1. Load existing catalogue if it exists
        catalogue_file = "catalogue.json"
        final_catalogue = {
            "agencies": [],
            "supervisors": [],
            "platforms": [],
            "restricted_resources": [],
            "grants": [],
            "festivals": [],
            "indie_games": [],
            "ad_agencies": [],
            "music_libraries": [],
            "competitions": []
        }
        
        if os.path.exists(catalogue_file):
            try:
                with open(catalogue_file, "r") as f:
                    final_catalogue = json.load(f)
                # Ensure the loaded catalogue has the new keys
                for key in ["ad_agencies", "music_libraries", "competitions"]:
                    if key not in final_catalogue:
                        final_catalogue[key] = []
                print(f"Orchestrator: Loaded existing catalogue. Current counts: {len(final_catalogue.get('agencies', []))} agencies, {len(final_catalogue.get('supervisors', []))} supervisors.")
            except Exception as e:
                print(f"Orchestrator: Error loading existing catalogue: {e}")
                
        # Initialize Seen Sets from existing catalogue to avoid duplication
        seen_agencies = {agency["name"].lower().strip() for agency in final_catalogue.get("agencies", [])}
        seen_supervisors = {(supervisor["name"] + "_" + supervisor["company"]).lower().strip() for supervisor in final_catalogue.get("supervisors", [])}
        seen_platforms = {platform["name"].lower().strip() for platform in final_catalogue.get("platforms", [])}
        seen_restricted = {res["source_name"].lower().strip() for res in final_catalogue.get("restricted_resources", [])}
        seen_grants = {grant["name"].lower().strip() for grant in final_catalogue.get("grants", [])}
        seen_festivals = {(festival["name"] + "_" + festival["location"]).lower().strip() for festival in final_catalogue.get("festivals", [])}
        seen_indie_games = {(game["project_name"] + "_" + game["developer_studio"]).lower().strip() for game in final_catalogue.get("indie_games", [])}
        seen_ad_agencies = {agency["name"].lower().strip() for agency in final_catalogue.get("ad_agencies", [])}
        seen_music_libraries = {lib["name"].lower().strip() for lib in final_catalogue.get("music_libraries", [])}
        seen_competitions = {comp["name"].lower().strip() for comp in final_catalogue.get("competitions", [])}

        # 2. Scout & Plan search strategy
        subagents = await scout_and_plan_queries(model, user_focus=user_focus)
        
        # Spawn sub-agents concurrently
        tasks = []
        for topic, query in subagents.items():
            tasks.append(run_subagent_research(topic, query, model))
            
        # Gather results
        results = await asyncio.gather(*tasks)
        
        # Merge and deduplicate findings
        print("Orchestrator: Merging and deduplicating sub-agent catalogues...")
        
        for res in results:
            # Merge agencies
            for agency in res.get("agencies", []):
                name_key = agency["name"].lower().strip()
                if name_key not in seen_agencies:
                    seen_agencies.add(name_key)
                    final_catalogue["agencies"].append(agency)
                    
            # Merge supervisors
            for supervisor in res.get("supervisors", []):
                name_key = (supervisor["name"] + "_" + supervisor["company"]).lower().strip()
                if name_key not in seen_supervisors:
                    seen_supervisors.add(name_key)
                    final_catalogue["supervisors"].append(supervisor)
                    
            # Merge platforms
            for platform in res.get("platforms", []):
                name_key = platform["name"].lower().strip()
                if name_key not in seen_platforms:
                    seen_platforms.add(name_key)
                    final_catalogue["platforms"].append(platform)
                    
            # Merge restricted resources
            for resource in res.get("restricted_resources", []):
                name_key = resource["source_name"].lower().strip()
                if name_key not in seen_restricted:
                    seen_restricted.add(name_key)
                    final_catalogue["restricted_resources"].append(resource)

            # Merge grants
            for grant in res.get("grants", []):
                name_key = grant["name"].lower().strip()
                if name_key not in seen_grants:
                    seen_grants.add(name_key)
                    final_catalogue["grants"].append(grant)
                    
            # Merge festivals
            for festival in res.get("festivals", []):
                name_key = (festival["name"] + "_" + festival["location"]).lower().strip()
                if name_key not in seen_festivals:
                    seen_festivals.add(name_key)
                    final_catalogue["festivals"].append(festival)
                    
            # Merge indie games
            for game in res.get("indie_games", []):
                name_key = (game["project_name"] + "_" + game["developer_studio"]).lower().strip()
                if name_key not in seen_indie_games:
                    seen_indie_games.add(name_key)
                    final_catalogue["indie_games"].append(game)
                    
            # Merge ad agencies
            for agency in res.get("ad_agencies", []):
                name_key = agency["name"].lower().strip()
                if name_key not in seen_ad_agencies:
                    seen_ad_agencies.add(name_key)
                    final_catalogue["ad_agencies"].append(agency)
                    
            # Merge music libraries
            for lib in res.get("music_libraries", []):
                name_key = lib["name"].lower().strip()
                if name_key not in seen_music_libraries:
                    seen_music_libraries.add(name_key)
                    final_catalogue["music_libraries"].append(lib)
                    
            # Merge competitions
            for comp in res.get("competitions", []):
                name_key = comp["name"].lower().strip()
                if name_key not in seen_competitions:
                    seen_competitions.add(name_key)
                    final_catalogue["competitions"].append(comp)
                    
        # Save output
        print(f"Orchestrator: Compilation complete. Total: {len(final_catalogue['agencies'])} agencies, {len(final_catalogue['supervisors'])} supervisors, {len(final_catalogue['platforms'])} brief platforms, {len(final_catalogue['grants'])} grants, {len(final_catalogue['festivals'])} festivals, {len(final_catalogue['indie_games'])} indie game projects, {len(final_catalogue['ad_agencies'])} ad agencies, {len(final_catalogue['music_libraries'])} music libraries, {len(final_catalogue['competitions'])} songwriting competitions.")
        
        with open("catalogue.json", "w") as f:
            json.dump(final_catalogue, f, indent=2)
            
        write_markdown_catalogue(final_catalogue)
        write_html_dashboard(final_catalogue)
        print("Orchestrator: Saved output to catalogue.json, catalogue.md, and dashboard.html.")

        # Update search history with executed queries
        history_file = "search_history.json"
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except Exception:
                pass
                
        for topic, query in subagents.items():
            if query not in history:
                history.append(query)
                
        try:
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
            print(f"Orchestrator: Updated search_history.json with {len(subagents)} executed queries.")
        except Exception as e:
            print(f"Orchestrator: Error saving search history: {e}")

def write_markdown_catalogue(data):
    """Formats the JSON catalogue data into a beautiful markdown report."""
    lines = [
        "# Sync Licensing Opportunity Catalogue\n",
        "This catalogue was compiled by the Deep Research Sync Licensing Agent. It lists agencies, music supervisors, brief & pitch platforms, music grants & funding programs, showcase festivals & gigs, indie video game projects, advertising agencies & creative directors, production music libraries, songwriting competitions & award programs, and restricted resources.\n",
        "## Sync Licensing Agencies\n",
        "| Agency Name | Location | Focus / Genre | Submission Guidelines | Contact / Website |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for agency in data.get("agencies", []):
        lines.append(f"| **{agency['name']}** | {agency['location']} | {agency['roster_genre_focus']} | {agency['submission_guidelines']} | [{agency['website']}]({agency['website']}) <br> `{agency['contact_info']}` |")
        
    lines.extend([
        "\n## Music Supervisors\n",
        "| Supervisor Name | Company | Location | Notable Projects | Submission Policy | Contact |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for sup in data.get("supervisors", []):
        lines.append(f"| **{sup['name']}** | {sup['company']} | {sup['location']} | {sup['notable_projects']} | {sup['submission_policy']} | {sup['contact_info']} |")
        
    lines.extend([
        "\n## Brief & Pitch Platforms\n",
        "| Platform Name | Description | Key Requirements | Link |",
        "| :--- | :--- | :--- | :--- |"
    ])
    
    for plat in data.get("platforms", []):
        lines.append(f"| **{plat['name']}** | {plat['description']} | {plat['requirements']} | [Link]({plat['url']}) |")
        
    lines.extend([
        "\n## Music Grants & Funding Programs\n",
        "| Grant Name | Organization | Eligibility Summary | Deadlines | Link |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for grant in data.get("grants", []):
        lines.append(f"| **{grant['name']}** | {grant['organization']} | {grant['eligibility_summary']} | {grant['deadlines']} | [Link]({grant['url']}) |")
        
    lines.extend([
        "\n## Showcase Festivals & Gigs\n",
        "| Festival Name | Location | Application Window | Requirements / Fees | Link |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for festival in data.get("festivals", []):
        lines.append(f"| **{festival['name']}** | {festival['location']} | {festival['application_window']} | {festival['requirements_fees']} | [Link]({festival['url']}) |")
        
    lines.extend([
        "\n## Indie Video Game Projects\n",
        "| Project Name | Developer / Studio | Status / Music Needs | Contact Info | Link |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for game in data.get("indie_games", []):
        lines.append(f"| **{game['project_name']}** | {game['developer_studio']} | {game['status_or_needs']} | `{game['contact_info']}` | [Link]({game['url']}) |")
        
    lines.extend([
        "\n## Advertising Agencies & Creative Directors\n",
        "| Agency Name | Location | Creative Directors / Leads | Contact / Submission | Website |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for agency in data.get("ad_agencies", []):
        lines.append(f"| **{agency['name']}** | {agency['location']} | {agency['creative_director_or_leads']} | `{agency['contact_info']}` | [Link]({agency['website']}) |")
        
    lines.extend([
        "\n## Production Music Libraries (Contributor Submission Windows)\n",
        "| Library Name | Submission Status | Requirements & Target Genres | Payout Model | Link |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for lib in data.get("music_libraries", []):
        lines.append(f"| **{lib['name']}** | *{lib['submission_status']}* | {lib['requirements_genres']} | {lib['payout_model']} | [Link]({lib['url']}) |")
        
    lines.extend([
        "\n## Songwriting Competitions & Award Programs\n",
        "| Competition Name | Deadlines | Entry Fees & Requirements | Prizes & Categories | Link |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    
    for comp in data.get("competitions", []):
        lines.append(f"| **{comp['name']}** | {comp['deadlines']} | {comp['entry_fees_requirements']} | {comp['prizes_categories']} | [Link]({comp['url']}) |")

    lines.extend([
        "\n## Restricted Resources & Paid Databases\n",
        "> [!NOTE]\n",
        "> The following resources require paid subscription, membership, or authentication credentials and could not be fully scraped automatically.\n\n",
        "| Source Name | Expected Value / Utility | Access Requirement | Website |",
        "| :--- | :--- | :--- | :--- |"
    ])
    
    for res in data.get("restricted_resources", []):
        lines.append(f"| **{res['source_name']}** | {res['expected_value']} | {res['reason_for_restriction']} | [Link]({res['url']}) |")
        
    with open("catalogue.md", "w") as f:
        f.write("\n".join(lines))

def write_html_dashboard(data):
    """Generates an interactive dashboard.html with embedded data."""
    import json
    with open("dashboard_template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    rendered_html = html_template.replace("%DATA%", json.dumps(data, indent=2))
    with open("dashboard.html", "w") as f:
        f.write(rendered_html)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync Licensing Deep Research Agent")
    parser.add_argument("--trace", action="store_true", help="Enable Arize Phoenix tracing")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini model to use (e.g. gemini-2.5-flash, gemini-3.5-flash)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Prompt the user to direct the agent")
    parser.add_argument("-q", "--query", type=str, default=None, help="Directly specify custom research guidance")
    parser.add_argument("-n", "--non-interactive", action="store_true", help="Force non-interactive automatic execution")
    args = parser.parse_args()
    
    if args.trace and HAS_OTEL:
        try:
            import phoenix as px
            from phoenix.otel import register
            try:
                print("Orchestrator: Connecting to Arize Phoenix tracing server...")
                px.launch_app()
            except Exception:
                print("Orchestrator: Phoenix already running externally, connecting to existing server...")
            register(project_name="sync-licensing-agent")
        except Exception as e:
            print(f"Orchestrator: Failed to initialize Arize Phoenix: {e}")
            
    asyncio.run(main(
        model=args.model,
        interactive=args.interactive,
        user_focus=args.query,
        non_interactive=args.non_interactive
    ))
