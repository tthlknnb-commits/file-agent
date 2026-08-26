from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from document_writer import write_docx, write_text
from file_reader import Evidence, read_paths
from file_search import search_evidence

PRODUCTS = {
    "báo cáo": "REPORT", "bao cao": "REPORT", "report": "REPORT",
    "kế hoạch": "PLAN", "ke hoach": "PLAN", "plan": "PLAN",
    "tờ trình": "PROPOSAL", "to trinh": "PROPOSAL", "proposal": "PROPOSAL",
    "công văn": "OFFICIAL_LETTER", "cong van": "OFFICIAL_LETTER",
    "quyết định": "DECISION", "quyet dinh": "DECISION",
    "thông báo": "NOTICE", "thong bao": "NOTICE",
    "biên bản": "MINUTES", "bien ban": "MINUTES",
    "bài phát biểu": "SPEECH", "bai phat bieu": "SPEECH", "speech": "SPEECH",
    "tham luận": "CONFERENCE", "tham luan": "CONFERENCE",
    "phản biện": "CRITIQUE", "phan bien": "CRITIQUE", "critique": "CRITIQUE",
    "đề cương": "OUTLINE", "de cuong": "OUTLINE", "outline": "OUTLINE",
    "tập huấn": "TRAINING", "tap huan": "TRAINING", "training": "TRAINING",
    "phân tích": "ANALYSIS", "phan tich": "ANALYSIS", "analysis": "ANALYSIS",
}

@dataclass
class Source:
    uri: str
    title: str
    content: str
    source_type: str
    status: str = "UNVERIFIED"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    locator: str | None = None
    sha256: str = ""

@dataclass
class Issue:
    severity: str
    code: str
    message: str
    location: str | None = None
    recommendation: str | None = None

@dataclass
class ProcessResult:
    product_type: str | None
    decision: str
    status: str
    content: str
    sources: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    metadata: dict[str, Any]


def discover_local_sources(paths: list[str], recursive: bool = True) -> list[Source]:
    evidence = read_paths(paths, recursive=recursive)
    return [Source(e.source_uri, e.title, e.content, "LOCAL_FILE", e.status,
                   locator=e.locator, sha256=e.sha256) for e in evidence]


def fetch_web_sources(urls: list[str]) -> list[Source]:
    results: list[Source] = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-Admin-Office/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read(2_000_000)
                content_type = response.headers.get_content_type()
                if content_type.startswith("text/") or content_type in {"application/json", "application/xml"}:
                    content = raw.decode("utf-8", errors="replace")
                    results.append(Source(url, url, content, "WEB", "UNVERIFIED", sha256=hashlib.sha256(content.encode()).hexdigest()))
        except Exception as exc:
            results.append(Source(url, url, f"FETCH_ERROR: {exc}", "WEB", "UNVERIFIED"))
    return results


def classify_product(request: str, explicit_product: str | None = None) -> tuple[str | None, list[Issue]]:
    if explicit_product:
        return explicit_product.upper(), []
    matches = {product for phrase, product in PRODUCTS.items() if phrase in request.lower()}
    if len(matches) == 1:
        return next(iter(matches)), []
    if len(matches) > 1:
        return None, [Issue("CRITICAL", "AMBIGUOUS_PRODUCT", "Có nhiều loại sản phẩm có thể làm thay đổi đầu ra; cần xác nhận.", recommendation="Xác nhận loại sản phẩm cần tạo.")]
    return None, [Issue("CRITICAL", "MISSING_PRODUCT", "Chưa xác định được loại sản phẩm.", recommendation="Nêu rõ sản phẩm cần tạo.")]


def _decision(issues: list[Issue]) -> str:
    if any(i.severity == "CRITICAL" for i in issues):
        return "BLOCKED"
    if any(i.severity == "MAJOR" for i in issues):
        return "NEEDS_INPUT"
    return "PASS"


def _source_rows(sources: list[Source]) -> list[dict[str, Any]]:
    return [{"uri": s.uri, "title": s.title, "type": s.source_type, "status": s.status,
             "locator": s.locator, "retrieved_at": s.retrieved_at,
             "sha256": s.sha256 or hashlib.sha256(s.content.encode()).hexdigest()} for s in sources]


def process(request: str, local_paths: list[str] | None = None, web_urls: list[str] | None = None,
            explicit_product: str | None = None, output_dir: str | None = None,
            search_query: str | None = None, output_format: str = "docx") -> ProcessResult:
    """Controlled workflow: user-authorized sources -> evidence -> product -> QC -> output."""
    issues: list[Issue] = []
    sources = discover_local_sources(local_paths or [])
    sources.extend(fetch_web_sources(web_urls or []))
    product, product_issues = classify_product(request, explicit_product)
    issues.extend(product_issues)
    if not sources:
        issues.append(Issue("MAJOR", "NO_SOURCES", "Chưa tìm thấy tài liệu nguồn trong vị trí đã chỉ định.", recommendation="Kiểm tra đường dẫn hoặc cung cấp nguồn dữ liệu."))
    hits = search_evidence([Evidence(s.uri, s.title, s.source_type, s.locator, s.content, s.sha256, s.status) for s in sources], search_query or request) if sources else []
    if not hits and sources and search_query:
        issues.append(Issue("MINOR", "NO_SEARCH_HITS", "Không tìm thấy đoạn dữ liệu khớp truy vấn; không được tự suy đoán dữ liệu."))
    decision = _decision(issues)
    status = "WORKING" if decision == "PASS" else "REVIEW" if decision == "NEEDS_INPUT" else "DRAFT"
    content = ""
    output_file = None
    if decision != "BLOCKED":
        content = (f"AI ADMIN OFFICE\nSản phẩm: {product}\n\nYêu cầu: {request}\n\n"
                   "Nội dung nguồn được thu thập và kiểm soát theo Evidence Ledger. "
                   "Chưa tự tạo dữ kiện nghiệp vụ chưa có trong nguồn.\n")
        if hits:
            content += "\nDỮ LIỆU THAM CHIẾU:\n" + "\n".join(f"- {h.title} ({h.locator or 'document'}): {h.excerpt}" for h in hits[:10])
        if output_dir:
            out_dir = Path(output_dir)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = out_dir / f"AI_Admin_Office_{stamp}.{output_format.lstrip('.') }"
            if output_format.lower() == "docx":
                write_docx(content, output_file, f"{product or 'AI ADMIN OFFICE'}")
            else:
                write_text(content, output_file)
    metadata = {"workflow": "INPUT→IDENTIFY→INTENT_LOCK→CLASSIFY→SOURCE_DISCOVERY→EVIDENCE_LEDGER→CHECK→PLAN→EXECUTE→INTEGRATE→QC→DECISION→OUTPUT",
                "output_file": str(output_file) if output_file else None,
                "source_count": len(sources), "search_hit_count": len(hits)}
    return ProcessResult(product, decision, status, content, _source_rows(sources), [asdict(i) for i in issues], metadata)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="AI Admin Office local processing engine")
    parser.add_argument("request")
    parser.add_argument("paths", nargs="*", help="Authorized local files/folders; any drive is allowed")
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--product")
    parser.add_argument("--output-dir")
    parser.add_argument("--search")
    parser.add_argument("--format", default="docx")
    args = parser.parse_args()
    result = process(args.request, args.paths, args.url, args.product, args.output_dir, args.search, args.format)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
