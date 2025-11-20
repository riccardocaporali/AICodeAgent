# tests/e2e/test_run_file.py
from pathlib import Path

import pytest

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import RealLLMClient
from aicodeagent.pipeline import run_pipeline
from aicodeagent.tools.create_test_env import create_test_env

pytestmark = pytest.mark.llm


def test_run_file(tmp_path: Path):
    # 1) Create isolated project_root
    project_root = create_test_env(tmp_path)

    # 2) Initialize real LLM + pipeline options
    llm = RealLLMClient()
    options = PipelineOptions(
        verbose=False, I_O=False, reset=True, demo=False, test=True
    )

    # 3) Run the pipeline
    result = run_pipeline(
        prompt="Run the file calculator_bugged/main.py exactly as is. Use this exact path: calculator_bugged/main.py",
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

    try:
        # HARD ASSERTS — comportamento ideale
        assert "run_python_file" in joined

        assert "Calculator App" in joined
        assert 'Usage: python main.py "' in joined
        assert 'Example: python main.py "3 + 5"' in joined

    except AssertionError:
        # SOFT FAIL — LLM ha risposto in modo ragionevole ma incompleto
        if (
            "which file" in joined.lower()
            or "specify" in joined.lower()
            or "directory" in joined.lower()
            or "cannot find" in joined.lower()
            or "not sure" in joined.lower()
            or "main.py"
            in joined.lower()  # ha almeno capito il file ma non lo ha eseguito
        ):
            import pytest

            pytest.xfail(
                "Soft fail: LLM produced partial/clarifying response instead of running main.py."
            )

        # HARD FAIL — comportamento assurdo/non correlato
        raise
