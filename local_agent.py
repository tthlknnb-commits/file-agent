from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_admin_office import process
from request_router import route_request

SUPPORTED = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm", ".docx", ".xlsx", ".pdf"}


def inspect_paths(paths: list[str]) -> list[dict]:
    rows = []
    for raw in paths:
        p = Path(raw).expanduser()
        if not p.exists():
            rows.append({"path": raw, "exists": False})
            continue
        files = list(p.rglob("*") if p.is_dir() else [p])
        rows.append({
            "path": str(p),
            "exists": True,
            "kind": "directory" if p.is_dir() else "file",
            "files": [str(f) for f in files if f.is_file() and f.suffix.lower() in SUPPORTED],
        })
    return rows


def run(request: str, paths: list[str] | None = None, output_dir: str | None = None) -> dict:
    routed = route_request(request)
    authorized_paths = list(paths) if paths else routed.local_paths
    result = process(request, local_paths=authorized_paths, output_dir=output_dir or "output")
    return {
        "request": request,
        "authorized_paths": inspect_paths(authorized_paths),
        "routed_web_urls": routed.web_urls,
        "web_research_requested": routed.needs_web_research,
        "result": result.__dict__,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Admin Office local computer bridge")
    parser.add_argument("request")
    parser.add_argument("paths", nargs="*", help="Optional explicitly authorized local files/folders on any drive")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()
    print(json.dumps(run(args.request, args.paths, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
