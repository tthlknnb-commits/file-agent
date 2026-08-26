from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


def search_web(query: str, max_results: int = 5, official_only: bool = False) -> list[SearchResult]:
    """Search the public web without treating search results as authoritative facts.

    Official-source preference is expressed through the query; authority is still
    checked separately by source_control before a result can be treated as confirmed.
    """
    effective_query = f"{query} site:.gov.vn" if official_only else query
    params = urllib.parse.urlencode({"q": effective_query, "kl": "vn-vn"})
    url = f"https://html.duckduckgo.com/html/?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "AI-Admin-Office/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(2_000_000).decode("utf-8", errors="replace")

    results: list[SearchResult] = []
    pattern = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(body):
        raw_url, raw_title, raw_snippet = match.groups()
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query).get("uddg", [raw_url])[0]
        title = re.sub(r"<[^>]+>", "", raw_title)
        snippet = re.sub(r"<[^>]+>", "", raw_snippet)
        results.append(SearchResult(html.unescape(title).strip(), parsed, html.unescape(snippet).strip()))
        if len(results) >= max_results:
            break
    return results
