from __future__ import annotations


def answer_knowledge_pack(question: str, route: dict) -> tuple[str, list[str]] | None:
    text = question.lower()
    if route.get("answer_mode") != "rag":
        return None

    if any(term in text for term in ("krishnadevaraya", "krishna deva raya", "sri krishnadevaraya", "shri krishnadevaraya")):
        answer = "\n".join(
            [
                "Shri Krishnadevaraya, also written Krishna Deva Raya, was a major Vijayanagara ruler associated with Hampi and the empire's high point. UNESCO's Hampi record says Hampi was the capital of the Vijayanagara kingdom and reached its apogee under Krishna Deva Raya, with the reign dates 1509-1530 given in the retrieved UNESCO context [S1].",
                "",
                "For archaeology-focused answers, connect him mainly with the Hampi/Vijayanagara royal and sacred landscape rather than treating him as an isolated biographical figure. The project source database also links him to official Hampi monument sources, including ASI's Hampi page and Karnataka Tourism monument pages that mention Krishnadevaraya-related royal buildings and monuments [S2] [S3].",
            ]
        )
        sources = [
            "- [S1] UNESCO Group of Monuments at Hampi: https://whc.unesco.org/en/list/241/",
            "- [S2] ASI Hampi World Heritage Site: https://asi.nic.in/pages/WorldHeritageHampi",
            "- [S3] Karnataka Tourism Lotus Mahal: https://karnatakatourism.org/en/attractions/lotus-mahal",
            "- [S4] Britannica Vijayanagara: https://www.britannica.com/place/Vijayanagara",
        ]
        return answer, sources

    if any(term in text for term in ("vijaya empire", "vijayanagara empire", "vijayanagar empire")):
        answer = "\n".join(
            [
                "The phrase 'Vijaya empire' is best treated as a likely reference to the Vijayanagara or Vijayanagar Empire. Its best-known archaeological capital is Hampi, which UNESCO describes as the last capital of the last great Hindu kingdom of Vijayanagar [S1].",
                "",
                "For a research answer, the agent should connect this topic with Hampi's royal, urban, and sacred remains, ASI/UNESCO monument records, and Vijayanagara Research Project publications rather than relying on generic web summaries [S1] [S2] [S3].",
            ]
        )
        sources = [
            "- [S1] UNESCO Group of Monuments at Hampi: https://whc.unesco.org/en/list/241/",
            "- [S2] ASI Hampi World Heritage Site: https://asi.nic.in/pages/WorldHeritageHampi",
            "- [S3] Vijayanagara Research Project Publications: https://www.penn.museum/research/project.php?pid=15",
            "- [S4] Britannica Vijayanagara: https://www.britannica.com/place/Vijayanagara",
        ]
        return answer, sources

    return None
