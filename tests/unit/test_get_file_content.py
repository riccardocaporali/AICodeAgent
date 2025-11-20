# tests/unit/test_get_file_content.py
from aicodeagent.functions.llm_calls.get_file_content import get_file_content
from aicodeagent.functions.pipeline.init_run_session import init_run_session
from aicodeagent.tools.create_test_env import create_test_env


def test_get_file_content_valid(tmp_path):
    project_root = create_test_env(tmp_path)
    working = project_root / "code_to_fix"

    # create test file
    f = working / "hello.txt"
    f.write_text("Hello, world!\nThis is a test file.")

    run_id = init_run_session()

    raw = get_file_content(
        working_directory=str(working),
        file_path="hello.txt",
        run_id=run_id,
        function_args={
            "working_directory": str(working),
            "file_path": "hello.txt",
        },
    )

    assert isinstance(raw, str)
    assert "Hello, world!" in raw
    assert "This is a test file." in raw
