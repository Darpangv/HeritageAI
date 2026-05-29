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
        "title": "Bhuvan Indian Geo-Platform",
        "category": "GIS Mapping",
        "region": "India",
        "source": "NRSC / ISRO",
        "link": "https://bhuvan.nrsc.gov.in/",
        "notes": "Official Indian geo-platform with satellite imagery, thematic services, and map layers useful for heritage context.",
    },
    {
        "title": "Bhuvan Thematic Services",
        "category": "GIS Mapping",
        "region": "India",
        "source": "NRSC / ISRO",
        "link": "https://bhuvan-app1.nrsc.gov.in/thematic/thematic/index.php",
        "notes": "Bhuvan thematic map services for Indian geospatial layers.",
    },
    {
        "title": "Bhoonidhi Indian Earth Observation Data Hub",
        "category": "Satellite Data",
        "region": "India",
        "source": "NRSC / ISRO",
        "link": "https://bhoonidhi.nrsc.gov.in/bhoonidhi/",
        "notes": "Official ISRO/NRSC catalogue and access portal for Indian earth observation satellite data.",
    },
    {
        "title": "VEDAS Visualisation of Earth Observation Data",
        "category": "Satellite Data Platform",
        "region": "India",
        "source": "SAC / ISRO",
        "link": "https://vedas.sac.gov.in/",
        "notes": "ISRO visual analytics platform for earth observation data and thematic geospatial products.",
    },
    {
        "title": "MOSDAC Meteorological and Oceanographic Satellite Data",
        "category": "Satellite Data Platform",
        "region": "India",
        "source": "SAC / ISRO",
        "link": "https://www.mosdac.gov.in/",
        "notes": "Official ISRO satellite data portal for weather, ocean, atmosphere, and derived geospatial products.",
    },
    {
        "title": "IIRS Geoportals",
        "category": "GIS Mapping",
        "region": "India",
        "source": "IIRS / ISRO",
        "link": "https://www.iirs.gov.in/geoportals",
        "notes": "Indian Institute of Remote Sensing page linking geospatial portals and remote sensing resources.",
    },
    {
        "title": "NRSC Data Products and Services",
        "category": "Satellite Data",
        "region": "India",
        "source": "NRSC / ISRO",
        "link": "https://www.nrsc.gov.in/",
        "notes": "Official National Remote Sensing Centre site for Indian satellite data products and services.",
    },
    {
        "title": "ISRO Earth Observation Applications",
        "category": "Satellite Data",
        "region": "India",
        "source": "ISRO",
        "link": "https://www.isro.gov.in/Applications.html",
        "notes": "Official ISRO overview of earth observation applications relevant to landscape and settlement studies.",
    },
    {
        "title": "Haryana Archaeology Satellite Mapping",
        "category": "GIS Mapping",
        "region": "Haryana",
        "source": "Department of Archaeology and Museums Haryana",
        "link": "https://archaeology.haryana.gov.in/satellite-mapping/",
        "notes": "State archaeology page for satellite mapping of archaeological sites in Haryana.",
    },
    {
        "title": "Centrally Protected Monuments Dataset",
        "category": "GIS Dataset",
        "region": "India",
        "source": "Open Government Data Platform India",
        "link": "https://data.gov.in/catalog/centrally-protected-monuments-archaeological-survey-india",
        "notes": "Government dataset for centrally protected monuments under ASI, useful for geocoding and map overlays.",
    },
    {
        "title": "Mapping the Indian Palaeolithic GIS Article",
        "category": "GIS Research Paper",
        "region": "India",
        "source": "Journal of Computer Applications in Archaeology",
        "link": "https://journal.caa-international.org/articles/10.5334/jcaa.148",
        "notes": "Open-access article using geospatial methods to map Indian Lower Palaeolithic records.",
    },
    {
        "title": "Mapping the Indian Palaeolithic Repository",
        "category": "GIS Dataset",
        "region": "India",
        "source": "Cambridge Repository",
        "link": "https://www.repository.cam.ac.uk/items/34ccf187-4850-484d-bb78-0cc6b42be7e7",
        "notes": "Repository record for Indian Palaeolithic mapping data and outputs.",
    },
    {
        "title": "Remote Sensing and GIS in Indian Archaeology",
        "category": "Remote Sensing Research",
        "region": "India",
        "source": "Current Science",
        "link": "https://www.currentscience.ac.in/Volumes/113/10/1877.pdf",
        "notes": "Research article on remote sensing and GIS applications for Indian archaeology.",
    },
    {
        "title": "Geospatial Technology for Cultural Heritage Management",
        "category": "GIS Research Paper",
        "region": "India",
        "source": "Indian Society of Remote Sensing",
        "link": "https://link.springer.com/article/10.1007/s12524-020-01186-7",
        "notes": "Research article on geospatial technologies for cultural heritage documentation and management.",
    },
    {
        "title": "UAV Mapping of Archaeological Sites in Gujarat",
        "category": "GIS Research Paper",
        "region": "Gujarat",
        "source": "arXiv",
        "link": "https://arxiv.org/abs/2105.07644",
        "notes": "Research paper on collaborative mapping and 3D reconstruction of archaeological sites using UAVs.",
    },
    {
        "title": "Google Earth Engine",
        "category": "Satellite Data Platform",
        "region": "Global",
        "source": "Google Earth Engine",
        "link": "https://earthengine.google.com/",
        "notes": "Cloud platform for satellite imagery analysis, useful for landscape archaeology and change detection.",
    },
    {
        "title": "Google Earth Engine Sentinel-2 Surface Reflectance Dataset",
        "category": "Satellite Dataset",
        "region": "Global",
        "source": "Google Earth Engine",
        "link": "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED",
        "notes": "Sentinel-2 harmonized surface reflectance catalogue for multispectral archaeology and landscape analysis.",
    },
    {
        "title": "USGS EarthExplorer",
        "category": "Satellite Data Platform",
        "region": "Global",
        "source": "USGS",
        "link": "https://earthexplorer.usgs.gov/",
        "notes": "Satellite and aerial imagery search portal including Landsat and historical imagery useful for archaeology.",
    },
    {
        "title": "NASA Earthdata Search",
        "category": "Satellite Data Platform",
        "region": "Global",
        "source": "NASA",
        "link": "https://search.earthdata.nasa.gov/",
        "notes": "NASA earth observation data catalogue for satellite imagery and derived products.",
    },
    {
        "title": "Copernicus Data Space Ecosystem",
        "category": "Satellite Data Platform",
        "region": "Global",
        "source": "Copernicus",
        "link": "https://dataspace.copernicus.eu/",
        "notes": "European Copernicus satellite data portal, including Sentinel imagery useful for archaeological remote sensing.",
    },
    {
        "title": "OpenTopography",
        "category": "GIS Dataset",
        "region": "Global",
        "source": "OpenTopography",
        "link": "https://opentopography.org/",
        "notes": "Topographic and lidar data portal useful for landscape archaeology where coverage is available.",
    },
    {
        "title": "OpenStreetMap India",
        "category": "GIS Mapping",
        "region": "India",
        "source": "OpenStreetMap",
        "link": "https://www.openstreetmap.org/#map=5/22.351/78.668",
        "notes": "Open basemap and community geodata for India, useful as contextual map layer.",
    },
    {
        "title": "ArcGIS Living Atlas",
        "category": "GIS Mapping",
        "region": "Global",
        "source": "Esri",
        "link": "https://livingatlas.arcgis.com/",
        "notes": "Curated geospatial layers and basemaps useful for heritage mapping and environmental context.",
    },
    {
        "title": "OpenHeritage3D",
        "category": "GIS Dataset",
        "region": "Global",
        "source": "OpenHeritage3D",
        "link": "https://openheritage3d.org/",
        "notes": "Open 3D heritage datasets, useful for sites with lidar/photogrammetry coverage.",
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

    backup = write_csv_with_backup(fieldnames, rows, reason="add_gis_satellite_sources")

    print(f"Added {len(added)} GIS and satellite sources.")
    print(f"CSV now has {len(rows)} links.")
    if backup:
        print(f"Backup saved: {backup}")
    for row in added:
        print(f"- {row['title']} :: {row['link']}")


if __name__ == "__main__":
    main()
