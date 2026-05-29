from __future__ import annotations


HAMPI_MAP = {
    "name": "Hampi World Heritage Area",
    "center": "15.3350, 76.4600",
    "open_url": "https://www.openstreetmap.org/#map=14/15.3350/76.4600",
    "embed_url": "https://www.openstreetmap.org/export/embed.html?bbox=76.4200%2C15.3000%2C76.5000%2C15.3700&layer=mapnik&marker=15.3350%2C76.4600",
    "sources": [
        "- [S1] UNESCO Group of Monuments at Hampi: https://whc.unesco.org/en/list/241/",
        "- [S2] OpenStreetMap Hampi map view: https://www.openstreetmap.org/#map=14/15.3350/76.4600",
        "- [S3] Karnataka Tourism Hampi: https://karnatakatourism.org/destinations/hampi/",
        "- [S4] Bhuvan Indian Geo-Platform: https://bhuvan.nrsc.gov.in/",
    ],
}


def answer_map_view(question: str, route: dict) -> tuple[str, list[str]] | None:
    if route.get("answer_mode") != "map_view":
        return None
    if route.get("site") != "hampi":
        return None

    answer = "\n".join(
        [
            f"Here is an interactive map view for {HAMPI_MAP['name']}.",
            "",
            f"Open full map: {HAMPI_MAP['open_url']}",
            "",
            "Map note: this is a public contextual map view for the well-known Hampi World Heritage area. For research-grade archaeology/GIS work, use official layers such as ASI/UNESCO records, Bhuvan/NRSC satellite data, and published site plans.",
            "",
            f"<!--MAP_EMBED_URL:{HAMPI_MAP['embed_url']}-->",
        ]
    )
    return answer, HAMPI_MAP["sources"]
