# tests/unit/test_propose_changes.py
from aicodeagent.functions.llm_calls.propose_changes import propose_changes
from aicodeagent.functions.pipeline.init_run_session import init_run_session
from aicodeagent.tools.create_test_env import create_test_env


def test_propose_changes_existing(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    # existing file
    fp = working / "script.py"
    fp.write_text("v1")

    run_id = init_run_session()

    result = propose_changes(
        working_directory=str(working),
        file_path="script.py",
        content="v2",
        run_id=run_id,
    )

    # the function MUST NOT write to the working directory → content must stay unchanged
    assert fp.read_text() == "v1"

    # the only guaranteed behavior is the returned message
    assert "Save proposed changes" in result
    assert "script.py" in result
    assert "2 characters" in result


def test_propose_changes_new_file(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    run_id = init_run_session()

    result = propose_changes(
        working_directory=str(working),
        file_path="newfile.py",
        content="hello",
        run_id=run_id,
    )

    new_fp = working / "newfile.py"

    # the file MUST NOT be created in the working directory
    assert not new_fp.exists()

    # the only guaranteed behavior is the returned message
    assert "Save proposed creation" in result
    assert "newfile.py" in result
    assert "5 characters" in result
