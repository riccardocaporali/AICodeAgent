import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.get_files_info import get_files_info
from functions.internal.reset_test_env import reset_test_env

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)

# === SETUP: crea dei file e sottocartelle dummy ===
# __test_env__/
# ├─ example.txt
# └─ pkg/
#     └─ module.py

os.makedirs(os.path.join(TEST_DIR, "pkg"), exist_ok=True)

with open(os.path.join(TEST_DIR, "example.txt"), "w") as f:
    f.write("print('hello world')\n")

with open(os.path.join(TEST_DIR, "pkg", "module.py"), "w") as f:
    f.write("# module file\n")

# === HELPER ===
def print_test_result(n, description, result):
    print(f"\nTest {n}: {description}")
    print(result)

# === TESTS ===

print("\n==== get_files_info TESTS ====\n")

# 1. Normal run on subfolder
res1 = get_files_info(TEST_DIR, "pkg")
print_test_result(1, "list contents of pkg/", res1)

# 2. Normal run on base directory
res2 = get_files_info(TEST_DIR)
print_test_result(2, "list contents of base test directory", res2)

# 3. Error: attempt to access outside of test_env
res3 = get_files_info(TEST_DIR, "../main.py")
print_test_result(3, "attempt to escape working directory", res3)

# 4. Error: non-existent file inside test_env
res4 = get_files_info(TEST_DIR, "ghost_file.py")
print_test_result(4, "non-existent file in test_env", res4)
