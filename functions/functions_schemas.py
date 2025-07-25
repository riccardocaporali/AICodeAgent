from google import genai
from google.genai import types
from functions.llm_calls.get_files_info import get_files_info
from functions.llm_calls.get_file_content import get_file_content
from functions.llm_calls.run_python import run_python_file
from functions.llm_calls.write_file import write_file

# Define the dictionary of functions
function_dict = {
    "get_files_info" : get_files_info,
    "get_file_content" : get_file_content,
    "run_python_file" : run_python_file,
    "write_file" : write_file,
}

schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description= "The directory to list files from, relative to the 'code_to_fix' directory. Use None or omit the field to list the root of 'code_to_fix'."
            ),
        },
    ),
)

schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description="Return a string representing the content of the input file.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'."
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory.",
            ),
        },
        required=["file_path"]
    ),
)

schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="Run a Python file and return its output, errors, and exit code.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'."
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory.",
            ),
        },
        required=["file_path"]
    ),
)

schema_write_file = types.FunctionDeclaration(
    name="write_file",
    description="Overwrite the target file with the provided content. If the file does not exist, it will be created. Supports dry-run, logging, and run tracking.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'."
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The content to write into the target file."
            ),
            "dry_run": types.Schema(
                type=types.Type.BOOLEAN,
                description="If true, no actual file will be written — only diff and log will be created."
            ),
            "log_changes": types.Schema(
                type=types.Type.BOOLEAN,
                description="If true, the change will be logged and added to the summary file."
            ),
        },
        required=["file_path", "content"]
    )
)