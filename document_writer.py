from __future__ import annotations

from pathlib import Path
from typing import Any


def write_text(content: str, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_docx(content: str, output: str | Path, title: str | None = None) -> Path:
    from docx import Document
    from docx.shared import Pt

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    if title:
        document.add_heading(title, level=1)
    for block in content.split("\n\n"):
        if block.strip():
            document.add_paragraph(block.strip())
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(13)
    document.save(path)
    return path


def write_csv(rows: list[dict[str, Any]], output: str | Path) -> Path:
    import csv

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return path
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
