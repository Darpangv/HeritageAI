from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


DYNASTY_ALIASES = {
    "maurya": {
        "terms": ("maurya", "mauryan", "ashoka", "asoka", "chandragupta maurya", "bindusara"),
        "boost_terms": ["Maurya", "Mauryan", "Ashoka", "Asoka", "Chandragupta Maurya", "Sanchi", "edicts"],
    },
    "gupta": {
        "terms": ("gupta", "samudragupta", "chandragupta ii", "vikramaditya", "skandagupta"),
        "boost_terms": ["Gupta", "Samudragupta", "Chandragupta II", "Vikramaditya", "Udayagiri"],
    },
    "chola": {
        "terms": ("chola", "rajaraja", "raja raja", "rajendra chola", "kulottunga", "brihadisvara", "gangaikonda"),
        "boost_terms": ["Chola", "Rajaraja", "Rajendra Chola", "Brihadisvara", "Gangaikondacholapuram"],
    },
    "pallava": {
        "terms": ("pallava", "mahendravarman", "narasimhavarman", "mamallapuram", "mahabalipuram"),
        "boost_terms": ["Pallava", "Narasimhavarman", "Mamallapuram", "Mahabalipuram"],
    },
    "chalukya": {
        "terms": ("chalukya", "pulakeshin", "pulakesi", "badami", "pattadakal", "aihole"),
        "boost_terms": ["Chalukya", "Pulakeshin", "Badami", "Pattadakal", "Aihole"],
    },
    "rashtrakuta": {
        "terms": ("rashtrakuta", "amoghavarsha", "krishna i", "ellora", "kailasa temple"),
        "boost_terms": ["Rashtrakuta", "Amoghavarsha", "Krishna I", "Ellora", "Kailasa"],
    },
    "pandya": {
        "terms": ("pandya", "pandyan", "madurai", "meenakshi", "jatarvarman", "maravarman"),
        "boost_terms": ["Pandya", "Pandyan", "Madurai", "Meenakshi"],
    },
    "satavahana": {
        "terms": ("satavahana", "satakarni", "gautamiputra", "amaravati", "nashik caves"),
        "boost_terms": ["Satavahana", "Satakarni", "Gautamiputra", "Amaravati", "Nashik caves"],
    },
    "kakatiya": {
        "terms": ("kakatiya", "rudrama devi", "rudramadevi", "ganapati deva", "warangal", "ramappa"),
        "boost_terms": ["Kakatiya", "Rudrama Devi", "Warangal", "Ramappa"],
    },
    "hoysala": {
        "terms": ("hoysala", "vishnuvardhana", "belur", "halebidu", "somanathapura"),
        "boost_terms": ["Hoysala", "Vishnuvardhana", "Belur", "Halebidu", "Somanathapura"],
    },
    "mughal": {
        "terms": ("mughal", "babur", "humayun", "akbar", "jahangir", "shah jahan", "aurangzeb", "fatehpur sikri", "taj mahal"),
        "boost_terms": ["Mughal", "Babur", "Humayun", "Akbar", "Jahangir", "Shah Jahan", "Aurangzeb", "Fatehpur Sikri", "Taj Mahal"],
    },
    "maratha": {
        "terms": ("maratha", "shivaji", "chhatrapati shivaji", "sambhaji", "shahu", "peshwa", "raigad", "shivneri"),
        "boost_terms": ["Maratha", "Shivaji", "Chhatrapati Shivaji", "Raigad", "Shivneri", "forts"],
    },
}


def detect_dynasty(text: str) -> tuple[str, dict] | None:
    for dynasty, config in DYNASTY_ALIASES.items():
        if _contains(text, config["terms"]):
            return dynasty, config
    return None


