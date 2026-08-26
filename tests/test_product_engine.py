from product_engine import PRODUCT_SPECS, ProductEngine


def test_required_product_types_have_specs() -> None:
    required = {
        "REPORT", "PLAN", "PROPOSAL", "OFFICIAL_LETTER", "DECISION", "NOTICE",
        "MINUTES", "SPEECH", "CONFERENCE", "CRITIQUE", "OUTLINE", "TRAINING", "ANALYSIS",
    }
    assert required <= PRODUCT_SPECS.keys()


def test_product_engine_has_full_pipeline() -> None:
    engine = ProductEngine()
    for product in PRODUCT_SPECS:
        assert engine.identify(product).product_type == product
        assert engine.validate(product) == []
        assert engine.plan(product)
        draft = engine.execute(product, "Yêu cầu kiểm thử", [])
        assert engine.integrate(draft, product) == draft


def test_unknown_product_is_rejected() -> None:
    assert ProductEngine().validate("UNKNOWN") == ["UNKNOWN_PRODUCT:UNKNOWN"]
