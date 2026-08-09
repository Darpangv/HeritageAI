from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from collections import Counter
from pathlib import Path
import csv
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from heritage_agent import tokenize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = PROJECT_ROOT / "data" / "vector_store"
SQLITE_FILE = VECTOR_DIR / "heritage_vectors.sqlite"
LOCAL_DIMENSIONS = 384
TFIDF_MAX_FEATURES = 5000
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
MIN_RERANK_SCORE = 0.03


def stable_hash(text: str) -> int:
    value = 2166136261
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def local_hash_embedding(text: str, dimensions: int = LOCAL_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        index = stable_hash(token) % dimensions
        sign = -1.0 if stable_hash(f"{token}:sign") % 2 else 1.0
        vector[index] += sign

    return normalize(vector)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def sparse_cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


def openai_embedding(text: str) -> tuple[list[float], str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when HERITAGE_EMBEDDING_PROVIDER=openai")

    model = os.environ.get("OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    from openai_compat import openai_endpoint

    request = Request(
        openai_endpoint("embeddings"),
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI embeddings failed with HTTP {error.code}: {body}") from error

    return normalize(result["data"][0]["embedding"]), model


def embed_text(text: str) -> tuple[list[float], str]:
    provider = os.environ.get("HERITAGE_EMBEDDING_PROVIDER", "local").lower()
    if provider == "openai":
        return openai_embedding(text)
    if provider == "hash":
        return local_hash_embedding(text), f"local-hash-{LOCAL_DIMENSIONS}"
    if provider != "local":
        raise RuntimeError("HERITAGE_EMBEDDING_PROVIDER must be 'local', 'hash', or 'openai'")
    return local_hash_embedding(text), f"local-hash-{LOCAL_DIMENSIONS}"


class TfidfVectorizer:
    def __init__(self, vocabulary: dict[str, int], idf: list[float]) -> None:
        self.vocabulary = vocabulary
        self.idf = idf

    @classmethod
    def fit(cls, texts: list[str], max_features: int = TFIDF_MAX_FEATURES) -> "TfidfVectorizer":
        document_frequency: Counter[str] = Counter()
        corpus_frequency: Counter[str] = Counter()
        for text in texts:
            tokens = tokenize(text)
            document_frequency.update(tokens)
            corpus_frequency.update(tokens)

        terms = sorted(
            document_frequency,
            key=lambda term: (document_frequency[term], corpus_frequency[term], len(term)),
            reverse=True,
        )[:max_features]
        vocabulary = {term: index for index, term in enumerate(terms)}
        document_count = max(1, len(texts))
        idf = [
            math.log((1 + document_count) / (1 + document_frequency[term])) + 1
            for term in terms
        ]
        return cls(vocabulary=vocabulary, idf=idf)

    def transform(self, text: str) -> dict[str, float]:
        counts: Counter[int] = Counter()
        for token in tokenize(text):
            index = self.vocabulary.get(token)
            if index is not None:
                counts[index] += 1

        if not counts:
            return {}

        total = sum(counts.values())
        vector = {
            str(index): (count / total) * self.idf[index]
            for index, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in vector.values()))
        if norm == 0:
            return vector
        return {index: value / norm for index, value in vector.items()}

    def to_json(self) -> str:
        return json.dumps({"vocabulary": self.vocabulary, "idf": self.idf})

    @classmethod
    def from_json(cls, raw: str) -> "TfidfVectorizer":
        payload = json.loads(raw)
        return cls(vocabulary=payload["vocabulary"], idf=payload["idf"])


class VectorStore:
    def __init__(self, path: Path = SQLITE_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._source_metadata: dict[str, dict[str, str]] | None = None
        self.initialize()

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                page INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                embedding_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_chunks_url ON chunks(url)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS idx_chunks_title ON chunks(title)")
        self.connection.commit()

    def clear(self) -> None:
        self.connection.execute("DELETE FROM chunks")
        self.connection.execute("DELETE FROM metadata")
        self.connection.commit()

    def set_metadata(self, key: str, value: str) -> None:
        self.connection.execute(
            """
            INSERT INTO metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )

    def get_metadata(self, key: str) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (key,),
        ).fetchone()
        return str(row["value"]) if row else None

    def upsert_chunk(self, record: dict) -> None:
        embedding = record["embedding"]
        self.connection.execute(
            """
            INSERT INTO chunks (
                id, title, source, url, pdf_path, page, chunk_index, text,
                embedding_model, dimensions, embedding_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                source=excluded.source,
                url=excluded.url,
                pdf_path=excluded.pdf_path,
                page=excluded.page,
                chunk_index=excluded.chunk_index,
                text=excluded.text,
                embedding_model=excluded.embedding_model,
                dimensions=excluded.dimensions,
                embedding_json=excluded.embedding_json,
                created_at=excluded.created_at
            """,
            (
                record["id"],
                record["title"],
                record["source"],
                record["url"],
                record["pdf_path"],
                record["page"],
                record["chunk_index"],
                record["text"],
                record["embedding_model"],
                len(embedding),
                json.dumps(embedding),
                int(time.time()),
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"])

    def search(
        self,
        question: str,
        top_k: int = 5,
        candidate_k: int | None = None,
        route: dict | None = None,
    ) -> list[dict]:
        rows = self.connection.execute("SELECT * FROM chunks").fetchall()
        if not rows:
            return []

        first_model = rows[0]["embedding_model"]
        vectorizer_raw = self.get_metadata("tfidf_vectorizer")
        if first_model.startswith("local-tfidf") and vectorizer_raw:
            vectorizer = TfidfVectorizer.from_json(vectorizer_raw)
            question_embedding = vectorizer.transform(question)
            query_model = first_model
            use_sparse = True
        else:
            question_embedding, query_model = embed_text(question)
            use_sparse = False

        results = []
        for row in rows:
            embedding = json.loads(row["embedding_json"])
            if use_sparse:
                score = sparse_cosine_similarity(question_embedding, embedding)
            else:
                if len(embedding) != len(question_embedding):
                    continue
                score = cosine_similarity(question_embedding, embedding)
            if score <= 0:
                continue
            metadata = self.source_metadata(row["url"])
            quality_boost = self.quality_boost(row["url"])
            results.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "source": row["source"],
                    "url": row["url"],
                    "pdf_path": row["pdf_path"],
                    "page": row["page"],
                    "chunk_index": row["chunk_index"],
                    "text": row["text"],
                    "embedding_model": row["embedding_model"],
                    "query_model": query_model,
                    "score": score,
                    "raw_score": score,
                    "quality_boost": quality_boost,
                    "document_category": metadata.get("document_category", ""),
                    "priority": metadata.get("priority", ""),
                    "trust_score": metadata.get("trust_score", ""),
                    "rerank_score": score,
                    "rerank_reason": "semantic only",
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        candidates = results[: candidate_k or max(top_k * 8, 30)]
        reranked = self.rerank(question, candidates, route=route)
        return [result for result in reranked if result["rerank_score"] >= MIN_RERANK_SCORE][:top_k]

    def close(self) -> None:
        self.connection.close()

    def load_source_metadata(self) -> dict[str, dict[str, str]]:
        if self._source_metadata is not None:
            return self._source_metadata

        metadata: dict[str, dict[str, str]] = {}
        csv_file = PROJECT_ROOT / "metadata" / "heritage_links.csv"
        try:
            with csv_file.open(newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    link = row.get("link", "").rstrip("/")
                    if link:
                        metadata[link] = row
        except Exception:
            metadata = {}
        self._source_metadata = metadata
        return metadata

    def source_metadata(self, url: str) -> dict[str, str]:
        metadata = self.load_source_metadata()
        return metadata.get(url.rstrip("/"), {})

    def quality_boost(self, url: str) -> float:
        try:
            row = self.source_metadata(url)
            if row:
                score = int(row.get("trust_score") or 50)
                priority = row.get("priority", "medium")
                usable = row.get("usable_for_rag", "yes")
                if usable == "no" or priority == "exclude":
                    return 0.25
                return 0.75 + (score / 100)
        except Exception:
            pass
        return 1.0

    def query_category_profile(self, question: str, route: dict | None = None) -> dict[str, float]:
        text = question.lower()
        profile = {
            "GIS / Map / Satellite": ("gis", "map", "mapping", "satellite", "remote sensing", "earth observation", "uav", "lidar"),
            "Excavation Report": ("excavation", "trench", "burial", "urn", "stratigraphy", "dig"),
            "Annual Review": ("annual review", "indian archaeology", "a review", "asi review"),
            "Research Paper": ("research", "paper", "study", "analysis", "doi", "journal"),
            "Dataset": ("dataset", "data", "catalog", "csv", "coordinates"),
            "Manuscript / Text": ("manuscript", "text", "inscription", "epigraphy", "script"),
            "Book / Monograph": ("book", "monograph", "volume"),
            "Museum / Collection": ("museum", "collection", "artefact", "artifact"),
            "Monument / Site Record": ("monument", "monuments", "structure", "structures", "site", "temple", "fort", "gateway", "mandapa"),
            "Conservation / Management": ("conservation", "management", "preservation", "world heritage"),
            "Article / Blog": ("blog", "article", "news", "overview"),
        }
        profile_scores = {
            category: 1.0
            for category, terms in profile.items()
            if any(term in text for term in terms)
        }
        for category in (route or {}).get("preferred_categories", []):
            profile_scores[category] = max(1.0, profile_scores.get(category, 0.0))
        return profile_scores

    def keyword_overlap_score(self, question: str, result: dict, route: dict | None = None) -> float:
        query_terms = tokenize(question)
        route_terms = tokenize(" ".join((route or {}).get("boost_terms", [])))
        query_terms = query_terms | route_terms
        if not query_terms:
            return 0.0
        title_terms = tokenize(result.get("title", ""))
        category_terms = tokenize(
            " ".join(
                [
                    result.get("document_category", ""),
                    result.get("source", ""),
                    result.get("url", ""),
                ]
            )
        )
        text_terms = tokenize(result.get("text", "")[:1200])
        title_overlap = len(query_terms & title_terms) / len(query_terms)
        category_overlap = len(query_terms & category_terms) / len(query_terms)
        text_overlap = len(query_terms & text_terms) / len(query_terms)
        return min(1.0, (title_overlap * 0.45) + (category_overlap * 0.25) + (text_overlap * 0.30))

    def rerank(self, question: str, candidates: list[dict], route: dict | None = None) -> list[dict]:
        category_profile = self.query_category_profile(question, route=route)
        preferred_categories = set((route or {}).get("preferred_categories", []))
        per_url_counts: Counter[str] = Counter()
        reranked = []

        for result in candidates:
            semantic = max(0.0, float(result.get("raw_score", 0.0)))
            quality = min(1.0, max(0.0, (float(result.get("quality_boost", 1.0)) - 0.25) / 1.5))
            keyword = self.keyword_overlap_score(question, result, route=route)
            category = result.get("document_category", "")
            category_fit = category_profile.get(category, 0.0)

            url = result.get("url", "")
            diversity_penalty = min(0.15, per_url_counts[url] * 0.05)
            per_url_counts[url] += 1

            relevance_score = semantic * 0.62 + keyword * 0.24 + category_fit * 0.14
            category_mismatch_penalty = 1.0
            if preferred_categories and category not in preferred_categories:
                category_mismatch_penalty = 0.45
                relevance_score *= category_mismatch_penalty
            quality_multiplier = 0.75 + quality * 0.25
            rerank_score = relevance_score * quality_multiplier - diversity_penalty
            result = dict(result)
            result["score"] = min(1.0, max(0.0, rerank_score))
            result["rerank_score"] = result["score"]
            result["rerank_reason"] = (
                f"route={((route or {}).get('intent') or 'general_heritage')}; "
                f"semantic={semantic:.3f}; quality={quality:.3f}; "
                f"keyword={keyword:.3f}; category_fit={category_fit:.3f}; "
                f"category_mismatch_penalty={category_mismatch_penalty:.3f}; "
                f"quality_multiplier={quality_multiplier:.3f}; "
                f"diversity_penalty={diversity_penalty:.3f}"
            )
            reranked.append(result)

        reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return reranked
