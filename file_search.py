from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from file_reader import Evidence, read_paths


@dataclass
class SearchHit:
    source_uri: str
    title: str
    locator: str | None
    score: float
    excerpt: str


def _terms(query: str) -> list[str]:
    return [x for x in re.findall(r"[\wÀ-ỹ]+", query.lower()) if len(x) > 1]


def search_evidence(evidence: list[Evidence], query: str, limit: int = 20) -> list[SearchHit]:
    terms = _terms(query)
    if not terms:
        return []
    hits: list[SearchHit] = []
    for item in evidence:
        text = item.content.lower()
        matched = sum(text.count(term) for term in terms)
        if not matched:
            continue
        score = matched / max(len(terms), 1)
        first = min((text.find(term) for term in terms if text.find(term) >= 0), default=0)
        start = max(0, first - 180)
        excerpt = item.content[start:start + 500].replace("\n", " ").strip()
        hits.append(SearchHit(item.source_uri, item.title, item.locator, score, excerpt))
    return sorted(hits, key=lambda x: x.score, reverse=True)[:limit]


def search_paths(paths: list[str], query: str, limit: int = 20) -> list[SearchHit]:
    return search_evidence(read_paths(paths), query, limit)
