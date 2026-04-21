from stock_mvp.pipeline import run_post_close_pipeline


def test_dashboard_report_shape():
    result = run_post_close_pipeline(ai_enabled=False, refresh_realtime_only=True)
    report = result.get("dashboard_report")
    assert report is not None
    assert "headline" in report
    assert "summary" in report
