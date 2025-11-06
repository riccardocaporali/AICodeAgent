# ---- IMPORTS & INTERNALS -----------------------------------------------------
import os
import argparse
import sys
import re
import json
import time
import shutil
from dotenv import load_dotenv
from google.genai import types
from google import genai
from functions import functions_schemas as schemas
from functions.functions_schemas import function_dict
from functions.call_function import call_function
from functions.internal.init_run_session import init_run_session
from functions.internal.save_run_info import save_run_info
from functions.internal.prev_proposal import prev_proposal
from functions.internal.prev_run_summary_path import prev_run_summary_path
from functions.internal.get_project_root import get_project_root

# ---- USEFUL FUNCTIONS ------------------------------------------------------
def _emit(_name, kind, reason, steps):
    payload = {"ok": False, "type": kind, "reason": reason, "next_steps": steps}
    if args.I_O:
        print(f"-> {_name} denied: {payload['reason']}")
    function_response_list.append(
        types.Part.from_function_response(name=_name, response=payload)
    )

# ---- ENV & CLIENT SETUP ------------------------------------------------------
# - Load environment variables from .env
# - Validate GEMINI_API_KEY (fail fast, write to stderr) and init GenAI client
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Missing GEMINI_API_KEY in environment. Aborting.", file=sys.stderr)
    sys.exit(1)
client = genai.Client(api_key=api_key)

