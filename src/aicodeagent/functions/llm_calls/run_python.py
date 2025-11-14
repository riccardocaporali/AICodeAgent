import os
import subprocess
import sys

from aicodeagent.functions.core.get_secure_path import get_secure_path
from aicodeagent.functions.core.save_logs import save_logs
from aicodeagent.functions.core.save_summary_entry import save_summary_entry


# --- helpers (module-level) ---
def pack_run_data(stdout, stderr, exit_code):
    return [stdout, stderr, exit_code]


def run_python_file(working_directory, file_path, run_id, function_args=None):
    """
    Securely runs a Python file within the project sandbox.

    - Verifies the file path using `get_secure_path` and ensures it's a `.py` file.
    - Executes the script in a subprocess with a timeout and captures output/errors.
    - Returns stdout, stderr, and exit code.
    """
    # Function name
    function_name = "run_python_file"
    # Define summary directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    # Get the file name
    file_name = "unknown"

    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)
        # Get the file name
        file_name = os.path.basename(full_path)

        if not os.path.isfile(full_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'
        if not full_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file.'

        # Run the file, timeout handling
        try:
            output = subprocess.run(
                [sys.executable, full_path],
                timeout=30,
                capture_output=True,
                text=True,
                cwd=working_directory,
            )

        except subprocess.TimeoutExpired as te:
            stdout = te.stdout or ""
            stderr = te.stderr or ""
            exit_code = "TIMEOUT"
            run_data = {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}

            # Save log
            log_line = save_logs(
                file_name, base_dir, function_name, result="TIMEOUT", details=run_data
            )

            # Save summary
            if log_line:
                save_summary_entry(base_dir, function_name, function_args, log_line)

            return (
                "Error: execution timed out after 30 seconds.\n"
                f"STDOUT:{stdout}\n"
                f"STDERR:{stderr}"
            )

        # Data
        stdout = output.stdout or ""
        stderr = output.stderr or ""
        exit_code = output.returncode
        run_data = {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}

        # Save log
        log_line = save_logs(
            file_name, base_dir, function_name, result="OK", details=run_data
        )

        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        # Output
        if stdout.strip() == "" and stderr.strip() == "":
            return "No output produced."
        return f"STDOUT:{stdout}\nSTDERR:{stderr}\nExit code:{exit_code}"

    except Exception as e:
        details = str(e)
        # Save logs
        log_line = save_logs(
            file_name, base_dir, function_name, result="ERROR", details=details
        )
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)
        return "Error: " + str(e)
