# tests/e2e/test_llm_hello.py
import shutil
from pathlib import Path


def create_test_env(tmp_path: Path):
    # 1) Create project_root isolated
    project_root = tmp_path / "env"
    project_root.mkdir()

    # 2) Copy code_to_fix in minirepo
    src = Path("examples/minirepo/code_to_fix")
    dst = project_root / "code_to_fix"
    shutil.copytree(src, dst)
    return project_root
