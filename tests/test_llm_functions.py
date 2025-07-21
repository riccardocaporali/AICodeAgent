import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.run_python import run_python_file
from functions.llm_calls.get_files_info import  get_files_info

# Manual test get_file_info

normal_run_1 = get_files_info("calculator", "pkg")
normal_run_2 = get_files_info("calculator")
error_run_1 = get_files_info("calculator", "../main.py")
error_run_2 = get_files_info("calculator", "nonexistent.py")

print(normal_run_1)
print(normal_run_2)
print(error_run_1)
print(error_run_2)


