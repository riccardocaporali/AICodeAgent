import os
import sys

from aicodeagent.functions.llm_calls.get_files_info import get_files_info
from aicodeagent.functions.internal.reset_test_env import reset_test_env
from aicodeagent.functions.internal.init_run_session import init_run_session
from aicodeagent.functions.internal.clear_output_dirs import clear_output_dirs

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
run_id = init_run_session()

# Paths ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)

# === SETUP: Create file and subfolder ===
# __test_env__/
# ├─ example.txt
# └─ pkg/
#     └─ module.py
os.makedirs(os.path.join(TEST_DIR, "pkg"), exist_ok=True)

with open(os.path.join(TEST_DIR, "example.txt"), "w", encoding="utf-8") as f:
    f.write("print('hello world')\n")

with open(os.path.join(TEST_DIR, "pkg", "module.py"), "w", encoding="utf-8") as f:
    f.write("# module file\n")

# === HELPERS ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

def read_tail(path, n=40):
    if not os.path.isfile(path):
        return "<missing>"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:]).rstrip()

print("\n==== get_files_info TESTS ====\n")

# 1) SUCCESS: list contents of pkg/
res1 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="pkg",
    function_args={"working_directory": TEST_DIR, "directory": "pkg"},
)
print_test_result(1, "list contents of pkg/", res1)

# 2) SUCCESS: list contents of base test directory
res2 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory=".", 
    function_args={"working_directory": TEST_DIR, "directory": "."},
)
print_test_result(2, "list contents of base test directory", res2)

# 3) ERROR: attempt to access outside of test_env 
res3 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="../main.py",
    function_args={"working_directory": TEST_DIR, "directory": "../main.py"},
)
print_test_result(3, "attempt to escape working directory", res3)

# 4) ERROR: non-existent subdir in test_env 
res4 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="ghost_folder",
    function_args={"working_directory": TEST_DIR, "directory": "ghost_folder"},
)
print_test_result(4, "non-existent folder in test_env", res4)

# Clear ai_outputs se richiesto
if "--clear" in sys.argv:
    clear_output_dirs()