def test_data_source_priority_defaults():
    import importlib

    config = importlib.import_module("stock_mvp.config")

    cfg = config.Config()
    assert cfg.DATA_SOURCE_PRIORITY
    assert cfg.REALTIME_SOURCE_PRIORITY
