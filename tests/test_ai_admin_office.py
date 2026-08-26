from ai_admin_office import calculate_completion, classify_product, process


def test_completion_rate():
    assert calculate_completion(100, 80) == 80
    assert calculate_completion(100, 120) == 120


def test_zero_denominator():
    assert calculate_completion(0, 80) is None


def test_explicit_product_is_not_reclassified():
    assert classify_product("viết báo cáo", "PLAN")[0] == "PLAN"


def test_ambiguous_product_blocks():
    product, issues = classify_product("viết báo cáo và quyết định")
    assert product is None
    assert issues[0].code == "AMBIGUOUS_PRODUCT"


def test_unknown_product_blocks():
    product, issues = classify_product("làm một tài liệu")
    assert product is None
    assert issues[0].code == "MISSING_PRODUCT"


def test_process_requires_sources(tmp_path):
    result = process("viết báo cáo", [str(tmp_path)])
    assert result.decision in {"NEEDS_INPUT", "BLOCKED"}
    assert any(i["code"] == "NO_SOURCES" for i in result.issues)
