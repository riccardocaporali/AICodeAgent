import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path
from functions.internal.save_summary_entry import save_summary_entry
from functions.internal.save_logs import save_logs

def get_files_info(working_directory, run_id, directory=None, function_args=None):
    """
    Lists all files and directories inside the specified target folder.

    - Uses `get_secure_path` to resolve the path securely within the project sandbox.
    - If `directory` is None, defaults to listing the root of the working_directory.
    - Returns file names with their sizes and directory status.
    """

    # Function name
    function_name = "get_files_info"
    # Define summary directory
    base_dir = os.path.abspath(os.path.join("__ai_outputs__", run_id))
    # Get the file name 
    file_name = "unknown"

    try:
        # Determine the secure directory path
        target_path = directory if directory else "."
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, target_path)
        # Get the file name 
        file_name = os.path.basename(os.path.normpath(full_path)) or "."
        
        if not os.path.isdir(full_path):
            return f'Error: "{full_path}" is not a directory'

        # Directory content extraction
        directory_content = os.listdir(full_path)
        file_list = []
        for file in directory_content:
            file_path = os.path.join(full_path, file)
            if os.path.isdir(file_path):
                file_list.append(f"- {file}: is_dir=True")
            else:
                file_list.append(f"- {file}: file_size={os.path.getsize(file_path)} bytes, is_dir=False")

        # Save logs
        log_line = save_logs(file_name, base_dir, function_name, list_data=file_list,result="OK")
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        return "\n".join(file_list)

    except Exception as e:
        details = str(e)

        # Save logs
        log_line = save_logs(file_name, base_dir, function_name,result="ERROR",details=details)
        # Save summary
        if log_line:
            save_summary_entry(base_dir, function_name, function_args, log_line)

        return "Error: " + str(e)