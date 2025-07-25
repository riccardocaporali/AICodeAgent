import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path

def get_files_info(working_directory, directory=None):
    """
    Lists all files and directories inside the specified target folder.

    - Uses `get_secure_path` to resolve the path securely within the project sandbox.
    - If `directory` is None, defaults to listing the root of the working_directory.
    - Returns file names with their sizes and directory status.
    """

    try:
        # Determine the secure directory path
        target_path = directory if directory else "."
        full_path = get_secure_path(working_directory, target_path)
        
        if not os.path.isdir(full_path):
            return f'Error: "{full_path}" is not a directory'

        # Directory content extraction
        directory_content = os.listdir(full_path)
        file_list = []
        for file in directory_content:
            file_path = os.path.join(full_path, file)
            file_list.append(f"- {file}: file_size={os.path.getsize(file_path)} bytes, is_dir={os.path.isdir(file_path)}")

        return "\n".join(file_list)

    except Exception as e:
        return "Error: " + str(e)