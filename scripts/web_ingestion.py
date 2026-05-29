from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin


TEXT_TAGS = {
    "article",
    "caption",
    "dd",
    "div",
    "dt",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "td",
    "th",
}
SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "iframe", "nav", "footer"}
BOILERPLATE_PATTERNS = (
    "accept cookies",
    "all rights reserved",
    "cookie policy",
    "copyright",
    "follow us",
    "privacy policy",
    "skip to content",
    "terms of use",
)


@dataclass
class WebDocument:
    url: str
    title: str = ""
    description: str = ""
    text: str = ""
    links: list[dict[str, str]] = field(default_factory=list)


class WebPageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self.description = ""
        self.links: list[dict[str, str]] = []
        self._skip_depth = 0
        self._tag_stack: list[str] = []
        self._current_href: str | None = None
        self._current_link_text: list[str] = []
        self._current_text_tag: str | None = None
        self._current_text: list[str] = []
        self._blocks: list[str] = []
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}
        self._tag_stack.append(tag)

        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return

        if tag == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            if name == "description" or prop == "og:description":
                self.description = clean_text(attr_map.get("content", ""))[:500]
            return

        if tag == "a":
            href = attr_map.get("href")
            if href:
                self._current_href = urljoin(self.base_url, href)
                self._current_link_text = []

        if tag == "title":
            self._title_parts = []

        if not self._skip_depth and tag in TEXT_TAGS:
            self._flush_current_text()
            self._current_text_tag = tag
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "title":
            self.title = clean_text(" ".join(self._title_parts))[:250]

        if tag == "a" and self._current_href:
            label = clean_text(" ".join(self._current_link_text))
            self.links.append({"url": self._current_href, "text": label})
            self._current_href = None
            self._current_link_text = []

        if tag == self._current_text_tag:
            self._flush_current_text()

        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return

        if self._tag_stack and self._tag_stack[-1] == "title":
            self._title_parts.append(data)

        if self._current_href:
            self._current_link_text.append(data)

        if self._current_text_tag:
            self._current_text.append(data)

    def _flush_current_text(self) -> None:
        if not self._current_text_tag:
            return
        text = clean_text(" ".join(self._current_text))
        if is_content_block(text):
            prefix = heading_prefix(self._current_text_tag)
            self._blocks.append(f"{prefix}{text}" if prefix else text)
        self._current_text_tag = None
        self._current_text = []

    def document(self) -> WebDocument:
        self._flush_current_text()
        blocks = dedupe_preserve_order(self._blocks)
        text_parts = []
        if self.title:
            text_parts.append(f"Title: {self.title}")
        if self.description:
            text_parts.append(f"Description: {self.description}")
        text_parts.extend(blocks)
        return WebDocument(
            url=self.base_url,
            title=self.title,
            description=self.description,
            text="\n".join(text_parts).strip(),
            links=self.links,
        )


def heading_prefix(tag: str) -> str:
    if tag in {"h1", "h2", "h3"}:
        return f"{tag.upper()}: "
    return ""


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_content_block(text: str) -> bool:
    lowered = text.lower()
    if len(text) < 25:
        return False
    if any(pattern in lowered for pattern in BOILERPLATE_PATTERNS):
        return False
    if len(re.findall(r"[A-Za-z0-9]", text)) < 12:
        return False
    return True


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    output = []
    for item in items:
        key = re.sub(r"\W+", "", item.lower())[:220]
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def parse_web_document(url: str, html: str) -> WebDocument:
    parser = WebPageParser(url)
    parser.feed(html)
    return parser.document()


def extract_pdf_links(document: WebDocument) -> list[dict[str, str]]:
    links = []
    seen = set()
    for link in document.links:
        url = link["url"].split("#", 1)[0]
        if ".pdf" not in url.lower():
            continue
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        links.append({"url": url, "text": link.get("text", "")})
    return links


def extract_relevant_text(
    document: WebDocument,
    terms: set[str],
    required_terms: list[str] | None = None,
    max_chars: int = 4500,
) -> str:
    text = document.text
    if not text:
        return ""

    lowered = text.lower()
    required_terms = [term.lower() for term in (required_terms or [])]
    if required_terms and not any(term in lowered for term in required_terms):
        return ""

    blocks = [block.strip() for block in text.splitlines() if block.strip()]
    scored = []
    for index, block in enumerate(blocks):
        score = score_block(block, terms)
        block_lower = block.lower()
        if required_terms and any(term in block_lower for term in required_terms):
            score += 5
        if block.startswith(("H1:", "H2:", "H3:", "Title:", "Description:")):
            score += 1
        if score > 0:
            scored.append((score, index, block))

    if not scored:
        return text[:max_chars]

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = sorted(scored[:10], key=lambda item: item[1])
    excerpt = "\n".join(block for _, _, block in selected)
    return excerpt[:max_chars]


def score_block(text: str, terms: set[str]) -> int:
    if not terms:
        return 1
    tokens = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    return len(tokens & terms)
