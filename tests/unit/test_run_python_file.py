# tests/unit/test_run_python_file.py
from aicodeagent.functions.llm_calls.run_python import run_python_file
from aicodeagent.functions.pipeline.init_run_session import init_run_session
from aicodeagent.tools.create_test_env import create_test_env


def test_run_python_success(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "__test_env__"
    working.mkdir(exist_ok=True)

    # create script that writes a file
    script = working / "create_file.py"
    script.write_text(
        "with open('output.txt', 'w', encoding='utf-8') as f:\n    f.write('ok')\n"
    )

    run_id = init_run_session()

    result = run_python_file(
        working_directory=str(working),
        file_path="create_file.py",
        run_id=run_id,
        function_args={
            "working_directory": str(working),
            "file_path": "create_file.py",
        },
    )

    # guaranteed behavior
    assert isinstance(result, str)
    assert "No output produced" in result

    # the file must be created in the working directory
    created = working / "output.txt"
    assert created.exists()
    assert created.read_text() == "ok"


def test_run_python_nonexistent(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "__test_env__"
    working.mkdir(exist_ok=True)

    run_id = init_run_session()

    result = run_python_file(
        working_directory=str(working),
        file_path="missing.py",
        run_id=run_id,
        function_args={"working_directory": str(working), "file_path": "missing.py"},
    )

    # guaranteed behavior
    assert isinstance(result, str)
    assert "error" in result.lower()
    assert "missing.py" in result


def test_run_python_path_traversal(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "__test_env__"
    working.mkdir(exist_ok=True)

    run_id = init_run_session()

    result = run_python_file(
        working_directory=str(working),
        file_path="../evil.py",
        run_id=run_id,
        function_args={"working_directory": str(working), "file_path": "../evil.py"},
    )

    # guaranteed behavior
    assert isinstance(result, str)
    assert "error" in result.lower()


def test_run_python_timeout(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "__test_env__"
    working.mkdir(exist_ok=True)

    # script that sleeps too long
    sleep_script = working / "sleep_long.py"
    sleep_script.write_text("import time\ntime.sleep(40)\n")

    run_id = init_run_session()

    result = run_python_file(
        working_directory=str(working),
        file_path="sleep_long.py",
        run_id=run_id,
        function_args={"working_directory": str(working), "file_path": "sleep_long.py"},
    )

    # guaranteed behavior
    assert isinstance(result, str)
    assert "timeout" in result.lower() or "timed out" in result.lower()
