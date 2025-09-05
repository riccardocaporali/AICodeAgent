import os

def get_secure_path(working_directory, file_name):
    """
    Safely constructs an absolute file path within the given working_directory.

    - Prevents directory traversal (e.g., '..' or absolute paths).
    - Ensures the resolved path stays strictly within the working_directory.
    - Verifies that the target directory already exists (does NOT create it).

    Returns the secure absolute path if all checks pass.
    """

    if ".." in file_name or file_name.startswith("/"):
        raise PermissionError(f"Invalid filename: '{file_name}' contains disallowed characters or path traversal")
    
    path = os.path.abspath(os.path.join(working_directory, file_name))
    working_directory_path = os.path.abspath(working_directory)

    if os.path.isabs(file_name):
        raise PermissionError(f"Invalid filename: '{file_name}' is absolute")

    if os.path.commonpath([working_directory_path, path]) != working_directory_path:
        raise PermissionError(f"Unauthorized path: must stay inside working_directory ({working_directory})")
    
    if not os.path.isdir(os.path.dirname(path)):
        raise FileNotFoundError(f"Directory does not exist: {os.path.dirname(path)}")

    return path