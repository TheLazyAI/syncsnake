#!/usr/bin/env python3
"""
build_records.py — convert catalogue.json (agent output) into records.js (swipe deck).

The swipe deck (/Users/maryann/syncsnake_deck/app.html) loads window.RECORDS from
records.js. The agent writes catalogue.json. This script transforms one into the
other so the deck always reflects the latest run.

Card shape:  {title, subtitle, desc, pills, url, contact, cat}

Usage:
    python build_records.py            # write records.js, print summary
    python build_records.py --json     # print records as JSON to stdout (no file write)
"""

import json
import sys
from pathlib import Path

CATALOGUE = Path(__file__).parent / "catalogue.json"
RECORDS = Path(__file__).parent / "deck" / "records.js"

# Categories the deck shows, in display order. restricted_resources is deliberately
# excluded (those are resources to AVOID), and empty categories are skipped at build.
CATEGORY_ORDER = [
    "agencies", "supervisors", "music_libraries", "platforms",
    "ad_agencies", "grants", "competitions", "festivals",
]

# Values that mean "no data" — treated as empty.
_EMPTY = {"", "not specified", "n/a", "na", "none", "unknown", "not publicly listed"}


def clean(v) -> str:
    if not isinstance(v, str):
        return ""
    s = v.strip()
    return "" if s.lower() in _EMPTY else s


def join_desc(*parts: str) -> str:
    """Join non-empty description fragments with a separator."""
    return "  ".join(p for p in (clean(x) for x in parts) if p)


def pills(*vals: str) -> list:
    return [p for p in (clean(v) for v in vals) if p]


def map_entry(cat: str, e: dict) -> dict:
    """Map one catalogue entry to a deck card based on its category schema."""
    g = lambda k: clean(e.get(k, ""))

    if cat == "agencies":
        return dict(title=g("name"), subtitle=g("location"),
                    desc=g("submission_guidelines"),
                    pills=pills(e.get("roster_genre_focus"), e.get("regions")),
                    url=g("website"), contact=g("contact_info"))

    if cat == "supervisors":
        return dict(title=g("name"), subtitle=g("company"),
                    desc=join_desc(e.get("submission_policy"), e.get("notable_projects")),
                    pills=pills(e.get("location")),
                    url="", contact=g("contact_info"))

    if cat == "music_libraries":
        return dict(title=g("name"), subtitle=g("submission_status"),
                    desc=join_desc(e.get("requirements_genres"), e.get("payout_model")),
                    pills=[], url=g("url"), contact="")

    if cat == "platforms":
        return dict(title=g("name"), subtitle="",
                    desc=join_desc(e.get("description"), e.get("requirements")),
                    pills=[], url=g("url"), contact="")

    if cat == "ad_agencies":
        leads = g("creative_director_or_leads")
        return dict(title=g("name"), subtitle=g("location"),
                    desc=(f"Leads: {leads}" if leads else ""),
                    pills=[], url=g("website"), contact=g("contact_info"))

    if cat == "grants":
        deadlines = g("deadlines")
        return dict(title=g("name"), subtitle=g("organization"),
                    desc=join_desc(e.get("eligibility_summary"),
                                   f"Deadlines: {deadlines}" if deadlines else ""),
                    pills=[], url=g("url"), contact="")

    if cat == "competitions":
        return dict(title=g("name"), subtitle=g("deadlines"),
                    desc=join_desc(e.get("prizes_categories"), e.get("entry_fees_requirements")),
                    pills=[], url=g("url"), contact="")

    if cat == "festivals":
        return dict(title=g("name"), subtitle=g("location"),
                    desc=join_desc(e.get("application_window"), e.get("requirements_fees")),
                    pills=pills(e.get("location")), url=g("url"), contact="")

    # Fallback: best-effort generic mapping.
    return dict(title=g("name"), subtitle="", desc="", pills=[],
                url=g("url"), contact=g("contact_info"))


def build() -> list:
    data = json.loads(CATALOGUE.read_text())
    records = []
    for cat in CATEGORY_ORDER:
        for e in data.get(cat, []):
            if not isinstance(e, dict) or not clean(e.get("name", "")):
                continue
            card = map_entry(cat, e)
            card["cat"] = cat
            records.append(card)
    return records


def main():
    records = build()
    if "--json" in sys.argv:
        print(json.dumps(records, ensure_ascii=False))
        return

    lines = ["window.RECORDS = ["]
    lines += [f"  {json.dumps(r, ensure_ascii=False)}," for r in records]
    lines.append("];")
    RECORDS.write_text("\n".join(lines) + "\n")

    # Summary
    from collections import Counter
    counts = Counter(r["cat"] for r in records)
    print(f"Wrote {len(records)} cards to {RECORDS}")
    for cat in CATEGORY_ORDER:
        if counts.get(cat):
            print(f"  {cat}: {counts[cat]}")


if __name__ == "__main__":
    main()
