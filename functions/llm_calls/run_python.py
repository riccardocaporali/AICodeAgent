import os, sys
import subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path

def run_python_file(working_directory, file_path):
    """
    Securely runs a Python file within the project sandbox.

    - Verifies the file path using `get_secure_path` and ensures it's a `.py` file.
    - Executes the script in a subprocess with a timeout and captures output/errors.
    - Returns stdout, stderr, and exit code.
    """
    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)
        if not os.path.isfile(full_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'
        if not full_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file.'
    
        # Run the file
        result = subprocess.run(["python3", full_path], timeout = 30, capture_output=True, text=True, cwd=working_directory)
        if result.stdout.strip() == "" and result.stderr.strip() == "":
            return "No output produced."
        output = f"STDOUT:{result.stdout}"
        output_error = f"STDERR:{result.stderr}"
        return f"{output}\n{output_error}\nExit code:{result.returncode}"

    except Exception as e:
        return f"Error: executing Python file: {e}"