from pathlib import Path

from file_reader import read_file, read_paths
from file_search import search_evidence


def test_text_reader_preserves_evidence(tmp_path: Path):
    source = tmp_path / "report.txt"
    source.write_text("Kế hoạch: 100\nThực hiện: 80", encoding="utf-8")
    evidence = read_file(source)
    assert len(evidence) == 1
    assert "Thực hiện: 80" in evidence[0].content
    assert evidence[0].status == "USER_SUPPLIED"
    assert evidence[0].sha256


def test_search_returns_source_and_locator(tmp_path: Path):
    source = tmp_path / "six_months.txt"
    source.write_text("Báo cáo 6 tháng\nThực hiện 80 hộ", encoding="utf-8")
    evidence = read_paths([str(tmp_path)])
    hits = search_evidence(evidence, "6 tháng 80 hộ")
    assert hits
    assert hits[0].source_uri.endswith("six_months.txt")
    assert "80 hộ" in hits[0].excerpt


def test_unknown_extension_is_not_read(tmp_path: Path):
    source = tmp_path / "secret.bin"
    source.write_bytes(b"not a supported document")
    assert read_file(source) == []
