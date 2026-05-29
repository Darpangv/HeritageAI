from __future__ import annotations


DOCUMENT_CATEGORY_COLUMNS = ["document_category", "category_confidence"]

DOCUMENT_CATEGORIES = [
    "Excavation Report",
    "Annual Review",
    "Research Paper",
    "Journal / Periodical",
    "Book / Monograph",
    "Manuscript / Text",
    "Archive / Repository",
    "Museum / Collection",
    "Monument / Site Record",
    "GIS / Map / Satellite",
    "Dataset",
    "Government / Policy",
    "Conservation / Management",
    "Article / Blog",
    "Tool / Platform",
    "Unknown / Mixed",
]


def _haystack(row: dict[str, str]) -> str:
    return " ".join(
        row.get(column, "")
        for column in ["title", "category", "source", "link", "notes", "source_type"]
    ).lower()


def classify_document_category(row: dict[str, str]) -> dict[str, str]:
    text = _haystack(row)
    source_type = row.get("source_type", "").lower()
    url = row.get("link", "").lower()
    original_category = row.get("category", "").lower()

    if original_category in {"article", "article / blog", "heritage articles", "article collection"}:
        return {"document_category": "Article / Blog", "category_confidence": "88"}

    rules: list[tuple[str, int, tuple[str, ...]]] = [
        ("Tool / Platform", 95, ("github", "python.org", "streamlit", "openai.com", "tool", "platform")),
        ("GIS / Map / Satellite", 95, ("gis", "map", "mapping", "geospatial", "satellite", "remote sensing", "earth observation", "bhuvan", "vedas", "mosdac", "sentinel", "landsat", "uav")),
        ("Excavation Report", 95, ("excavation report", "excavations at", "excavation archive", "adichchanallur", "maheshwar", "navdatoli")),
        ("Annual Review", 95, ("indian archaeology", "a review", "asi review", "annual report")),
        ("Dataset", 90, ("dataset", "catalog", "data.gov", "open data", "repository dataset")),
        ("Research Paper", 90, ("research paper", "journal article", "doi", "plos", "arxiv", "springer", "sage", "sciencedirect", "antiquity", "current science", "pmc.ncbi")),
        ("Journal / Periodical", 88, ("research journal", "journal", "periodical", "bulletin")),
        ("Book / Monograph", 86, ("book", "monograph", "public domain books")),
        ("Manuscript / Text", 86, ("manuscript", "inscription", "epigraphy", "textual record")),
        ("Museum / Collection", 86, ("museum", "collection", "artifact", "artefact")),
        ("Monument / Site Record", 84, ("monument", "site record", "protected monument", "temple", "hampi", "site")),
        ("Conservation / Management", 84, ("conservation", "management", "heritage management", "world heritage")),
        ("Government / Policy", 82, ("government", "policy", "niti", "ministry", ".gov.in", "asi.nic.in")),
        ("Archive / Repository", 82, ("archive", "repository", "library", "zenodo", "archive.org", "ignca")),
        ("Article / Blog", 78, ("article", "blog", "news", "indianexpress", "timesofindia", "sahapedia", "mapacademy")),
    ]

    for category, confidence, terms in rules:
        if any(term in text for term in terms):
            return {"document_category": category, "category_confidence": str(confidence)}

    if source_type == "pdf" or url.endswith(".pdf"):
        return {"document_category": "Unknown / Mixed", "category_confidence": "55"}
    if source_type in {"archive", "source_page"}:
        return {"document_category": "Archive / Repository", "category_confidence": "60"}
    if source_type == "research":
        return {"document_category": "Research Paper", "category_confidence": "65"}
    if source_type == "dataset":
        return {"document_category": "Dataset", "category_confidence": "65"}
    if source_type == "gis":
        return {"document_category": "GIS / Map / Satellite", "category_confidence": "65"}

    return {"document_category": "Unknown / Mixed", "category_confidence": "40"}
