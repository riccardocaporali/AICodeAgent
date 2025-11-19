# tests/e2e/test_gating_directory_query.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm

"""Verify the pipeline’s directory-query gating. This test ensures that when the model asks for the project root,
the pipeline intercepts the request, injects the predefined hint ('code_to_fix/'), and then resumes the loop correctly
without errors."""


def test_llm_hello(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(verbose=False, I_O=False, reset=True, demo=False)

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="Where is the project root directory?",
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
        project_root_override=project_root,
    )

    # 4) Check that the LLM actually attempted to run the calculator app

    joined = "\n".join(str(m) for m in messages)

    assert "The project root is 'code_to_fix/'" in joined
    assert "run_python_file" in joined or "get_files_info" in joined
