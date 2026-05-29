from __future__ import annotations

from urllib.parse import urlparse


QUALITY_COLUMNS = ["source_type", "trust_score", "usable_for_rag", "priority"]

HIGH_TRUST_DOMAINS = {
    "asi.nic.in",
    "whc.unesco.org",
    "unesco.org",
    "nationalarchives.nic.in",
    "museumsofindia.gov.in",
    "ignca.gov.in",
    "data.gov.in",
    "bhuvan.nrsc.gov.in",
    "nrsc.gov.in",
    "isro.gov.in",
    "vedas.sac.gov.in",
    "mosdac.gov.in",
    "iirs.gov.in",
    "indianculture.gov.in",
    "tnarch.gov.in",
    "archaeology.haryana.gov.in",
    "karnatakatourism.org",
}

MEDIUM_TRUST_DOMAINS = {
    "archive.org",
    "dsal.uchicago.edu",
    "caa-india.org",
    "intach.org",
    "openheritage3d.org",
    "cyark.org",
    "britishmuseum.org",
    "metmuseum.org",
    "loc.gov",
    "si.edu",
    "europeana.eu",
    "wikidata.org",
    "penn.museum",
    "ecommons.cornell.edu",
    "link.springer.com",
    "mdpi.com",
    "britannica.com",
}

TOOL_DOMAINS = {
    "github.com",
    "git-scm.com",
    "python.org",
    "streamlit.io",
    "vercel.com",
    "render.com",
    "railway.app",
    "postman.com",
    "openai.com",
    "ollama.com",
    "jdownloader.org",
    "httrack.com",
}


def domain_for(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def domain_matches(domain: str, trusted_domains: set[str]) -> bool:
    return any(domain == trusted or domain.endswith(f".{trusted}") for trusted in trusted_domains)


def infer_source_type(row: dict[str, str]) -> str:
    category = row.get("category", "").lower()
    url = row.get("link", "").lower()
    domain = domain_for(row.get("link", ""))

    if domain in TOOL_DOMAINS or category == "tool":
        return "tool"
    if "example.com" in domain or "example" in url:
        return "example"
    if url.endswith(".pdf") or "/pdf/" in url or category in {"pdf", "heritage pdf"}:
        return "pdf"
    if "dataset" in category or "data" in category:
        return "dataset"
    if any(term in category for term in ("gis", "map", "mapping", "geospatial", "satellite", "remote sensing")):
        return "gis"
    if "research" in category or "arxiv" in domain or "mdpi" in domain:
        return "research"
    if "archive" in category or "library" in category:
        return "archive"
    return "source_page"


def quality_for(row: dict[str, str]) -> dict[str, str]:
    url = row.get("link", "")
    domain = domain_for(url)
    status = row.get("status", "pending").lower() or "pending"
    source_type = infer_source_type(row)

    score = 50
    if domain_matches(domain, HIGH_TRUST_DOMAINS):
        score += 35
    elif domain_matches(domain, MEDIUM_TRUST_DOMAINS):
        score += 20

    if source_type == "pdf":
        score += 15
    elif source_type in {"archive", "dataset", "gis", "research"}:
        score += 8
    elif source_type == "tool":
        score -= 35
    elif source_type == "example":
        score -= 50

    if status in {"verified", "pdf"}:
        score += 15
    elif status == "redirect":
        score += 8
    elif status == "pending":
        score -= 5
    elif status == "broken":
        score -= 40

    score = max(0, min(100, score))
    archaeology_valuable = source_type in {
        "pdf",
        "archive",
        "dataset",
        "gis",
        "research",
        "source_page",
    }
    usable_for_rag = (
        "yes"
        if archaeology_valuable and source_type not in {"tool", "example"} and status != "broken"
        else "no"
    )

    if score >= 85:
        priority = "high"
    elif score >= 60:
        priority = "medium"
    elif score >= 35:
        priority = "low"
    else:
        priority = "exclude"

    return {
        "source_type": source_type,
        "trust_score": str(score),
        "usable_for_rag": usable_for_rag,
        "priority": priority,
    }
