import os


def test_actions_workflow_exists():
    assert os.path.exists(".github/workflows/daily_pipeline.yml")


def test_actions_artifact_block():
    with open(".github/workflows/daily_pipeline.yml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "upload-artifact" in content