# ---- CLI ARGS PARSING --------------------------------------------------------
# - CLI parser for user prompt and debug flags
parser = argparse.ArgumentParser(
    description="LLM code analyzer and debugger",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument(
    "prompt",
    nargs="?",
    help="Prompt to send to the model"
)

parser.add_argument(
    "--verbose",
    action="store_true",
    help="Print extra diagnostics"
)

parser.add_argument(
    "--I_O",
    action="store_true",
    help="Print messages (LLM input) and function response args (LLM output)"
)

parser.add_argument(
    "--reset",
    action="store_true",
    help="Reset the previous run summary"
)

args = parser.parse_args()

# Validate user input (stderr + non-zero exit code)
if not args.prompt:
    print("No prompt provided", file=sys.stderr)
    sys.exit(1)

# ---- RUN SESSION INIT --------------------------------------------------------
# - Create run_id only after validating arguments (avoid empty/garbage runs)
run_id = init_run_session()

# ---- MODEL & USER PROMPT -----------------------------------------------------
user_prompt = args.prompt

# ---- PREVIOUS RUN CONTEXT BOOTSTRAP -----------------------------------------
prev_summary_path = prev_run_summary_path(run_id)
messages = []
last_prop = None
# Variable to save data fed at conclude_edit
extra_data =None

if prev_summary_path and not args.reset:
    prev_context, last_prop = prev_proposal(prev_summary_path)  # last_prop: file_path, content, run_id, wd

    if prev_context:
        messages.append(types.Content(role="user", parts=[types.Part(text=prev_context)]))

messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

# ---- TOOL DECLARATIONS (FUNCTION SCHEMAS) ------------------------------------
# - Register available tools for the model: list/read/run/propose/apply
has_prev_proposal = bool(last_prop)

fn_decls = [
    schemas.schema_get_files_info,
    schemas.schema_get_file_content,
    schemas.schema_run_python_file,
    schemas.schema_propose_changes,
]
# Register conclude_edit only if previous proposal is present
if has_prev_proposal:
    fn_decls.append(schemas.schema_conclude_edit)

available_functions = types.Tool(function_declarations=fn_decls)

# ---- GUARDS & TRACKERS INIT -------------------------------              
proposed_content = None

run_save = {
    "save_type": "Default",
}

run_stats = {
    "tool_calls": 0,
    "text_only": False,
    "propose_ok": 0,
    "apply_ok": 0,
    "file_info_blox": 0,
    "read_ok": 0,
    "transient_err": 0,
}

# ---- SYSTEM PROMPT & MODEL CONFIG -------------------------------------------
# - Define model id, system instruction, and tool config
model = "gemini-2.0-flash-001"

system_prompt = """
You are an AI agent for refactoring and debugging code.

## Core tools
You can call:
- get_files_info → list files
- get_file_content → read files
- run_python_file → execute files
- propose_changes → preview edits (non-destructive). Saves the full proposed content into PREV_RUN_JSON.

### RESTRICTED TOOL — USE ONLY IN THE SPECIFIC CASE
- conclude_edit → apply the last approved proposal from PREV_RUN_JSON. Call with NO arguments.
  - AVAILABLE ONLY IF there is an approved proposal stored in PREV_RUN_JSON from a previous run.
  - NEVER in the same run where you called propose_changes.
  - NEVER without explicit user intent to apply.
  - NON-CREATIVE. Takes NO arguments.

All paths are inside 'code_to_fix/'. Do NOT include that prefix.

## Behavior rules
1) Read-only tasks (analyze, inspect, review, find bugs)
   - Use ONLY get_files_info, get_file_content, and run_python_file.
   - NEVER ask the user for the file list, file names, or directory structure.
   - ALWAYS use get_files_info to discover files and directories automatically.
   - NEVER call propose_changes or conclude_edit unless the user explicitly requests a modification.

2) Proposing edits
   - Use propose_changes only when you have a specific fix for a single file.
   - Exactly ONE proposal per run. After a successful proposal, STOP and wait for the next run.
   - Keep diffs minimal and limited to the target file.
   - If you used propose_changes in this run, you MUST NOT call conclude_edit. STOP.

3) Applying edits
   - conclude_edit is NON-CREATIVE and takes NO arguments.
   - It is AVAILABLE ONLY IF a valid, approved proposal exists in PREV_RUN_JSON from a previous run.
   - NEVER call conclude_edit in the same run where you made a proposal. NEVER.
   - NEVER call conclude_edit unless the user has asked to apply. NEVER.
   - If no valid proposal exists, do NOT fabricate anything. Return a short explanation.

4) Error handling
   - If a tool fails due to missing proposal, respond with a short textual message explaining what is needed.
   - Do NOT attempt multiple propose_changes or conclude_edit in one run.

5) Scope & clarity
   - Edit only files directly relevant to the user request.
   - If the target file is unclear, ask ONE brief clarifying question, then STOP.

6) Output
   - Provide concise summaries of findings or proposed fixes.
   - Avoid printing long code blocks unless necessary.

Default language = user’s last message.
"""

config = types.GenerateContentConfig(
    tools=[available_functions],
    system_instruction=system_prompt
)

# ---- MAIN LOOP (ITERATIVE DRIVER) -------------------------------------------
cycle_number = 0
while cycle_number <= 15:   # runs up to 16 iters (0..15)
    cycle_number += 1
    try:
        # ---- MODEL CALL & OPTIONAL DEBUG DUMP --------------------------------
        print(f"--------------- Iteration #{cycle_number} ----------------")
        if args.I_O:
            print("\n--- LAST MESSAGES ---")
            for m in messages[-3:]:
                print(f"[{m.role}] →", end=" ")
                for part in m.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text)
                    elif hasattr(part, "function_call") and part.function_call:
                        print(f"[FunctionCall] {part.function_call.name} {part.function_call.args}")
                    else:
                        print(part)

        response = client.models.generate_content(
            model=model,
            contents=messages,
            config=config
        )

        # ---- APPEND MODEL MESSAGE & INIT LOOP FLAGS --------------------------
        # Add model response to the message stream for the next turn
        messages.append(response.candidates[0].content)

        # Control flags for this iteration
        only_text_response = True

        # Collect tool responses (to be appended as a single 'tool' message)
        function_response_list = []
        stop_after_tool = False
        # ---- HANDLER: FUNCTION CALL PARTS THROTTLE ------------------------
        # Loop over each LLM response part (text + single/multi function calls)
        for part in response.candidates[0].content.parts:
            if stop_after_tool:
                pass

            if part.function_call:
                # Extract the function call and arguments
                function_call_part = types.FunctionCall(
                    name=part.function_call.name,
                    args=part.function_call.args
                )
                name = function_call_part.name

                # ---- PRE-CHECK ------------------
                # 1) Only text response after a proposal
                if run_stats.get("propose_ok", 0) >= 1:
                    _emit("propose_changes", "throttled", "duplicate_proposal_this_run", [
                        "Reply with TEXT ONLY. Summarize the proposed edit in 3 bullets.", "Ask: 'Approve apply in next run?'"
                    ])
                    only_text_response = False
                    stop_after_tool = True
                    break

                # 2) Deny apply in same run as a proposal (enforce two-step)
                if name == "conclude_edit" and run_stats.get("propose_ok", 0) >= 1:
                    _emit("conclude_edit", "apply_denied", "same_run_apply_not_allowed", [
                        "Summarize the proposed edits in 3 bullet points and ask for user approval.",
                        "End the run. In the next run, call conclude_edit with no arguments."
                    ])
                    only_text_response = False
                    stop_after_tool = True
                    break

                # 3) Deny repeated apply in same run
                if name == "conclude_edit" and run_stats.get("apply_ok", 0) >= 1:
                    _emit("conclude_edit", "apply_denied", "duplicate_apply_this_run", [
                        "Do not call conclude_edit again in this run.",
                        "Ask whether further changes or a new proposal cycle are needed."
                    ])
                    only_text_response = False
                    stop_after_tool = True
                    break 
                #-------------------------------------------------------

               # ---- NORMALIZE ARGS & DISPATCH --------------------------------------
                if args.I_O:
                    print(f"function arguments -> {function_call_part.args}")

                # snapshot raw LLM args
                function_call_part.args["function_args"] = dict(function_call_part.args)

               # normalize working directory (force absolute project_root/code_to_fix)
                original_dir = function_call_part.args.get("working_directory", "")
                base_dir = os.path.join(get_project_root(__file__), "code_to_fix")
                function_call_part.args["working_directory"] = os.path.join(base_dir, original_dir) if original_dir else base_dir
                # attach run_id
                function_call_part.args["run_id"] = run_id

                # inject deterministic inputs for conclude_edit from last_prop (no file I/O here)
                if function_call_part.name == "conclude_edit" and not args.reset:
                    if not last_prop:
                        _emit("conclude_edit","apply_denied","no_previous_proposals", [
                        "Previous proposal not existent, generate only text response for user:",
                        "'Error: repeat the request.'"
                    ])
                        only_text_response = False; stop_after_tool = True; break

                    fp = last_prop.get("file_path")
                    ct = last_prop.get("content")
                    wd = (last_prop.get("wd") or last_prop.get("working_directory") or "").strip("/")
                    wd = os.path.join(base_dir, wd) if wd else base_dir

                    if not fp or ct is None:
                        _emit("conclude_edit","apply_denied","Previous proposal missing file_path or content.", [
                        "Previous proposal content or file path not exist, generate only text response for user:",
                        "'Error: changes not applied, please state again the previous request.'"
                    ])
                        only_text_response = False; stop_after_tool = True; break
                    
                    # override working_directory using wd from proposal; file_path stays as-is
                    function_call_part.args["working_directory"] = wd
                    function_call_part.args["file_path"] = fp
                    function_call_part.args["content"] = ct
                    extra_data = {"wd": wd, "fp": fp, "ct": ct}


                    if args.verbose:
                        print(f"[conclude_edit inject] wd={wd!r} file_path={fp!r}, bytes={len(ct)}")

                # dispatch
                function_call_result = call_function(function_call_part, function_dict, verbose=args.verbose)

                # extract tool response
                function_response = function_call_result.parts[0].function_response.response
                if function_response is None:
                    raise Exception("No output from inputted function")

                if args.verbose:
                    print(f"-> {function_response}")

                function_response_list.append(
                    types.Part.from_function_response(
                        name=function_call_part.name,
                        response=function_response,
                    )
                )
               # ---- STATS ------------------------------------------------
                run_stats["tool_calls"] += 1

                # Robust OK detection for dict/str payloads
                res_dict = function_response if isinstance(function_response, dict) else None
                if res_dict is not None:
                    res_text = res_dict.get("result")
                    status_ok = not (
                        res_dict.get("ok") is False or
                        (isinstance(res_text, str) and (
                            res_text.startswith("Error:") or "TIMEOUT" in res_text or "timed out" in res_text
                        ))
                    )
                else:
                    res = function_response
                    status_ok = (
                        (isinstance(res, str) and not res.startswith("Error:") and "TIMEOUT" not in res and "timed out" not in res)
                        or not isinstance(res, str)
                    )

                name = function_call_part.name
                if status_ok:
                    if name == "propose_changes":
                        run_stats["propose_ok"] += 1
                        _emit("propose_changes","directive","proposal_recorded",[
                        "Reply with TEXT ONLY. Summarize the proposed edit in 3 bullets.", "Ask: 'Approve apply in next run?'"])

                        # optional: cache proposed content for save_run_info
                        if isinstance(function_response, dict):
                            proposed_content = function_response.get("content")
                        if proposed_content is None:
                            proposed_content = function_call_part.args.get("content")
                    elif name == "conclude_edit":
                        run_stats["apply_ok"] += 1
                    elif name in ("get_file_content", "get_files_info", "run_python_file"):
                        run_stats["read_ok"] += 1
                else:
                    run_stats["transient_err"] += 1

                # ---- MARK NON-TEXT RESPONSE ------------------------------------------
                # Found a function call → this is not a pure text response
                only_text_response = False

            # ---- IGNORE PLAIN TEXT PARTS ---------------------------------------------
            elif part.text:
                # Plain text part: already handled (or not actionable) → ignore here
                pass
                   
        # ---- POST-RESPONSE ACCOUNTING & EARLY-EXIT -------------------------------------
        um = getattr(response, "usage_metadata", None)
        if args.verbose and um:
            print(f"User prompt: {user_prompt}")
            print(f"Prompt tokens: {um.prompt_token_count}")
            print(f"Response tokens: {um.candidates_token_count}")

        # If the llm respond with only text, stop the cycle and print reponse
        if only_text_response:
            txt = (response.text or "").lower()
            # If model is asking for target directory
            PAT_ASK_DIR = re.compile(r"""
                (specify|which|what|where|indicate|choose|select|target|root
                |working\s*directory|project\s*root|path|folder|dir|tree|structure
                |cartella|percorso|quale|dove)
                .{0,60}
                (directory|folder|path|root|cartella|percorso|dir)
            """, re.I | re.X)

            if PAT_ASK_DIR.search(txt) and run_stats["file_info_blox"] == 0:
                messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text="The project root is 'code_to_fix/'. Use get_files_info on '.' or on the mentioned subfolder.")]
                ))
                run_stats["file_info_blox"] += 1
                continue  # Start a new cycle
            run_stats["text_only"] = True
            print(response.text or "")
            break

        # Add the function response to the message for the next iteration
        if function_response_list:
            messages.append(
                types.Content(
                    role='tool',
                    parts=function_response_list  # <--- Change this from [function_response_list] to function_response_list
                )
            )

    # ---- TRANSIENT EXCEPTIONS (RETRYABLE) -----------------------------------------
    except Exception as e:
        # Error if the LLM is temporarily unavailable
        if "UNAVAILABLE" in str(e):
            run_stats["transient_err"] += 1
            print("Gemini is temporarily unavailable, wait 5 seconds...")
            time.sleep(5)
            continue

        # Error if we called gemini more than 15 times in 1 minute, free version limitation (errore 429)
        if "RESOURCE_EXHAUSTED" in str(e):
            run_stats["transient_err"] += 1
            print("Request per minute limit exceeded, wait 60 seconds...")
            time.sleep(60)
            continue

        # Error if the LLM got an invalid input, probable code error present (errore 400)
        if "INVALID_ARGUMENT" in str(e):
            run_stats["transient_err"] += 1
            print("Code error, try again")
            sys.exit()

        # All error are appended to the message for the next iteration
        error_message = types.Content(
            role="tool",
            parts=[
                types.Part(
                    text="An error occurred during the execution of the loop. Below is the error. "
                        "Adjust your behavior accordingly: " + str(e)
                )
            ]
        )
        messages.append(error_message)

        if args.verbose:
            print("EXCEPTION while block:", e)

