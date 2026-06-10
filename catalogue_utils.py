"""Shared catalogue helpers — extracted from the original scrape_agent.py.

scrape_agent_adk.py imports EMPTY_CATALOGUE, write_markdown_catalogue,
write_html_dashboard, and query_phoenix_performance from here.
"""
import json

# ── Optional Arize Phoenix client (feedback loop) ────────────────────────────
try:
    from phoenix.client import Client as PhoenixClient
    HAS_PHOENIX_CLIENT = True
except ImportError:
    HAS_PHOENIX_CLIENT = False
    PhoenixClient = None

EMPTY_CATALOGUE = {k: [] for k in [
    "agencies", "supervisors", "platforms", "restricted_resources",
    "grants", "festivals", "indie_games", "ad_agencies",
    "music_libraries", "competitions",
]}


def _get_span_attr(span, key: str) -> str:
    for kv in span.attributes:
        if kv.key == key:
            val = kv.value
            if val.HasField("string_value"):
                return val.string_value
            if val.HasField("int_value"):
                return str(val.int_value)
    return ""


def query_phoenix_performance(project_name: str = "sync-licensing-agent") -> dict:
    """Queries Arize Phoenix for historical sub-agent performance to inform the viability gate."""
    if not HAS_PHOENIX_CLIENT:
        return {}
    try:
        client = PhoenixClient()
        spans = client.spans.get_spans(project_identifier=project_name, span_kind="AGENT", limit=500, timeout=5)
        stats: dict = {}
        for span in spans:
            name = span.name
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
            if topic not in stats:
                stats[topic] = {"runs": 0, "total_results": 0}
            stats[topic]["runs"]          += 1
            stats[topic]["total_results"] += total
        for s in stats.values():
            s["avg_results"] = round(s["total_results"] / s["runs"], 1) if s["runs"] else 0
        return stats
    except Exception:
        return {}


def write_markdown_catalogue(data: dict):
    lines = [
        "# Sync Licensing Opportunity Catalogue\n",
        "Compiled by SyncSnake (Medusa). Agencies, supervisors, platforms, grants, "
        "festivals, ad agencies, libraries, competitions, and restricted resources.\n",
        "## Sync Licensing Agencies\n",
        "| Agency Name | Location | Focus / Genre | Submission Guidelines | Contact / Website |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for a in data.get("agencies", []):
        lines.append(f"| **{a['name']}** | {a['location']} | {a['roster_genre_focus']} | {a['submission_guidelines']} | [{a['website']}]({a['website']}) `{a['contact_info']}` |")
    lines += ["\n## Music Supervisors\n", "| Name | Company | Location | Notable Projects | Submission Policy | Contact |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for s in data.get("supervisors", []):
        lines.append(f"| **{s['name']}** | {s['company']} | {s['location']} | {s['notable_projects']} | {s['submission_policy']} | {s['contact_info']} |")
    lines += ["\n## Brief & Pitch Platforms\n", "| Platform | Description | Requirements | Link |", "| :--- | :--- | :--- | :--- |"]
    for p in data.get("platforms", []):
        lines.append(f"| **{p['name']}** | {p['description']} | {p['requirements']} | [Link]({p['url']}) |")
    lines += ["\n## Grants & Funding\n", "| Grant | Organization | Eligibility | Deadlines | Link |", "| :--- | :--- | :--- | :--- | :--- |"]
    for g in data.get("grants", []):
        lines.append(f"| **{g['name']}** | {g['organization']} | {g['eligibility_summary']} | {g['deadlines']} | [Link]({g['url']}) |")
    lines += ["\n## Festivals & Showcases\n", "| Festival | Location | Application Window | Requirements | Link |", "| :--- | :--- | :--- | :--- | :--- |"]
    for f in data.get("festivals", []):
        lines.append(f"| **{f['name']}** | {f['location']} | {f['application_window']} | {f['requirements_fees']} | [Link]({f['url']}) |")
    lines += ["\n## Indie Video Game Projects\n", "| Project | Studio | Needs | Contact | Link |", "| :--- | :--- | :--- | :--- | :--- |"]
    for g in data.get("indie_games", []):
        lines.append(f"| **{g['project_name']}** | {g['developer_studio']} | {g['status_or_needs']} | `{g['contact_info']}` | [Link]({g['url']}) |")
    lines += ["\n## Advertising Agencies\n", "| Agency | Location | Creative Leads | Contact | Website |", "| :--- | :--- | :--- | :--- | :--- |"]
    for a in data.get("ad_agencies", []):
        lines.append(f"| **{a['name']}** | {a['location']} | {a['creative_director_or_leads']} | `{a['contact_info']}` | [Link]({a['website']}) |")
    lines += ["\n## Production Music Libraries\n", "| Library | Status | Requirements | Payout | Link |", "| :--- | :--- | :--- | :--- | :--- |"]
    for lib in data.get("music_libraries", []):
        lines.append(f"| **{lib['name']}** | *{lib['submission_status']}* | {lib['requirements_genres']} | {lib['payout_model']} | [Link]({lib['url']}) |")
    lines += ["\n## Songwriting Competitions\n", "| Competition | Deadlines | Fees & Requirements | Prizes | Link |", "| :--- | :--- | :--- | :--- | :--- |"]
    for c in data.get("competitions", []):
        lines.append(f"| **{c['name']}** | {c['deadlines']} | {c['entry_fees_requirements']} | {c['prizes_categories']} | [Link]({c['url']}) |")
    lines += ["\n## Restricted Resources\n", "| Source | Expected Value | Access Requirement | Website |", "| :--- | :--- | :--- | :--- |"]
    for r in data.get("restricted_resources", []):
        lines.append(f"| **{r['source_name']}** | {r['expected_value']} | {r['reason_for_restriction']} | [Link]({r['url']}) |")
    with open("catalogue.md", "w") as f:
        f.write("\n".join(lines))


def write_html_dashboard(data: dict):
    with open("dashboard_template.html", "r", encoding="utf-8") as f:
        template = f.read()
    with open("dashboard.html", "w") as f:
        f.write(template.replace("%DATA%", json.dumps(data, indent=2)))
