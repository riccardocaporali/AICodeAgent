# tests/unit/test_conclude_edit.py
from aicodeagent.functions.llm_calls.conclude_edit import conclude_edit
from aicodeagent.functions.pipeline.init_run_session import init_run_session
from aicodeagent.tools.create_test_env import create_test_env


def test_conclude_edit_write_existing(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    file_path = working / "existing.py"
    file_path.write_text("v1")

    run_id = init_run_session()

    result = conclude_edit(
        working_directory=str(working),
        file_path="existing.py",
        content="v2",
        run_id=run_id,
        dry_run=False,
    )

    # must return a success message
    assert "OK" in result or "success" in result.lower()

    # file must be overwritten
    assert file_path.read_text() == "v2"


def test_conclude_edit_write_new(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    run_id = init_run_session()

    result = conclude_edit(
        working_directory=str(working),
        file_path="newfile.py",
        content="hello",
        run_id=run_id,
        dry_run=False,
    )

    new_file = working / "newfile.py"

    # must return a success message
    assert "OK" in result or "success" in result.lower()

    # file must be created
    assert new_file.exists()
    assert new_file.read_text() == "hello"
