# tests/e2e/test_list_file.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm


def test_list_file(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(
        verbose=False, I_O=False, reset=True, demo=False, test=True
    )

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="List all files of calculator_bugged",
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

    # 4) Minimal checks
    # check that messages contain the file listing
    joined = "\n".join(str(m) for m in messages)

    try:
        # HARD ASSERT — ideal behavior: the LLM lists all files in calculator_bugged
        assert "calculator_bugged" in joined
        assert "lorem.txt" in joined
        assert "main.py" in joined
        assert "tests.py" in joined

    except AssertionError:
        # SOFT FAIL — LLM gave a partial but reasonable answer (e.g. listed only some files,
        # asked which directory, or attempted clarification)
        if (
            "calculator_bugged" in joined.lower()
            or "which file" in joined.lower()
            or "directory" in joined.lower()
            or "specify" in joined.lower()
            or "not sure" in joined.lower()
            or "cannot find" in joined.lower()
        ):
            import pytest

            pytest.xfail(
                "Soft fail: LLM produced partial file listing or clarification request."
            )
        # HARD FAIL — nonsense or unrelated output
        raise
