import os
import shutil
from pathlib import Path

import pytest


# -------- Global markers registration --------
def pytest_configure(config):
    config.addinivalue_line("markers", "llm: test using real API calls")
    config.addinivalue_line("markers", "integration: integration-level test")
    config.addinivalue_line("markers", "e2e: end-to-end test")
    config.addinivalue_line("markers", "slow: slow-running test")


# -------- Shared fixtures --------
@pytest.fixture
def tmp_run_dir(tmp_path_factory):
    """Create an isolated temporary directory for each test run."""
    d = tmp_path_factory.mktemp("run")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mini_repo(tmp_run_dir):
    """Copy the static mini_repo into the temporary directory."""
    src = Path(__file__).parent / "integration" / "data" / "mini_repo"
    dst = tmp_run_dir / "repo_copy"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def file_llm_client():
    """Return a fake LLM backend that reads from canned responses."""
    from aicodeagent.llm_client import FileLLMClient

    data_dir = Path(__file__).parent / "integration" / "data" / "canned_llm"
    return FileLLMClient(data_dir)


@pytest.fixture
def have_api_key():
    """Return True if a real API key is set."""
    return bool(os.getenv("AICODEAGENT_API_KEY"))
