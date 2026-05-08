from backend.pipeline import _select_candidate_sectors


def test_select_candidate_sectors_with_watch_fallback():
    recs = [
        {"sector_name": "电池", "score": 35, "bucket": "watch"},
        {"sector_name": "电机", "score": 34, "bucket": "watch"},
        {"sector_name": "钢铁", "score": 10, "bucket": "hold"},
    ]

    selected = _select_candidate_sectors(recs, limit=2)
    assert selected == ["电池", "电机"]


def test_select_candidate_sectors_strong_priority():
    recs = [
        {"sector_name": "银行", "score": 22, "bucket": "watch"},
        {"sector_name": "贵金属", "score": 45, "bucket": "strong_recommend"},
        {"sector_name": "公路铁路运输", "score": 35, "bucket": "watch"},
    ]

    selected = _select_candidate_sectors(recs, limit=3)
    assert selected[0] == "贵金属"