def route_question(question: str) -> dict:
    from map_views import detect_map_site

    text = question.lower()
    research_map_terms = ("research grade", "research-grade", "archaeology", "archaeological", "gis", "satellite", "remote sensing", "layers")
    route = {
        "intent": "general_heritage",
        "answer_mode": "rag",
        "preferred_categories": [],
        "boost_terms": [],
        "reason": "default heritage RAG route",
    }

    inventory_terms = ("how many", "count", "total", "pending", "broken", "verified", "status", "csv")
    dynasty_match = detect_dynasty(text)

    if _contains(text, inventory_terms) or re.search(r"\b(how many|count|total)\b.*\b(links|sources)\b", text):
        route.update(
            {
                "intent": "source_inventory",
                "answer_mode": "source_inventory",
                "reason": "question asks about source database status/counts",
            }
        )
        return route

    if dynasty_match:
        dynasty, config = dynasty_match
        route.update(
            {
                "intent": "dynasty_or_ruler",
                "preferred_categories": ["Monument / Site Record", "Research Paper", "Archive / Repository", "Museum / Collection"],
                "boost_terms": config["boost_terms"],
                "required_terms": list(config["terms"]),
                "dynasty": dynasty,
                "reason": f"question appears to refer to the {dynasty.title()} dynasty/rulers",
            }
        )
    elif _contains(text, ("gis", "map", "mapping", "satellite", "remote sensing", "earth observation", "bhuvan", "vedas", "mosdac", "uav", "lidar", "coordinates")):
        route.update(
            {
                "intent": "gis_satellite",
                "preferred_categories": ["GIS / Map / Satellite", "Dataset"],
                "boost_terms": ["gis", "map", "satellite", "remote sensing", "earth observation"],
                "reason": "question asks for mapping, satellite, or geospatial evidence",
            }
        )
    elif _contains(text, ("excavation", "excavated", "trench", "burial", "urn", "stratigraphy", "dig")):
        route.update(
            {
                "intent": "excavation_report",
                "preferred_categories": ["Excavation Report", "Annual Review"],
                "boost_terms": ["excavation", "trench", "burial", "stratigraphy"],
                "reason": "question asks for excavation evidence",
            }
        )
    elif _contains(text, ("annual review", "indian archaeology a review", "iar", "asi review")):
        route.update(
            {
                "intent": "annual_review",
                "preferred_categories": ["Annual Review", "Excavation Report"],
                "boost_terms": ["annual review", "indian archaeology", "a review"],
                "reason": "question asks for ASI annual review material",
            }
        )
    elif _contains(text, ("manuscript", "inscription", "epigraphy", "script", "textual")):
        route.update(
            {
                "intent": "manuscript_text",
                "preferred_categories": ["Manuscript / Text", "Archive / Repository", "Research Paper"],
                "boost_terms": ["manuscript", "inscription", "epigraphy", "script"],
                "reason": "question asks for manuscript, inscription, or textual evidence",
            }
        )
    elif _contains(text, ("paper", "research", "study", "journal", "doi", "article")):
        route.update(
            {
                "intent": "research_literature",
                "preferred_categories": ["Research Paper", "Journal / Periodical", "Article / Blog"],
                "boost_terms": ["research", "paper", "journal", "study"],
                "reason": "question asks for research literature",
            }
        )
    elif _contains(text, ("monument", "temple", "site", "structure", "fort", "gateway", "mandapa", "world heritage")):
        route.update(
            {
                "intent": "site_monument",
                "preferred_categories": ["Monument / Site Record", "Conservation / Management", "Government / Policy"],
                "boost_terms": ["monument", "site", "temple", "structure", "world heritage"],
                "reason": "question asks about monuments or site records",
            }
        )
    elif _contains(text, ("krishnadevaraya", "krishna deva raya", "shri krishnadevaraya", "sri krishnadevaraya", "krishna raya")):
        route.update(
            {
                "intent": "historical_person",
                "preferred_categories": ["Monument / Site Record", "Research Paper", "Archive / Repository"],
                "boost_terms": ["Krishnadevaraya", "Krishna Deva Raya", "Vijayanagara", "Vijayanagar", "Hampi", "Tuluva"],
                "required_terms": ["krishnadevaraya", "krishna deva raya", "krishna raya"],
                "reason": "question asks about Shri Krishnadevaraya specifically",
            }
        )
    elif _contains(text, ("vijaya empire", "vijayanagara", "vijayanagar", "hampi empire")):
        route.update(
            {
                "intent": "historical_empire",
                "preferred_categories": ["Monument / Site Record", "Research Paper", "Archive / Repository"],
                "boost_terms": ["vijayanagara", "vijayanagar", "hampi", "krishnadevaraya", "empire"],
                "reason": "question appears to refer to the Vijayanagara/Vijayanagar empire",
            }
        )

    if route["intent"] == "site_monument" and _contains(text, ("hampi", "vijayanagara", "vijayanagar")) and _contains(text, ("list", "list out", "show")):
        route["answer_mode"] = "site_list"
        route["site"] = "hampi"
        route["required_terms"] = ["hampi", "vijayanagara", "vijayanagar"]
        route["reason"] = f"{route['reason']}; question asks for a site feature list"

    source_request_terms = ("source", "sources", "link", "links", "references", "urls")
    if route["intent"] != "general_heritage" and _contains(text, source_request_terms):
        route["answer_mode"] = "source_list"
        route["reason"] = f"{route['reason']}; question asks for source links/list"

    map_site = detect_map_site(question)
    if route.get("answer_mode") != "source_list" and map_site and _contains(text, ("map", "show", "open", "view")):
        route["answer_mode"] = "research_map_view" if _contains(text, research_map_terms) else "map_view"
        route["site"] = map_site
        route["reason"] = f"{route['reason']}; question asks to display a {'research ' if route['answer_mode'] == 'research_map_view' else ''}map view"

    return route


