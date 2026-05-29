from __future__ import annotations


HAMPI_TEMPLE_SOURCES = [
    "- [S1] UNESCO Group of Monuments at Hampi: https://whc.unesco.org/en/list/241/",
    "- [S2] ASI Hampi World Heritage Site: https://asi.nic.in/pages/WorldHeritageHampi",
    "- [S3] Karnataka Tourism Hampi: https://karnatakatourism.org/destinations/hampi/",
    "- [S4] Digital Analysis of Mula Virupaksha Temple Hampi: https://www.mdpi.com/2409-9252/2/3/23",
]

HAMPI_TEMPLES = [
    "Virupaksha Temple",
    "Vijaya Vittala / Vitthala Temple",
    "Krishna Temple",
    "Hazara Rama Temple",
    "Achyutaraya / Tiruvengalanatha Temple",
    "Pattabhirama Temple",
    "Malyavanta Raghunatha Temple",
    "Kodandarama Temple",
    "Prasanna Virupaksha / Underground Shiva Temple",
    "Hemakuta hill temple group, including Mula Virupaksha",
    "Chandikesvara Temple",
    "Saraswati Temple",
    "Ganagitti Jain Temple",
    "Badavilinga Temple",
]


def answer_site_list(question: str, route: dict) -> tuple[str, list[str]] | None:
    text = question.lower()
    if route.get("answer_mode") != "site_list":
        return None
    if route.get("site") != "hampi":
        return None
    if "temple" not in text:
        return None

    lines = [
        "Important temples and temple groups at Hampi include:",
    ]
    for index, temple in enumerate(HAMPI_TEMPLES, start=1):
        lines.append(f"{index}. {temple}")

    lines.extend(
        [
            "",
            "Note: Hampi has many shrines and temple remains, so this is a practical working list of well-known temples and temple groups, not a complete archaeological inventory.",
        ]
    )
    return "\n".join(lines), HAMPI_TEMPLE_SOURCES
