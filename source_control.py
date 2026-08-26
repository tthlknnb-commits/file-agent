from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceAssessment:
    uri: str
    authority: str
    status: str
    reason: str


OFFICIAL_SUFFIXES = (".gov.vn", ".chinhphu.vn", ".moj.gov.vn", ".quochoi.vn")


def assess_web_source(url: str) -> SourceAssessment:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not host:
        return SourceAssessment(url, "UNKNOWN", "UNVERIFIED", "URL không hợp lệ hoặc thiếu tên miền.")
    if host.endswith(OFFICIAL_SUFFIXES):
        return SourceAssessment(url, "OFFICIAL_GOVERNMENT", "CONFIRMED", "Tên miền thuộc nhóm nguồn cơ quan nhà nước được nhận diện.")
    return SourceAssessment(url, "UNKNOWN", "UNVERIFIED", "Chưa xác định được nguồn chính thống chỉ từ URL; cần kiểm tra trước khi dùng để khẳng định.")


def assess_sources(urls: list[str]) -> list[SourceAssessment]:
    return [assess_web_source(url) for url in urls]
