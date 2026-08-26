from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_admin_office import discover_local_sources, process

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


def run(request: str, paths: list[str], output_dir: str | None = None) -> dict:
    result = process(request, local_paths=paths, output_dir=output_dir)
    return {
        "request": request,
        "authorized_paths": inspect_paths(paths),
        "result": result.__dict__,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Admin Office local computer bridge")
    parser.add_argument("request")
    parser.add_argument("paths", nargs="+", help="Explicitly authorized files/folders on any drive")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    print(json.dumps(run(args.request, args.paths, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
