import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from functions.internal.get_secure_path import get_secure_path

def get_file_content(working_directory, file_path):
    try:
        # Create the path, check if it is secure and inside an existing directory
        full_path = get_secure_path(working_directory, file_path)
        
        if not os.path.isfile(full_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        # File content extraction
        MAX_CHARS = 10000
        with open(full_path, "r") as f:
            file_content_string = f.read(MAX_CHARS+1)
            if len(file_content_string) == 10001:
                file_content_string = file_content_string[:-1] + f'\n\n[...File "{file_path}" truncated at 10000 characters]'

        return file_content_string 
    
    except Exception as e:
        return "Error: " + str(e)