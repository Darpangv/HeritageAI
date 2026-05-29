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
        "title": "UNESCO Buddhist Monuments at Sanchi",
        "category": "Monument / Site Record",
        "region": "Madhya Pradesh",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/524/",
        "notes": "Maurya/Ashoka-linked Buddhist monument complex and official World Heritage source.",
    },
    {
        "title": "Britannica Ashoka",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/biography/Ashoka",
        "notes": "Reference source for Ashoka, Mauryan emperor, edicts, and Buddhist patronage.",
    },
    {
        "title": "Britannica Mauryan Empire",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/place/Mauryan-empire",
        "notes": "Reference source for the Mauryan Empire and rulers including Chandragupta and Ashoka.",
    },
    {
        "title": "UNESCO Archaeological Site of Nalanda Mahavihara",
        "category": "Monument / Site Record",
        "region": "Bihar",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/1502/",
        "notes": "Official UNESCO page for Nalanda, useful for Gupta and later dynastic Buddhist learning context.",
    },
    {
        "title": "Britannica Gupta Dynasty",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Gupta-dynasty",
        "notes": "Reference source for Gupta rulers including Samudragupta and Chandragupta II.",
    },
    {
        "title": "UNESCO Great Living Chola Temples",
        "category": "Monument / Site Record",
        "region": "Tamil Nadu",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/250/",
        "notes": "Official source for Chola temples, Rajaraja I, Rajendra I, Brihadisvara, Gangaikondacholapuram, and Darasuram.",
    },
    {
        "title": "Britannica Chola Dynasty",
        "category": "Article",
        "region": "Tamil Nadu",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Chola-dynasty",
        "notes": "Reference source for Chola dynasty and rulers including Rajaraja and Rajendra Chola.",
    },
    {
        "title": "Smithsonian Chola Bronzes",
        "category": "Museum / Collection",
        "region": "Tamil Nadu",
        "source": "Smithsonian",
        "link": "https://asia.si.edu/learn/india/chola-bronzes/",
        "notes": "Museum source for Chola-period bronze sculpture and religious art.",
    },
    {
        "title": "UNESCO Group of Monuments at Mahabalipuram",
        "category": "Monument / Site Record",
        "region": "Tamil Nadu",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/249/",
        "notes": "Official source for Pallava monuments at Mamallapuram/Mahabalipuram.",
    },
    {
        "title": "Britannica Pallava Dynasty",
        "category": "Article",
        "region": "Tamil Nadu",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Pallava-dynasty",
        "notes": "Reference source for Pallava dynasty and rulers such as Mahendravarman and Narasimhavarman.",
    },
    {
        "title": "UNESCO Group of Monuments at Pattadakal",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/239/",
        "notes": "Official source for Chalukya architecture at Pattadakal.",
    },
    {
        "title": "Britannica Chalukya Dynasty",
        "category": "Article",
        "region": "Deccan",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Chalukya-dynasty",
        "notes": "Reference source for Chalukya dynasty, Badami, Aihole, Pattadakal, and Pulakeshin.",
    },
    {
        "title": "UNESCO Ellora Caves",
        "category": "Monument / Site Record",
        "region": "Maharashtra",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/243/",
        "notes": "Official source for Ellora, Kailasa temple, and Rashtrakuta-period monument context.",
    },
    {
        "title": "Britannica Rashtrakuta Dynasty",
        "category": "Article",
        "region": "Deccan",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Rashtrakuta-dynasty",
        "notes": "Reference source for Rashtrakuta rulers including Amoghavarsha and Krishna I.",
    },
    {
        "title": "UNESCO Sacred Ensembles of the Hoysalas",
        "category": "Monument / Site Record",
        "region": "Karnataka",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/1670/",
        "notes": "Official source for Hoysala temples at Belur, Halebidu, and Somanathapura.",
    },
    {
        "title": "Britannica Hoysala Dynasty",
        "category": "Article",
        "region": "Karnataka",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Hoysala-dynasty",
        "notes": "Reference source for Hoysala dynasty and rulers including Vishnuvardhana.",
    },
    {
        "title": "UNESCO Kakatiya Rudreshwara Ramappa Temple",
        "category": "Monument / Site Record",
        "region": "Telangana",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/1570/",
        "notes": "Official source for Kakatiya-period Ramappa Temple.",
    },
    {
        "title": "Britannica Kakatiya Dynasty",
        "category": "Article",
        "region": "Telangana",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Kakatiya-dynasty",
        "notes": "Reference source for Kakatiya rulers and Warangal context.",
    },
    {
        "title": "Britannica Pandya Dynasty",
        "category": "Article",
        "region": "Tamil Nadu",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Pandya-dynasty",
        "notes": "Reference source for Pandya dynasty and Madurai context.",
    },
    {
        "title": "Britannica Satavahana Dynasty",
        "category": "Article",
        "region": "Deccan",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Satavahana-dynasty",
        "notes": "Reference source for Satavahana dynasty, Satakarni rulers, and Deccan history.",
    },
    {
        "title": "UNESCO Taj Mahal",
        "category": "Monument / Site Record",
        "region": "Uttar Pradesh",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/252/",
        "notes": "Official source for Shah Jahan and Mughal architecture.",
    },
    {
        "title": "UNESCO Agra Fort",
        "category": "Monument / Site Record",
        "region": "Uttar Pradesh",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/251/",
        "notes": "Official source for Mughal imperial architecture and rulers including Akbar, Jahangir, and Shah Jahan.",
    },
    {
        "title": "UNESCO Fatehpur Sikri",
        "category": "Monument / Site Record",
        "region": "Uttar Pradesh",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/255/",
        "notes": "Official source for Akbar's Mughal capital Fatehpur Sikri.",
    },
    {
        "title": "UNESCO Humayun's Tomb",
        "category": "Monument / Site Record",
        "region": "Delhi",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/232/",
        "notes": "Official source for Humayun and Mughal funerary architecture.",
    },
    {
        "title": "Britannica Mughal Dynasty",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/topic/Mughal-dynasty",
        "notes": "Reference source for Mughal rulers including Babur, Humayun, Akbar, Jahangir, Shah Jahan, and Aurangzeb.",
    },
    {
        "title": "Britannica Akbar",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/biography/Akbar",
        "notes": "Reference source for Akbar and Mughal imperial policy.",
    },
    {
        "title": "Britannica Shah Jahan",
        "category": "Article",
        "region": "India",
        "source": "Britannica",
        "link": "https://www.britannica.com/biography/Shah-Jahan",
        "notes": "Reference source for Shah Jahan and Mughal architecture.",
    },
    {
        "title": "UNESCO Maratha Military Landscapes of India",
        "category": "Monument / Site Record",
        "region": "India",
        "source": "UNESCO World Heritage Centre",
        "link": "https://whc.unesco.org/en/list/1721/",
        "notes": "Official UNESCO source for Maratha military landscapes and fort systems.",
    },
    {
        "title": "Britannica Shivaji",
        "category": "Article",
        "region": "Maharashtra",
        "source": "Britannica",
        "link": "https://www.britannica.com/biography/Shivaji",
        "notes": "Reference source for Chhatrapati Shivaji and the Maratha polity.",
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

    backup = write_csv_with_backup(fieldnames, rows, reason="add_dynasty_sources")
    print(f"Added {len(added)} dynasty/ruler sources.")
    print(f"CSV now has {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    for row in added:
        print(f"- {row['title']} :: {row['link']}")


if __name__ == "__main__":
    main()
