import os

def get_file_content(working_directory, file_path):
    try:
        full_path = os.path.abspath(os.path.join(working_directory, file_path))
        directory_path = os.path.abspath(working_directory)

        # Eedge cases handling
        if not full_path.startswith(os.path.abspath(directory_path)):
            return f'Error: Cannot read "{file_path}" as it is outside the permitted working directory'
        if not os.path.isfile(full_path):
            return f'Error: File not found or is not a regular file: "{file_path}"'

        # File content extraction
        MAX_CHARS = 10000
        with open(full_path, "r") as f:
            file_content_string = f.read(MAX_CHARS+1)
            if len(file_content_string) == 10001:
                file_content_string = file_content_string[:-1] + f'[...File "{file_path}" truncated at 10000 characters]'

        return file_content_string 
    
    except Exception as e:
        return "Error: " + str(e)