import os
import sys

from aicodeagent.functions.llm_calls.run_python import run_python_file
from aicodeagent.functions.internal.reset_test_env import reset_test_env
from aicodeagent.functions.internal.init_run_session import init_run_session
from aicodeagent.functions.internal.clear_output_dirs import clear_output_dirs
from aicodeagent.functions.llm_calls.get_file_content import get_file_content
from aicodeagent.functions.llm_calls.get_files_info import get_files_info
from aicodeagent.functions.llm_calls.propose_changes import propose_changes
from aicodeagent.functions.llm_calls.conclude_edit import conclude_edit

# === INTRODUCTION ===
# This is a general test that executes the LLM functions in sequence.
# The goal is to verify that logs, summaries, backups, and diff files are correctly generated.

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
run_id = init_run_session()

# Paths for ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)
LOG_PATH = os.path.join(RUN_DIR, "actions.log")
SUMMARY_PATH = os.path.join(RUN_DIR, "summary.txt")

# === SETUP: General file structure created for testing ===
# __test_env__/
# ├─ hello.txt
# ├─ create_hello.py
# └─ pkg/
#     └─ module.py

code_create = """\
import os
TEST_DIR = "."
os.makedirs(TEST_DIR, exist_ok=True)
file_path = os.path.join(TEST_DIR, "hello_created.txt")
with open(file_path, "w", encoding="utf-8") as f:
    f.write("Hello, world!\\nThis is a test file.")
"""
content = """\
# Proposed changes to hello.txt
"""

# File executed by run_python_file
os.makedirs(TEST_DIR, exist_ok=True)
with open(os.path.join(TEST_DIR, "create_hello.py"), "w", encoding="utf-8") as f:
    f.write(code_create)

# General test file for LLM functions
with open(os.path.join(TEST_DIR, "hello.txt"), "w", encoding="utf-8") as f:
    f.write("Hello, world!\nThis is a test file.")

# Subfolder with a file for get_files_info
os.makedirs(os.path.join(TEST_DIR, "pkg"), exist_ok=True)
with open(os.path.join(TEST_DIR, "pkg", "module.py"), "w", encoding="utf-8") as f:
    f.write("# module file\n")

# === HELPERS ===
def print_test_result(n, description, result):
    print(f"\n▶️ Test {n}: {description}")
    print(result)

def read_all(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def read_tail(path, n=20):
    if not os.path.isfile(path):
        return "<missing>"
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:]).rstrip()

def print_logs_and_summary_tail(label):
    print(f"\n— {label} | actions.log (tail) —")
    print(read_tail(LOG_PATH, n=40))
    print(f"\n— {label} | summary.txt (tail) —")
    print(read_tail(SUMMARY_PATH, n=80))

print("\n==== LLM FUNCTIONS TESTS ====\n")

# 1) === Test run_python_file ===
res1 = run_python_file(
    working_directory=TEST_DIR,
    file_path="create_hello.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "create_hello.py"},
)
print_test_result(1, "run valid file (should log and summarize)", res1)
print_logs_and_summary_tail("AFTER TEST 1")

# Verify that the file was created
created_file = os.path.join(TEST_DIR, "hello_created.txt")
print("\n— File creation check —")
if os.path.isfile(created_file):
    with open(created_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
    print(f"hello_created.txt found with content:\n{content}")
else:
    print("hello_created.txt was NOT created ❌")

# 2) === Test get_file_content ===
res2 = get_file_content(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
)
print_test_result(2, "read valid file (should log and summarize)", res2)

# 3) === Test get_files_info ===
res3 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="pkg",
    function_args={"working_directory": TEST_DIR, "directory": "pkg"},
)
print_test_result(3, "list contents of pkg/", res3)

# 4) === propose_changes ===
proposed_content = """\
# Proposed changes to hello.txt
"""
res4 = propose_changes(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    content=proposed_content,
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
)
print_test_result(4, "propose_changes on hello.txt", res4)

# 5) === conclude_edit ===
res5 = conclude_edit(
    working_directory=TEST_DIR,
    file_path="hello.txt",
    content=proposed_content,
    dry_run=False,
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "hello.txt"},
)
print_test_result(5, "conclude_edit on hello.txt", res5)

# Optional cleanup
if "--clear" in sys.argv:
    clear_output_dirs()