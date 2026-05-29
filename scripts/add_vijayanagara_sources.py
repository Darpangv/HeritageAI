from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from csv_backup import write_csv_with_backup
from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category
from source_quality import QUALITY_COLUMNS, quality_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "metadata" / "heritage_links.csv"

COLUMNS = [
    "title",
    "category",
    "region",
    "source",
    "link",
    "status",
    "http_status",
    "content_type",
    "last_checked",
    "notes",
    *QUALITY_COLUMNS,
    *DOCUMENT_CATEGORY_COLUMNS,
]

SOURCES = [
    {
        "title": "ASI Hampi World Heritage Site",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "Archaeological Survey of India",
        "link": "https://asi.nic.in/pages/WorldHeritageHampi",
        "notes": "Official ASI Hampi page; mentions Krishnadeva Raya and Vijayanagara royal buildings.",
    },
    {
        "title": "UNESCO Group of Monuments at Hampi",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/241/",
        "notes": "Official UNESCO Hampi listing; states Vijayanagara reached its apogee under Krishna Deva Raya.",
    },
    {
        "title": "Karnataka Tourism Hampi",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "Karnataka Tourism",
        "link": "https://karnatakatourism.org/destinations/hampi/",
        "notes": "Official Karnataka Tourism page with Hampi, Vijayanagara, and Krishnadevaraya context.",
    },
    {
        "title": "Karnataka Tourism Hampi Utsava",
        "category": "Article / Blog",
        "region": "Karnataka",
        "source": "Karnataka Tourism",
        "link": "https://karnatakatourism.org/events/hampi-utsav/",
        "notes": "Official page connecting Vijaya Utsava traditions to Emperor Krishnadevaraya.",
    },
    {
        "title": "Karnataka Tourism Stone Chariot Hampi",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "Karnataka Tourism",
        "link": "https://old.karnatakatourism.org/tour-item/stone-chariot-hampi/",
        "notes": "Official tourism page saying the Hampi stone chariot was built by order of King Krishnadevaraya.",
    },
    {
        "title": "Karnataka Tourism Lotus Mahal",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "Karnataka Tourism",
        "link": "https://karnatakatourism.org/en/attractions/lotus-mahal",
        "notes": "Official tourism page connecting Lotus Mahal to Vijayanagara ruler Krishnadevaraya.",
    },
    {
        "title": "Karnataka Tourism Hampi Bazaar and Royal Enclosure",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "Karnataka Tourism",
        "link": "https://karnatakatourism.org/en/attractions/hampi-bazaar-royal-enclosure",
        "notes": "Official page on Vijayanagara royal center and Hampi Bazaar.",
    },
    {
        "title": "Vijayanagara Research Project Publications",
        "category": "Archive / Repository",
        "region": "Karnataka",
        "source": "Penn Museum",
        "link": "https://www.penn.museum/sites/VRP/html/Publications.html",
        "notes": "Penn Museum Vijayanagara Research Project publications and archaeology references.",
    },
    {
        "title": "Krishna Temple Complex Hampi Thesis",
        "category": "Research Repository",
        "region": "Karnataka",
        "source": "Cornell eCommons",
        "link": "https://ecommons.cornell.edu/items/0993c2f6-9296-4897-9f68-791a710c0aa2",
        "notes": "Research repository record on Krishna Temple Complex at Hampi in contemporary context.",
    },
    {
        "title": "Royal Religious Beneficence in Premodern India",
        "category": "Research Paper",
        "region": "Karnataka",
        "source": "Springer Nature",
        "link": "https://link.springer.com/article/10.1186/s40613-016-0030-z",
        "notes": "Open research article on temple patronage, Vijayanagara kingship, and capital-city visual arts.",
    },
    {
        "title": "Early Medieval Shaiva Pilgrimage Landscape at Hampi",
        "category": "GIS Research Paper",
        "region": "Karnataka",
        "source": "MDPI Religions",
        "link": "https://www.mdpi.com/2077-1444/13/6/569",
        "notes": "Open paper on Hampi sacred landscape with GIS, satellite imagery, and Vijayanagara Research Project data.",
    },
    {
        "title": "Digital Analysis of Mula Virupaksha Temple Hampi",
        "category": "GIS Research Paper",
        "region": "Karnataka",
        "source": "MDPI Heritage",
        "link": "https://www.mdpi.com/2409-9252/2/3/23",
        "notes": "Open digital archaeology paper on Hemakuta Hill and Hampi religious landscape before Vijayanagara imperial development.",
    },
    {
        "title": "Britannica Vijayanagar",
        "category": "Article",
        "region": "Karnataka",
        "source": "Britannica",
        "link": "https://www.britannica.com/place/Vijayanagar",
        "notes": "Reference article on Vijayanagar city and empire; includes Krishna Deva Raya context.",
    },
    {
        "title": "Wikimedia Vijayanagara Empire Inscriptions",
        "category": "Archive / Repository",
        "region": "Karnataka",
        "source": "Wikimedia Commons",
        "link": "https://commons.wikimedia.org/wiki/Category:Vijayanagara_Empire_inscriptions",
        "notes": "Image archive category for Vijayanagara inscriptions, including Krishnadevaraya-related inscriptions.",
    },
    {
        "title": "Honnenahalli Inscription of Shri Krishnadevaraya",
        "category": "Manuscript / Text",
        "region": "Karnataka",
        "source": "Wikimedia Commons",
        "link": "https://commons.wikimedia.org/wiki/File:Honnenahalli_Inscription_of_furnishing_the_date_of_the_demise_of_shri_Krishnadevaraya.jpg",
        "notes": "Inscription image record related to the demise date of Sri Krishnadevaraya.",
    },
]


def normalize(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def load_rows() -> tuple[list[str], list[dict[str, str]]]:
    with CSV_FILE.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    for column in COLUMNS:
        if column not in fieldnames:
            fieldnames.append(column)
    for row in rows:
        for column in fieldnames:
            row.setdefault(column, "")
    return fieldnames, rows


def main() -> None:
    fieldnames, rows = load_rows()
    existing = {normalize(row["link"]) for row in rows if row.get("link")}
    added = []

    for source in SOURCES:
        key = normalize(source["link"])
        if key in existing:
            continue
        row = {
            "title": source["title"],
            "category": source["category"],
            "region": source["region"],
            "source": source["source"],
            "link": source["link"],
            "status": "pending",
            "http_status": "",
            "content_type": "",
            "last_checked": "",
            "notes": source["notes"],
        }
        row.update(quality_for(row))
        row.update(classify_document_category(row))
        rows.append(row)
        existing.add(key)
        added.append(row)

    backup = write_csv_with_backup(fieldnames, rows, reason="add_vijayanagara_sources")
    print(f"Added {len(added)} Vijayanagara / named-person sources.")
    print(f"CSV now has {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    for row in added:
        print(f"- {row['title']} :: {row['link']}")


if __name__ == "__main__":
    main()