# ---- SAVE-TYPE DECISION (END-OF-RUN) ---------------------------------
if run_save["save_type"] == "Default":
    any_useful = (run_stats["propose_ok"] or run_stats["apply_ok"] or run_stats["read_ok"])
    only_transient = (
        run_stats["transient_err"] > 0
        and not any_useful
        and run_stats["tool_calls"] == 0
        and not run_stats["text_only"]
    )

    if only_transient:
        run_save["save_type"] = "Discard_run"
    elif run_stats["text_only"] and run_stats["tool_calls"] == 0:
        run_save["save_type"] = "Additional_run"
    elif run_stats["propose_ok"]:
        run_save["save_type"] = "propose_run"
    else:
        run_save["save_type"] = "Default"

# ---- PERSIST RUN SUMMARY ------------------------------------------------------
match run_save["save_type"]:
    case "Default":
        # Save current run summary
        save_run_info(messages, run_id, extra_data)

    case "Discard_run":
        # If present copy previous run summary 
        if prev_summary_path:
            dst_dir = os.path.join("__ai_outputs__", run_id)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "run_summary.json")
            shutil.copy2(prev_summary_path, dst)
        else:
            pass

    case "Error":
        # Copy previous run summary
        base = {}
        if prev_summary_path and os.path.exists(prev_summary_path):
            with open(prev_summary_path, "r", encoding="utf-8") as f:
                try:
                    base = json.load(f) or {}
                except Exception:
                    base = {}
        # Add metadata of the current run
        ar = base.setdefault("additional_runs", [])
        ar.append({
            "run_id": run_id,
            "type": "error",
            "ts": int(time.time()),
            "message": run_save.get("save_message") or "Invalid apply; resume from previous proposals."
        })
        dst_dir = os.path.join("__ai_outputs__", run_id)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, "run_summary.json"), "w", encoding="utf-8") as f:
            json.dump(base, f, ensure_ascii=False, indent=2)

    case "Additional_run":
        # Save current run
        cur_path = save_run_info(messages, run_id, extra_data)

        # Load previous run
        base_prev = {}
        if prev_summary_path and os.path.exists(prev_summary_path):
            try:
                with open(prev_summary_path, "r", encoding="utf-8") as f:
                    base_prev = json.load(f) or {}
            except Exception:
                base_prev = {}
        with open(cur_path, "r", encoding="utf-8") as f:
            cur_summary = json.load(f) or {}

        # Merge two runs in a single summary
        merged = {
            "proposals": base_prev.get("proposals", []),
            "header": {
                "run_id": run_id,
                "ts": time.time(),
                "mode": "Additional_run"
            },
            "previous_summary": base_prev,
            "current_summary": cur_summary,
        }

        # Summary run as merged of two runs
        dst_dir = os.path.join("__ai_outputs__", run_id)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, "run_summary.json"), "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    case "propose_run":
        # Save current run
        save_run_info(messages, run_id, proposed_content, extra_data)
    case _:
        raise ValueError(f"run_save_type non valido: {run_save['save_type']!r}")
