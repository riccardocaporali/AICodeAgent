import os
from dotenv import load_dotenv
from google.genai import types
from google import genai
import sys 
from functions.functions_schemas import schema_get_files_info

# API and client definition
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Define LLM's input arguments
args = sys.argv[1:]
if not args or args[0] == "--verbose" and len(args) == 1:
     print("No prompt provided")
     sys.exit(1)
model = "gemini-2.0-flash-001"
user_prompt = sys.argv[1]
messages = [
    types.Content(role="user", parts=[types.Part(text=user_prompt)]),
]
available_functions = types.Tool(
    function_declarations=[
        schema_get_files_info,
    ]
)
system_prompt = """
You are a helpful AI coding agent.

When a user asks a question or makes a request, make a function call plan. You can perform the following operations:

- List files and directories

All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
"""
config=types.GenerateContentConfig(
    tools=[available_functions], system_instruction=system_prompt
)

# Generate LLM's response
response = client.models.generate_content(
    model = model,
    contents =  messages,
    config = config
)
prompt_token_count = response.usage_metadata.prompt_token_count
candidates_token_count = response.usage_metadata.candidates_token_count

# Print response and specifics
for part in response.candidates[0].content.parts:
    if part.function_call:
        print(f"Calling function: {part.function_call.name}({part.function_call.args})")
    elif part.text:
        print(part.text)
if args[-1] == "--verbose":
    print(f"User prompt: {user_prompt}")
    print(f"Prompt tokens: {prompt_token_count}")
    print(f"Response tokens: {candidates_token_count}")


