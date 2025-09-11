import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.llm_calls.apply_changes import  apply_changes
from functions.internal.reset_test_env import reset_test_env
from functions.internal.init_run_session import init_run_session
from functions.internal.clear_output_dirs import clear_output_dirs

TEST_DIR = "__test_env__"
reset_test_env(TEST_DIR)
# Get the run_ids to create the backup/diffs/logs directory 
run_id = init_run_session()

RUN_DIR = os.path.join("__ai_outputs__", run_id)

print("\n==== write_file TESTS ====\n")

# Setup
working_dir = TEST_DIR
existing_file = "test_script.py"
new_file = "new_generated.py"
outside_path = "../main.py"
content_v1 = f"# First version at {datetime.now()}\n('Test 1: dry run on existing file')\n"
content_v2 = f"# Modified version at {datetime.now()}\n('Test 2: actual write on existing file')\n"
content_v3 = f"# First version at {datetime.now()}\n('Test 3: write to new file')\n"
content_v4 = f"# First version at {datetime.now()}\n('Test 6: verbose mode with function_args')\n"
content_v5 = f"# Modified version at {datetime.now()}\n('Test 7: verbose mode with function_args')\n"

# Create the existing file to be modified in test 1 and 2
with open(os.path.join(working_dir, existing_file), "w") as f:
    f.write(content_v1)

# 1. Dry run on existing file
print("\u25B6\uFE0F Test 1: dry run on existing file")
result_1 = apply_changes(working_dir, existing_file, content_v1, dry_run=True, run_id=run_id )
print(result_1)

# 2. Actual write on existing file
print("\n\u25B6\uFE0F Test 2: actual write on existing file")
result_2 = apply_changes(working_dir, existing_file, content_v2, dry_run=False, run_id=run_id )
print(result_2)

# 3. Write to a new file
print("\n\u25B6\uFE0F Test 3: write to new file")
result_3 = apply_changes(working_dir, new_file, content_v3, dry_run=False, run_id=run_id )
print(result_3)

# 4. Attempt to write outside working directory
print("\n\u25B6\uFE0F Test 4: path escape attempt")
result_4 = apply_changes(working_dir, outside_path, content_v1, run_id=run_id )
print(result_4)

# 5. Attempt to write into a non existing directory
print("\n\u25B6\uFE0F Test 5: Non existing directory")
result_5 = apply_changes("Fake_directory", new_file, content_v1, run_id=run_id )
print(result_5)


# 6. Verbose mode with function_args manually passed, new file creation dry run on
print("\n\u25B6\uFE0F Test 6: verbose mode with function_args")
manual_args = {
    "working_directory": working_dir,
    "file_path": "manual_verbose.py",
    "content": content_v4,
    "run_id": run_id,
    "dry_run": True,
}

result_6 = apply_changes(
    working_directory=manual_args["working_directory"],
    file_path=manual_args["file_path"],
    content=manual_args["content"],
    run_id=manual_args["run_id"],
    dry_run=manual_args["dry_run"],
    function_args=manual_args
)
print(result_6)

# 7. Verbose mode with function_args manually passed, actual creation of new file
print("\n\u25B6\uFE0F Test 7: verbose mode with function_args")
manual_args = {
    "working_directory": working_dir,
    "file_path": "manual_verbose.py",
    "content": content_v5,
    "run_id": run_id,
    "dry_run": False,
}

result_7 = apply_changes(
    working_directory=manual_args["working_directory"],
    file_path=manual_args["file_path"],
    content=manual_args["content"],
    run_id=manual_args["run_id"],
    dry_run=manual_args["dry_run"],
    function_args=manual_args
)
print(result_7)

# Clear ai_ouputs sub directories if clear specified
if "--clear" in sys.argv:
    clear_output_dirs()
