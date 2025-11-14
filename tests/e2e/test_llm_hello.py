# tests/e2e/test_llm_basic.py
import os

import pytest

pytestmark = pytest.mark.llm

if "GEMINI_API_KEY" not in os.environ:
    pytest.skip("Missing GEMINI_API_KEY", allow_module_level=True)


def test_llm_hello():
    # qui dopo chiameremo la pipeline reale
    assert True