def expand_question(question: str, route: dict) -> str:
    additions = list(route.get("boost_terms", []))
    text = question.lower()
    if "vijaya empire" in text and "vijayanagara" not in text and "vijayanagar" not in text:
        additions.extend(["Vijayanagara Empire", "Vijayanagar", "Hampi"])
    if not additions:
        return question
    return f"{question} {' '.join(additions)}"


def inventory_answer(question: str) -> str:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    status_counts = Counter(row.get("status", "blank") or "blank" for row in rows)
    category_counts = Counter(row.get("document_category", "blank") or "blank" for row in rows)
    usable_counts = Counter(row.get("usable_for_rag", "blank") or "blank" for row in rows)

    text = question.lower()
    lines = [f"Total links in the source database: {len(rows)}."]

    if _contains(text, ("pending", "broken", "verified", "redirect", "pdf", "status")):
        lines.append("Status counts:")
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {status}: {count}")

    if _contains(text, ("category", "categories", "document")):
        lines.append("Top document categories:")
        for category, count in category_counts.most_common(10):
            lines.append(f"- {category}: {count}")

    if _contains(text, ("rag", "usable", "memory")):
        lines.append("RAG usability:")
        for usable, count in sorted(usable_counts.items()):
            lines.append(f"- {usable}: {count}")

    if len(lines) == 1:
        lines.append(f"Pending links: {status_counts.get('pending', 0)}.")
        lines.append(f"Verified/PDF links: {status_counts.get('verified', 0) + status_counts.get('pdf', 0)}.")
        lines.append(f"Broken links: {status_counts.get('broken', 0)}.")

    return "\n".join(lines)


def source_list_answer(question: str, route: dict, limit: int = 12) -> str:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    preferred_categories = set(route.get("preferred_categories", []))
    boost_terms = set(re.findall(r"[a-zA-Z0-9]+", " ".join(route.get("boost_terms", [])).lower()))
    question_terms = set(re.findall(r"[a-zA-Z0-9]+", question.lower())) | boost_terms

    scored = []
    for row in rows:
        haystack = " ".join(
            row.get(column, "")
            for column in ["title", "category", "document_category", "source", "region", "notes", "link"]
        ).lower()
        required_terms = [term.lower() for term in route.get("required_terms", [])]
        if required_terms and not any(term in haystack for term in required_terms):
            fallback_terms = []
            if route.get("intent") == "historical_person":
                fallback_terms = ["vijayanagara", "vijayanagar", "hampi", "krishnadevaraya", "krishna deva raya"]
            if not fallback_terms or not any(term in haystack for term in fallback_terms):
                continue
        score = len(question_terms & set(re.findall(r"[a-zA-Z0-9]+", haystack)))
        if row.get("document_category") in preferred_categories:
            score += 5
        if row.get("usable_for_rag", "yes").lower() == "yes":
            score += 1
        if row.get("priority") == "high":
            score += 2
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [row for _, row in scored[:limit]]

    if not selected:
        return "No matching source links were found in metadata/heritage_links.csv."

    lines = [f"Top {len(selected)} matching source links for route `{route.get('intent')}`:"]
    for index, row in enumerate(selected, start=1):
        lines.append(
            f"{index}. {row.get('title', 'Untitled')} "
            f"({row.get('document_category', 'Uncategorized')}; status={row.get('status', 'unknown')}): "
            f"{row.get('link', '')}"
        )
    return "\n".join(lines)


def format_route(route: dict) -> str:
    categories = ", ".join(route.get("preferred_categories") or ["none"])
    return (
        f"intent={route.get('intent')}; "
        f"answer_mode={route.get('answer_mode')}; "
        f"preferred_categories={categories}; "
        f"reason={route.get('reason')}"
    )
