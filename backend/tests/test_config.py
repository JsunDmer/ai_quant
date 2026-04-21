import sys
import tempfile
from pathlib import Path


def test_data_source_priority_defaults():
    import importlib

    config = importlib.import_module("backend.config")

    cfg = config.Config()
    assert cfg.DATA_SOURCE_PRIORITY
    assert cfg.REALTIME_SOURCE_PRIORITY


def test_db_path_relative_is_always_under_backend_dir(monkeypatch):
    """相对 DB_PATH 应相对 backend/ 解析，避免 cwd 不同在仓库根再建一份 .db。"""
    import importlib

    isolated = tempfile.mkdtemp()
    monkeypatch.chdir(isolated)
    monkeypatch.setenv("DB_PATH", "custom_pipeline.db")
    sys.modules.pop("backend.config", None)
    cfg_mod = importlib.import_module("backend.config")
    importlib.reload(cfg_mod)
    db_path = Path(cfg_mod.Config().DB_PATH)
    assert db_path.is_absolute()
    assert db_path.name == "custom_pipeline.db"
    assert db_path.parent == Path(cfg_mod.__file__).resolve().parent
