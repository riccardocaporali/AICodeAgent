from aicodeagent.functions.llm_calls.get_files_info import get_files_info
from aicodeagent.functions.pipeline.init_run_session import init_run_session
from aicodeagent.tools.create_test_env import create_test_env


def test_list_pkg(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    # create pkg folder inside code_to_fix
    pkg = working / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text("# module")

    run_id = init_run_session()

    raw = get_files_info(
        working_directory=str(working),
        run_id=run_id,
        directory="pkg",
        function_args={
            "working_directory": str(working),
            "directory": "pkg",
        },
    )

    assert isinstance(raw, str)
    assert "module.py" in raw
    assert "is_dir" in raw
    assert "file_size=" in raw
