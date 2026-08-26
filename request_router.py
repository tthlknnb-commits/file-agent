from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


WINDOWS_PATH_RE = re.compile(r"(?:(?:[A-Za-z]:[\\/])|(?:\\\\[^\\s]+))(?:[^<>\"|?*\r\n])*", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


@dataclass(frozen=True)
class RoutedRequest:
    request: str
    local_paths: list[str]
    web_urls: list[str]
    needs_web_research: bool
    research_query: str | None


def _clean_path(value: str) -> str:
    return value.rstrip(".,;:)]}")


def route_request(request: str) -> RoutedRequest:
    paths = []
    for match in WINDOWS_PATH_RE.findall(request):
        value = _clean_path(match)
        if value and value not in paths:
            paths.append(value)

    urls = []
    for match in URL_RE.findall(request):
        value = _clean_path(match)
        if urlparse(value).scheme and value not in urls:
            urls.append(value)

    lowered = request.lower()
    research_terms = (
        "internet", "trên mạng", "nguồn chính thống", "thể thức", "mẫu văn bản",
        "quy định hiện hành", "pháp luật", "căn cứ pháp lý", "kiểm tra hiện hành",
        "quy định mới", "văn bản mới nhất",
    )
    needs_research = any(term in lowered for term in research_terms)
    query = request if needs_research else None
    return RoutedRequest(request, paths, urls, needs_research, query)
