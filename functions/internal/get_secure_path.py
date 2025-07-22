import os

def get_secure_path(working_directory, file_name):
    if ".." in file_name or file_name.startswith("/"):
        raise PermissionError("Invalid filename")
    
    path = os.path.abspath(os.path.join(working_directory, file_name))
    
    if os.path.commonpath([working_directory, path]) != working_directory:
        raise PermissionError("Unauthorized path: must stay inside __ai_outputs__")
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path