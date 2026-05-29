from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from document_categories import DOCUMENT_CATEGORY_COLUMNS, classify_document_category
from csv_backup import write_csv_with_backup
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
        "title": "Indian Journal of Archaeology",
        "category": "Research Journal",
        "region": "India",
        "source": "Indian Journal of Archaeology",
        "link": "https://ijarch.com/",
        "notes": "Open-access archaeology journal with Indian archaeology articles.",
    },
    {
        "title": "Indian Journal of Archaeology Volume 9 Number 3",
        "category": "Research Journal",
        "region": "India",
        "source": "Indian Journal of Archaeology",
        "link": "https://ijarch.com/ija-vol-9-number-3/",
        "notes": "Issue page for Indian archaeology research articles.",
    },
    {
        "title": "Indo Archaeology Research Journal",
        "category": "Research Journal",
        "region": "India",
        "source": "Indo Archaeology",
        "link": "https://research.indoarchaeology.org/",
        "notes": "Open-access peer-reviewed archaeology journal and research platform.",
    },
    {
        "title": "Journal of Archaeological Studies in India",
        "category": "Research Journal",
        "region": "India",
        "source": "ARF Journals",
        "link": "https://www.arfjournals.com/image/79033_editor_noteampcontent.pdf",
        "notes": "Open-access journal PDF for archaeological studies in India.",
    },
    {
        "title": "Journal of Archaeological Studies in India Article",
        "category": "Research Paper",
        "region": "India",
        "source": "ARF Journals",
        "link": "https://www.arfjournals.com/image/catalog/Journals%20Papers/JASI/2023/No%201%20%282023%29/4_Riza.pdf",
        "notes": "Article PDF from Journal of Archaeological Studies in India.",
    },
    {
        "title": "Bulletin of the Deccan College Post-Graduate and Research Institute",
        "category": "Research Journal",
        "region": "India",
        "source": "JSTOR",
        "link": "https://www.jstor.org/journal/bulldeccollrese",
        "notes": "Research periodical covering ancient Indian history, culture, archaeology, anthropology, Sanskrit, and linguistics.",
    },
    {
        "title": "Deccan College Excavations at Maheshwar and Navdatoli 1952-53",
        "category": "Archaeology Report",
        "region": "India",
        "source": "Deccan College",
        "link": "https://virasat.dcpune.ac.in/jspui/handle/123456789/35810?mode=full",
        "notes": "Repository record for excavation report.",
    },
    {
        "title": "Mansar Site and Excavation Archive",
        "category": "Excavation Archive",
        "region": "India",
        "source": "Zenodo",
        "link": "https://zenodo.org/record/583415",
        "notes": "Mansar site and excavation archive hosted on Zenodo.",
    },
    {
        "title": "Indian Archaeology 2000-2001 A Review",
        "category": "ASI Review PDF",
        "region": "India",
        "source": "NMMA",
        "link": "https://nmma.nic.in/nmma/NAS1/nmma_doc/IAR/Indian%20Archaeology%202000-2001%20A%20Review.pdf",
        "notes": "Indian Archaeology - A Review annual report PDF.",
    },
    {
        "title": "Indian Archaeology 1962-63 A Review",
        "category": "ASI Review PDF",
        "region": "India",
        "source": "NMMA",
        "link": "https://nmma.nic.in/nmma/NAS1/nmma_doc/IAR/Indian%20Archaeology%201962-63%20A%20Review.pdf",
        "notes": "Indian Archaeology - A Review annual report PDF.",
    },
    {
        "title": "Indian Archaeology 1981-82 A Review",
        "category": "ASI Review PDF",
        "region": "India",
        "source": "Rhino Resource Center",
        "link": "https://www.rhinoresourcecenter.com/pdf_files/151/1513420370.pdf",
        "notes": "Indian Archaeology - A Review annual report PDF mirror.",
    },
    {
        "title": "Indian Archaeology Today",
        "category": "Archaeology Article PDF",
        "region": "India",
        "source": "IGNCA",
        "link": "https://ignca.gov.in/Asi_data/65402.pdf",
        "notes": "Article/report PDF related to Indian archaeology methods and practice.",
    },
    {
        "title": "Mapping the Indian Palaeolithic",
        "category": "Research Paper",
        "region": "India",
        "source": "Journal of Computer Applications in Archaeology",
        "link": "https://journal.caa-international.org/articles/10.5334/jcaa.148",
        "notes": "Open-access paper mapping Indian Lower Palaeolithic data from Indian Archaeology - A Review.",
    },
    {
        "title": "Mapping the Indian Palaeolithic Repository",
        "category": "Research Repository",
        "region": "India",
        "source": "Cambridge Repository",
        "link": "https://www.repository.cam.ac.uk/items/34ccf187-4850-484d-bb78-0cc6b42be7e7",
        "notes": "Repository record for Mapping the Indian Palaeolithic.",
    },
    {
        "title": "Acheulean Habitation in the Upper Son Valley",
        "category": "Research Paper",
        "region": "India",
        "source": "Antiquity",
        "link": "https://www.cambridge.org/core/journals/antiquity/article/acheulean-habitation-in-the-upper-son-valley-india-insights-into-early-occupation-and-environment/15902540040AA35F00386879377FBD22",
        "notes": "Open-access Antiquity paper on Acheulean occupation in India.",
    },
    {
        "title": "Harappan Cemetery of Rakhigarhi",
        "category": "Research Paper",
        "region": "India",
        "source": "PLOS ONE",
        "link": "https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0192299",
        "notes": "Open-access paper on archaeological and anthropological studies at Rakhigarhi.",
    },
    {
        "title": "Rural Complexity and Ceramic Economy in the Indus Civilisation",
        "category": "Research Paper",
        "region": "India",
        "source": "PMC",
        "link": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7643715/",
        "notes": "Open-access paper on Indus-period villages in northwest India.",
    },
    {
        "title": "Ground Penetrating Radar Investigations at Panchala and Vatsa Capitals",
        "category": "Research Paper",
        "region": "India",
        "source": "ScienceDirect",
        "link": "https://www.sciencedirect.com/science/article/pii/S2352409X23004467",
        "notes": "Paper on GPR investigations at Ahichhatra and Kaushambi.",
    },
    {
        "title": "Agro-Pastoralism and Religious Landscapes in Early Medieval South India",
        "category": "Research Paper",
        "region": "India",
        "source": "Sage Journals",
        "link": "https://journals.sagepub.com/doi/abs/10.1177/09719458211054593",
        "notes": "Research article on South Indian archaeology and religious landscapes.",
    },
    {
        "title": "Predictive Modelling for Archaeological Sites: Ashokan Edicts",
        "category": "Research Paper",
        "region": "India",
        "source": "Current Science / CoLab",
        "link": "https://colab.ws/articles/10.18520%2Fcs%2Fv110%2Fi10%2F1916-1921",
        "notes": "Research record for predictive modelling of archaeological sites using Ashokan edicts.",
    },
    {
        "title": "Post-Colonial Indian Archaeology",
        "category": "Research Paper",
        "region": "India",
        "source": "Bulletin of the History of Archaeology",
        "link": "https://account.archaeologybulletin.org/index.php/up-j-bha/article/view/bha.262/657",
        "notes": "Open PDF/article on social and political factors in post-colonial Indian archaeology.",
    },
    {
        "title": "Buddhist Caves in Western Deccan",
        "category": "Research Paper",
        "region": "India",
        "source": "Drexel Research Discovery",
        "link": "https://researchdiscovery.drexel.edu/esploro/outputs/journalArticle/The-Buddhist-Caves-in-Western-Deccan/991020535067304721",
        "notes": "Open record for paper on Buddhist caves in western Deccan.",
    },
    {
        "title": "Developing Indian Pasts: ASI and Technical Assistance in Nepal",
        "category": "Research Paper",
        "region": "South Asia",
        "source": "Sage Journals",
        "link": "https://journals.sagepub.com/doi/pdf/10.1177/00732753251398270",
        "notes": "PDF on ASI and Indian archaeological standards beyond India.",
    },
    {
        "title": "Network Analysis of Indus Civilization Inscriptions",
        "category": "Research Paper",
        "region": "South Asia",
        "source": "arXiv",
        "link": "https://arxiv.org/abs/1005.4997",
        "notes": "Paper using network analysis on undeciphered Indus inscriptions.",
    },
    {
        "title": "Collaborative Mapping of Archaeological Sites using UAVs",
        "category": "Research Paper",
        "region": "India",
        "source": "arXiv",
        "link": "https://arxiv.org/abs/2105.07644",
        "notes": "Paper creating a 3D map of Sadra Fort in Gujarat using UAVs.",
    },
    {
        "title": "Improving Heritage Management in India",
        "category": "Policy Report PDF",
        "region": "India",
        "source": "NITI Aayog",
        "link": "https://www.niti.gov.in/sites/default/files/2023-03/ImprovingHeritageManagement-in-India.pdf",
        "notes": "Government report discussing heritage management and excavation report gaps.",
    },
    {
        "title": "MINA Map Indian Archaeology Project",
        "category": "Digital Archaeology Project",
        "region": "India",
        "source": "MINA",
        "link": "https://dngupta.github.io/mina.github.io/project",
        "notes": "Project using Indian Archaeology - A Review data for web-based visualization.",
    },
    {
        "title": "MINA Map Indian Archaeology Blog",
        "category": "Archaeology Blog",
        "region": "India",
        "source": "MINA",
        "link": "https://mapindianarch.wordpress.com/",
        "notes": "Blog on the history and practice of Indian archaeology.",
    },
    {
        "title": "MINA Map Indian Archaeology PDF",
        "category": "Digital Archaeology PDF",
        "region": "India",
        "source": "Livingmaps Network",
        "link": "https://livingmaps.squarespace.com/s/LMR10_NehaGuptaEtAl.pdf",
        "notes": "PDF article on opening post-colonial archaeological research in India through web-based geovisualisation.",
    },
    {
        "title": "Livingmaps: Opening Post-Colonial Archaeological Research in India",
        "category": "Article",
        "region": "India",
        "source": "Livingmaps Network",
        "link": "https://www.livingmaps.org/neha-gupta",
        "notes": "Article about Indian archaeology web-based geovisualisation.",
    },
    {
        "title": "Unearthing India Blog",
        "category": "Archaeology Blog",
        "region": "India",
        "source": "Unearthing India",
        "link": "https://www.unearthingindia.in/",
        "notes": "Blog spotlighting Indian ancient history and archaeological research.",
    },
    {
        "title": "Explore Ancient India Blog",
        "category": "Archaeology Blog",
        "region": "India",
        "source": "Explore Ancient India",
        "link": "https://www.exploreancientindia.com/",
        "notes": "Blog covering ancient India from historical, archaeological, and classical perspectives.",
    },
    {
        "title": "Sahapedia",
        "category": "Heritage Articles",
        "region": "India",
        "source": "Sahapedia",
        "link": "https://www.sahapedia.org/",
        "notes": "Open online resource on arts, cultures, and heritage of India.",
    },
    {
        "title": "Sahapedia: The Indus Civilization",
        "category": "Article Collection",
        "region": "India",
        "source": "Sahapedia",
        "link": "https://www.sahapedia.org/index.php/the-indus-civilization",
        "notes": "Sahapedia article collection on Indus Civilization.",
    },
    {
        "title": "MAP Academy: Daimabad Bronzes",
        "category": "Article",
        "region": "India",
        "source": "MAP Academy",
        "link": "https://mapacademy.io/article/daimabad-bronzes/",
        "notes": "Article discussing Daimabad bronzes and excavation context.",
    },
    {
        "title": "Indian Express: Kutch Harappan Graveyard",
        "category": "Article",
        "region": "India",
        "source": "Indian Express",
        "link": "https://indianexpress.com/article/long-reads/kutch-harappan-graveyard-findings-9250132/",
        "notes": "Long-read article on Harappan graveyard and Padta Bet excavation context.",
    },
    {
        "title": "Indian Express: Sinauli Chariots and Pre-Iron Age Finds",
        "category": "Article",
        "region": "India",
        "source": "Indian Express",
        "link": "https://indianexpress.com/article/express-sunday-eye/wheel-of-time-chariots-and-sophisticated-weapons-from-the-pre-iron-age-5220282/",
        "notes": "Article on ASI excavation at Sinauli.",
    },
    {
        "title": "Times of India: Rajasthan 3500-Year-Old Settlement",
        "category": "Article",
        "region": "India",
        "source": "Times of India",
        "link": "https://timesofindia.indiatimes.com/city/jaipur/rajasthan-dig-reveals-3500-year-old-settlement-asi-traces-ancient-riverbed-findings-may-link-it-to-rig-veda-era-saraswati-river/articleshow/122032942.cms",
        "notes": "News article on ASI excavation in Rajasthan.",
    },
    {
        "title": "Indian Express: Deccan College Archaeology Repository Needs",
        "category": "Article",
        "region": "India",
        "source": "Indian Express",
        "link": "https://indianexpress.com/article/india/sos-from-deccan-college-precious-pieces-of-history-dumped-in-gunny-bags-7695514/",
        "notes": "Article on archaeology collections and repository issues at Deccan College.",
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

    backup = write_csv_with_backup(fieldnames, rows, reason="add_indian_archaeology_sources")

    print(f"Added {len(added)} Indian archaeology sources.")
    print(f"CSV now has {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    for row in added:
        print(f"- {row['title']} :: {row['link']}")


if __name__ == "__main__":
    main()
