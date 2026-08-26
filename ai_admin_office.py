from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm"}

@dataclass
class Source:
    uri: str
    title: str
    content: str
    source_type: str
    status: str = "UNVERIFIED"
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return ""


def discover_local_sources(paths: list[str], recursive: bool = True) -> list[Source]:
    """Read user-authorized files from any explicitly supplied drive/folder."""
    results: list[Source] = []
    for raw in paths:
        p = Path(raw).expanduser()
        if not p.exists():
            continue
        files = p.rglob("*") if p.is_dir() and recursive else [p]
        for file in files:
            if not file.is_file() or file.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            text = _read_text(file)
            if text:
                results.append(Source(str(file), file.name, text, "LOCAL_FILE", "USER_SUPPLIED"))
    return results


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
                    results.append(Source(url, url, content, "WEB", "UNVERIFIED"))
        except Exception as exc:
            results.append(Source(url, url, f"FETCH_ERROR: {exc}", "WEB", "UNVERIFIED"))
    return results


def classify_product(request: str, explicit_product: str | None = None) -> tuple[str | None, list[Issue]]:
    if explicit_product:
        return explicit_product.upper(), []
    normalized = request.lower()
    matches = {product for phrase, product in PRODUCTS.items() if phrase in normalized}
    if len(matches) == 1:
        return next(iter(matches)), []
    if len(matches) > 1:
        return None, [Issue("CRITICAL", "AMBIGUOUS_PRODUCT", "Yêu cầu chứa nhiều loại sản phẩm có thể làm thay đổi đầu ra; cần xác nhận.", recommendation="Xác nhận loại sản phẩm cần tạo.")]
    return None, [Issue("CRITICAL", "MISSING_PRODUCT", "Chưa xác định được loại sản phẩm.", recommendation="Nêu rõ báo cáo, kế hoạch, tờ trình, quyết định, công văn... cần tạo.")]


def find_current_values(sources: list[Source]) -> dict[str, str]:
    """Lightweight ledger extraction. It never overwrites source text."""
    values: dict[str, str] = {}
    pattern = re.compile(r"(?P<key>[\wÀ-ỹ /.-]{2,60})\s*[:=]\s*(?P<value>[-+\d.,]+\s*[\w%À-ỹ/.-]*)")
    for source in sources:
        for match in pattern.finditer(source.content):
            values[match.group("key").strip()] = match.group("value").strip()
    return values


def calculate_completion(plan: float, actual: float) -> float | None:
    if plan == 0:
        return None
    return actual / plan * 100


def _decision(issues: list[Issue]) -> str:
    if any(i.severity == "CRITICAL" for i in issues):
        return "BLOCKED"
    if any(i.severity == "MAJOR" for i in issues):
        return "NEEDS_INPUT"
    return "PASS"


def process(request: str, local_paths: list[str] | None = None, web_urls: list[str] | None = None,
            explicit_product: str | None = None, output_dir: str | None = None) -> ProcessResult:
    """End-to-end local processing entry point.

    This layer performs source discovery, intent/product control and QC. A language-model
    writer can be plugged into the execution stage without weakening provenance controls.
    """
    issues: list[Issue] = []
    sources = discover_local_sources(local_paths or [])
    sources.extend(fetch_web_sources(web_urls or []))
    product, product_issues = classify_product(request, explicit_product)
    issues.extend(product_issues)
    if not sources:
        issues.append(Issue("MAJOR", "NO_SOURCES", "Chưa tìm thấy tài liệu nguồn trong các vị trí được chỉ định.", recommendation="Kiểm tra lại đường dẫn hoặc cung cấp nguồn dữ liệu."))
    decision = _decision(issues)
    status = "WORKING" if decision == "PASS" else "REVIEW" if decision == "NEEDS_INPUT" else "DRAFT"
    content = ""
    if decision != "BLOCKED":
        content = (
            f"AI ADMIN OFFICE\nSản phẩm: {product}\n\n"
            "Đây là khung xử lý đã kiểm soát nguồn. Phần soạn thảo ngôn ngữ cần được thực hiện bởi writer/model được cấu hình.\n"
            f"Yêu cầu: {request}\n"
        )
    if output_dir and content:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path(output_dir) / f"AI_Admin_Office_{stamp}.txt"
        out.write_text(content, encoding="utf-8")
    source_rows = [{"uri": s.uri, "title": s.title, "type": s.source_type, "status": s.status, "retrieved_at": s.retrieved_at,
                    "sha256": hashlib.sha256(s.content.encode()).hexdigest()} for s in sources]
    return ProcessResult(product, decision, status, content, source_rows, [asdict(i) for i in issues],
                         {"workflow": "INPUT→IDENTIFY→INTENT_LOCK→CLASSIFY→SOURCE_DISCOVERY→CHECK→PLAN→EXECUTE→INTEGRATE→QC→DECISION→OUTPUT"})


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="AI Admin Office local processing engine")
    parser.add_argument("request")
    parser.add_argument("paths", nargs="*", help="Authorized local files/folders; any drive is allowed")
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--product")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = process(args.request, args.paths, args.url, args.product, args.output_dir)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
