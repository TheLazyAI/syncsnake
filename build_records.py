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
from datetime import date
from pathlib import Path

import feedback_store

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


import re


def _norm_name(name: str) -> str:
    """Normalize a name for duplicate detection (case/punctuation/space-insensitive)."""
    return re.sub(r"[^a-z0-9]", "", clean(name).lower())


def _completeness(card: dict) -> int:
    """How many useful fields a card actually fills — used to keep the richest dupe."""
    score = 0
    for k in ("subtitle", "desc", "url", "contact"):
        if clean(card.get(k, "")):
            score += 1
    score += len(card.get("pills", []) or [])
    return score


_REAL_URL = re.compile(r"^https?://", re.I)


def _has_real_url(card: dict) -> bool:
    u = clean(card.get("url", ""))
    return bool(u) and bool(_REAL_URL.match(u)) and "not specified" not in u.lower()


# Best-first ordering: real URL first, then richer cards. Stable within ties.
def _quality(card: dict):
    return (1 if _has_real_url(card) else 0, _completeness(card))


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
# "Now" for expiry decisions — the real current month, so expiry never goes stale.
_TODAY = date.today()
_NOW = (_TODAY.year, _TODAY.month)


def is_expired(text: str) -> bool:
    """Heuristic: True only when a deadline is clearly in the past with no future date.
    Ongoing/evergreen/unknown deadlines return False (we keep them)."""
    t = clean(text).lower()
    if not t:
        return False
    if any(w in t for w in ("ongoing", "rolling", "year-round", "year round", "evergreen", "anytime")):
        return False
    past = future = False
    for m, mi in _MONTHS.items():
        for y in re.findall(rf"{m}[a-z]*\.?\s*\d*,?\s*(20\d\d)", t):
            if (int(y), mi) < _NOW:
                past = True
            else:
                future = True
    if re.search(r"\b202[0-5]\b", t) and not future:
        past = True
    if ("closed" in t or "passed" in t) and not future:
        past = True
    return past and not future


# Which catalogue field carries the deadline, per category (for expiry filtering).
_DEADLINE_FIELD = {"grants": "deadlines", "competitions": "deadlines", "festivals": "application_window"}


def build() -> list:
    data = json.loads(CATALOGUE.read_text())
    blocked = feedback_store.blocked_ids()   # human flags survive regeneration
    records = []
    for cat in CATEGORY_ORDER:
        # Collapse exact-duplicate names within a category, keeping the most
        # complete card (the agent occasionally emits the same entity 2-3x).
        best: dict = {}      # normalized name -> card
        order: list = []     # preserve first-seen order
        dl_field = _DEADLINE_FIELD.get(cat)
        for e in data.get(cat, []):
            if not isinstance(e, dict) or not clean(e.get("name", "")):
                continue
            # Skip anything the user flagged (expired/duplicate/hallucinated) — this
            # is what makes a deck correction stick across rebuilds.
            bid = feedback_store.block_key(cat, e.get("name", ""))
            if bid in blocked:
                continue
            # Drop clearly-expired time-sensitive opportunities so stale dates
            # never surface on a card (grants/competitions/festivals only).
            if dl_field and is_expired(e.get(dl_field, "")):
                continue
            card = map_entry(cat, e)
            card["cat"] = cat
            card["id"] = bid       # stable id shared with the deck + feedback store
            key = _norm_name(e.get("name", ""))
            if key not in best:
                best[key] = card
                order.append(key)
            elif _completeness(card) > _completeness(best[key]):
                best[key] = card   # replace with the richer duplicate, keep position
        # Best-first within the category (stable): real URL + completeness lead.
        cards = [best[k] for k in order]
        cards.sort(key=_quality, reverse=True)
        records.extend(cards)
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
