# tests/e2e/test_seach+run_file.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm


def test_seach_run_file(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(
        verbose=False, I_O=False, reset=True, demo=False, test=True
    )

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="Try to run the calculator application.",
        llm=llm,
        options=options,
        project_root=project_root,
    )

    messages = result["messages"]
    run_id = result["run_id"]
    proposed_content = result["proposed_content"]
    extra_data = result["extra_data"]
    save_run_info(
        messages,
        run_id,
        proposed_content,
        extra_data,
        output_root=project_root,
    )

    # 4) Check that the LLM actually attempted to run the calculator app

    joined = "\n".join(str(m) for m in messages)

    # Must discover and inspect files
    assert "get_files_info" in joined
    assert "get_file_content" in joined

    # Must run the script
    assert "run_python_file" in joined

    # Output of the script
    assert "Calculator App" in joined
    assert "Usage: python main.py" in joined

    try:
        assert "get_files_info" in joined
    except AssertionError:
        # Soft fail se Gemini non ha risposto per rate limit
        if "Request per minute limit exceeded" in joined:
            pytest.xfail("Soft fail: LLM rate-limited during test.")
        raise
