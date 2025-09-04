import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from google import genai
from google.genai import types
from functions.llm_calls.get_files_info import get_files_info
from functions.llm_calls.get_file_content import get_file_content
from functions.llm_calls.run_python import run_python_file
from functions.llm_calls.write_file_preview import write_file_preview
from functions.llm_calls.write_file_confirmed import write_file_confirmed

# Define the dictionary of functions
function_dict = {
    "get_files_info" : get_files_info,
    "get_file_content" : get_file_content,
    "run_python_file" : run_python_file,
    "write_file_preview" : write_file_preview,
    "write_file_confirmed" : write_file_confirmed,
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

schema_write_file_preview = types.FunctionDeclaration(
    name="write_file_preview",
    description="Generate a preview of the proposed changes to a file. No actual file is modified. The diff and summary are saved in the __ai_outputs__ directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Path relative to the 'code_to_fix' directory. Use this to specify the subfolder containing the project to analyze (e.g., 'calculator' or 'project_01/module'). If not provided, 'file_path' is considered relative to 'code_to_fix'"
            ),
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the target file, starting from the working directory."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The proposed content to preview in the target file."
            ),
        },
        required=["file_path", "content"]
    )
)

schema_write_file_confirmed = types.FunctionDeclaration(
    name="write_file_confirmed",
    description="Overwrite the target file with the provided content. If the file does not exist, it will be created. This operation applies real changes to the target file. Use only after user confirmation.",
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
        },
        required=["file_path", "content"]
    )
)