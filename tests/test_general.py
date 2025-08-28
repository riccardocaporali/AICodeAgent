import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.run_python import run_python_file
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs
from functions.llm_calls.get_file_content import get_file_content
from functions.llm_calls.get_files_info import get_files_info

# === INTRODUCTION ===
# This is  a general test to execute of the llm function in sequence, the aim is to see if relative 
# logs, summary, backup and diffs files are created. 

# === CONFIGURATION ===
TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
run_id = init_run_session()

# Paths for ai_outputs
RUN_DIR = os.path.join("__ai_outputs__", run_id)
LOG_PATH = os.path.join(RUN_DIR, "actions.log")
SUMMARY_PATH = os.path.join(RUN_DIR, "summary.txt")

# === SETUP: General file structure created for testing purposes ===

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
# File to be executed by run_python_file
os.makedirs(TEST_DIR, exist_ok=True)
with open(os.path.join(TEST_DIR, "create_hello.py"), "w", encoding="utf-8") as f:
    f.write(code_create)

# General file for llm functions 
with open(os.path.join(TEST_DIR, "hello.txt"), "w", encoding="utf-8") as f:
    f.write("Hello, world!\nThis is a test file.")

# Subfolder with file for get_file_info
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

# Snapshot before
before_log = read_all(LOG_PATH)
before_summary = read_all(SUMMARY_PATH)

# 1) === Test run_python_file ===
res1 = run_python_file(
    working_directory=TEST_DIR,
    file_path="create_hello.py",
    run_id=run_id,
    function_args={"working_directory": TEST_DIR, "file_path": "create_hello.py"},
    log_changes=True
)
print_test_result(1, "run valid file (should log and summary)", res1)
print_logs_and_summary_tail("AFTER TEST 1")

# Snapshot after test 1
after1_log = read_all(LOG_PATH)
after1_summary = read_all(SUMMARY_PATH)

# Verify created file
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
    log_changes=True
)
print_test_result(2, "read valid file (should log and summary)", res2)
print_logs_and_summary_tail("AFTER TEST 2")
# Snapshot after test 2
after2_log = read_tail(LOG_PATH, n=1000)
after2_summary = read_tail(SUMMARY_PATH, n=2000)

# 3) === Test get_file_content ===
res3 = get_files_info(
    working_directory=TEST_DIR,
    run_id=run_id,
    directory="pkg",
    function_args={"working_directory": TEST_DIR, "directory": "pkg"},
    log_changes=True
)
print_test_result(3, "list contents of pkg/", res3)
print_logs_and_summary_tail("AFTER TEST 3")
after3_log = read_tail(LOG_PATH, n=2000)
after3_summary = read_tail(SUMMARY_PATH, n=4000)


# === CHECKS ===
print("\n— CHECK 1: Did Test 1 write something new? —")
print("Logs written:", "YES" if after1_log != before_log else "NO ❌")
print("Summary written:", "YES" if after1_summary != before_summary else "NO ❌")


# Optional clear
if "--clear" in sys.argv:
    clear_output_dirs()