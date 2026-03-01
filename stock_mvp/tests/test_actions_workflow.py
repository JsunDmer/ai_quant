import os


def test_actions_workflow_exists():
    assert os.path.exists(".github/workflows/daily_pipeline.yml")
