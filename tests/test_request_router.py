from request_router import route_request


def test_routes_explicit_windows_paths_on_any_drive() -> None:
    routed = route_request(r"Viết báo cáo 6 tháng, lấy dữ liệu ở D:\BaoCao\2026 và E:\HoSo")
    assert routed.local_paths == [r"D:\BaoCao\2026", r"E:\HoSo"]
    assert not routed.needs_web_research


def test_routes_url_and_web_research_intent() -> None:
    routed = route_request("Viết quyết định theo quy định hiện hành https://example.gov.vn/mau")
    assert routed.web_urls == ["https://example.gov.vn/mau"]
    assert routed.needs_web_research
    assert routed.research_query
