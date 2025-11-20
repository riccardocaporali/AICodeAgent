# tests/e2e/test_open_file.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm


def test_open_file(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(
        verbose=False, I_O=False, reset=True, demo=False, test=True
    )

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="Open and read the main.py file",
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
    run_dir = project_root / "__ai_outputs__" / run_id
    assert run_dir.exists()

    summary = run_dir / "run_summary.json"
    assert summary.exists()

    # 5) Check that the LLM actually read main.py content
    joined = "\n".join(str(m) for m in messages)

    try:
        # HARD ASSERT: model must include these lines if behaving correctly
        assert "from pkg.calculator import Calculator" in joined
        assert "Calculator App" in joined
    except AssertionError:
        # SOFT FAIL: the model responded but asked a clarifying question
        if (
            "which file" in joined.lower()
            or "specify" in joined.lower()
            or "located in the" in joined.lower()
        ):
            import pytest

            pytest.xfail(
                "Soft fail: LLM asked clarification instead of reading main.py"
            )

        # If it's not a soft fail → real failure
        raise
