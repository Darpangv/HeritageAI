from __future__ import annotations


PUBLIC_HERITAGE_MAPS = {
    "hampi": {
        "name": "Hampi World Heritage Area",
        "aliases": ("hampi", "vijayanagara", "vijayanagar"),
        "lat": 15.3350,
        "lon": 76.4600,
        "zoom": 14,
        "delta": 0.0400,
        "sources": [
            "- [S1] UNESCO Group of Monuments at Hampi: https://whc.unesco.org/en/list/241/",
            "- [S2] OpenStreetMap Hampi map view: https://www.openstreetmap.org/#map=14/15.3350/76.4600",
            "- [S3] Karnataka Tourism Hampi: https://karnatakatourism.org/destinations/hampi/",
            "- [S4] Bhuvan Indian Geo-Platform: https://bhuvan.nrsc.gov.in/",
        ],
    },
    "sanchi": {
        "name": "Buddhist Monuments at Sanchi",
        "aliases": ("sanchi", "buddhist monuments at sanchi"),
        "lat": 23.4793,
        "lon": 77.7390,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Buddhist Monuments at Sanchi: https://whc.unesco.org/en/list/524/",
            "- [S2] OpenStreetMap Sanchi map view: https://www.openstreetmap.org/#map=15/23.4793/77.7390",
        ],
    },
    "nalanda": {
        "name": "Archaeological Site of Nalanda Mahavihara",
        "aliases": ("nalanda", "nalanda mahavihara"),
        "lat": 25.1367,
        "lon": 85.4430,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Archaeological Site of Nalanda Mahavihara: https://whc.unesco.org/en/list/1502/",
            "- [S2] OpenStreetMap Nalanda map view: https://www.openstreetmap.org/#map=15/25.1367/85.4430",
        ],
    },
    "mahabalipuram": {
        "name": "Group of Monuments at Mahabalipuram",
        "aliases": ("mahabalipuram", "mamallapuram"),
        "lat": 12.6167,
        "lon": 80.1917,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Group of Monuments at Mahabalipuram: https://whc.unesco.org/en/list/249/",
            "- [S2] OpenStreetMap Mahabalipuram map view: https://www.openstreetmap.org/#map=15/12.6167/80.1917",
        ],
    },
    "pattadakal": {
        "name": "Group of Monuments at Pattadakal",
        "aliases": ("pattadakal",),
        "lat": 15.9486,
        "lon": 75.8167,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Group of Monuments at Pattadakal: https://whc.unesco.org/en/list/239/",
            "- [S2] OpenStreetMap Pattadakal map view: https://www.openstreetmap.org/#map=15/15.9486/75.8167",
        ],
    },
    "ellora": {
        "name": "Ellora Caves",
        "aliases": ("ellora", "ellora caves", "kailasa temple"),
        "lat": 20.0258,
        "lon": 75.1792,
        "zoom": 15,
        "delta": 0.0300,
        "sources": [
            "- [S1] UNESCO Ellora Caves: https://whc.unesco.org/en/list/243/",
            "- [S2] OpenStreetMap Ellora map view: https://www.openstreetmap.org/#map=15/20.0258/75.1792",
        ],
    },
    "taj_mahal": {
        "name": "Taj Mahal",
        "aliases": ("taj mahal",),
        "lat": 27.1751,
        "lon": 78.0421,
        "zoom": 16,
        "delta": 0.0150,
        "sources": [
            "- [S1] UNESCO Taj Mahal: https://whc.unesco.org/en/list/252/",
            "- [S2] OpenStreetMap Taj Mahal map view: https://www.openstreetmap.org/#map=16/27.1751/78.0421",
        ],
    },
    "agra_fort": {
        "name": "Agra Fort",
        "aliases": ("agra fort",),
        "lat": 27.1795,
        "lon": 78.0211,
        "zoom": 16,
        "delta": 0.0150,
        "sources": [
            "- [S1] UNESCO Agra Fort: https://whc.unesco.org/en/list/251/",
            "- [S2] OpenStreetMap Agra Fort map view: https://www.openstreetmap.org/#map=16/27.1795/78.0211",
        ],
    },
    "fatehpur_sikri": {
        "name": "Fatehpur Sikri",
        "aliases": ("fatehpur sikri",),
        "lat": 27.0945,
        "lon": 77.6679,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Fatehpur Sikri: https://whc.unesco.org/en/list/255/",
            "- [S2] OpenStreetMap Fatehpur Sikri map view: https://www.openstreetmap.org/#map=15/27.0945/77.6679",
        ],
    },
    "ramappa": {
        "name": "Kakatiya Rudreshwara Ramappa Temple",
        "aliases": ("ramappa", "rudreshwara", "kakatiya temple"),
        "lat": 18.2593,
        "lon": 79.9436,
        "zoom": 15,
        "delta": 0.0250,
        "sources": [
            "- [S1] UNESCO Kakatiya Rudreshwara Ramappa Temple: https://whc.unesco.org/en/list/1570/",
            "- [S2] OpenStreetMap Ramappa Temple map view: https://www.openstreetmap.org/#map=15/18.2593/79.9436",
        ],
    },
}


def detect_map_site(question: str) -> str | None:
    text = question.lower()
    for site_id, config in PUBLIC_HERITAGE_MAPS.items():
        if any(alias in text for alias in config["aliases"]):
            return site_id
    return None


def open_url(config: dict) -> str:
    return f"https://www.openstreetmap.org/#map={config['zoom']}/{config['lat']:.4f}/{config['lon']:.4f}"


def embed_url(config: dict) -> str:
    delta = float(config["delta"])
    west = config["lon"] - delta
    south = config["lat"] - delta
    east = config["lon"] + delta
    north = config["lat"] + delta
    return (
        "https://www.openstreetmap.org/export/embed.html?"
        f"bbox={west:.4f}%2C{south:.4f}%2C{east:.4f}%2C{north:.4f}"
        f"&layer=mapnik&marker={config['lat']:.4f}%2C{config['lon']:.4f}"
    )


def answer_map_view(question: str, route: dict) -> tuple[str, list[str]] | None:
    if route.get("answer_mode") != "map_view":
        return None

    site_id = route.get("site") or detect_map_site(question)
    if not site_id:
        return None

    config = PUBLIC_HERITAGE_MAPS.get(site_id)
    if not config:
        return None

    answer = "\n".join(
        [
            f"Here is an interactive public map view for {config['name']}.",
            "",
            f"Open full map: {open_url(config)}",
            "",
            "Map note: this is a public contextual map view for a well-known heritage site. For research-grade archaeology/GIS work, use official layers such as ASI/UNESCO records, Bhuvan/NRSC satellite data, and published site plans.",
            "",
            f"<!--MAP_EMBED_URL:{embed_url(config)}-->",
        ]
    )
    return answer, config["sources"]
