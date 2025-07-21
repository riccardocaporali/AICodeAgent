import os
import subprocess

def run_python_file(working_directory, file_path):
    try:
        full_path = os.path.abspath(os.path.join(working_directory, file_path))
        directory_path = os.path.abspath(working_directory)

        # Eedge cases handling
        if not full_path.startswith(os.path.abspath(directory_path)):
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(full_path):
            return f'Error: File "{file_path}" not found.'
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