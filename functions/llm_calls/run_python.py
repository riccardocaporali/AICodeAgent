import os, sys
import subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_logs import save_logs

# --- helpers (module-level) ---
def pack_run_data(stdout, stderr, exit_code):
    return [stdout, stderr, exit_code]

def run_python_file(working_directory, file_path, run_id, function_args=None, log_changes=True):
    """
    Securely runs a Python file within the project sandbox.

    - Verifies the file path using `get_secure_path` and ensures it's a `.py` file.
    - Executes the script in a subprocess with a timeout and captures output/errors.
    - Returns stdout, stderr, and exit code.
    """
    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)
        # Define summary directory
        base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
        # Function name
        function_name = "run_python_file"
        # Get the file name 
        file_name = os.path.basename(full_path)

        if not os.path.isfile(full_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'
        if not full_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file.'
    
        # Run the file, timeout handling
        try:
            result = subprocess.run(
                [sys.executable, full_path],
                timeout=30,
                capture_output=True,
                text=True,
                cwd=working_directory
            )
            
        except subprocess.TimeoutExpired as te:
            stdout = te.stdout or ""
            stderr = te.stderr or ""
            exit_code = "TIMEOUT"
            run_data = [stdout, stderr, exit_code]

            # Save log
            if log_changes:
                log_line = save_logs(file_name, base_dir, function_name, extra_data=run_data)

            # Save summary
            if log_changes:
                save_summary_entry(base_dir, function_name, function_args, log_line)

            return (
                "Error: execution timed out after 30 seconds.\n"
                f"STDOUT:{stdout}\n"
                f"STDERR:{stderr}"
            )

        # Data
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode
        run_data = [stdout, stderr, exit_code]

        # Save log
        if log_changes:
            log_line = save_logs(file_name, base_dir, function_name, extra_data=run_data)

        # Save summary
        if log_changes:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        # Output
        if stdout.strip() == "" and stderr.strip() == "":
            return "No output produced."
        return f"STDOUT:{stdout}\nSTDERR:{stderr}\nExit code:{exit_code}"

    except Exception as e:
        return "Error: " + str(e)