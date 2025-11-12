import json

from aicodeagent.main import run_pipeline


def test_pipeline_no_llm(mini_repo, file_llm_client, tmp_run_dir):
    run_pipeline(input_dir=mini_repo, output_dir=tmp_run_dir, llm=file_llm_client)

    summary = tmp_run_dir / "summary.json"
    diff = tmp_run_dir / "diff.patch"
    backup = tmp_run_dir / "backup"

    assert summary.exists()
    assert diff.exists() and diff.stat().st_size > 0
    assert backup.exists() and any(backup.iterdir())

    data = json.loads(summary.read_text())
    assert "files" in data and isinstance(data["files"], list)
