# tests/e2e/test_find_bug.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm


def test_llm_hello(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(
        verbose=False, I_O=False, reset=True, demo=False, test=True
    )

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="Analyze the calculator application and find any logical bug.",
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

    assert "get_file_content" in joined
    assert "calculator_bugged" in joined

    # Check if bug is found
    assert "precedence" in joined and ("+" in joined) and ("-" in joined)
    assert (
        "bug" in joined.lower()
        or "wrong" in joined.lower()
        or "incorrect" in joined.lower()
        or "error" in joined.lower()
        or "fix" in joined.lower()
        or "issue" in joined.lower()
        or "problem" in joined.lower()
    )
