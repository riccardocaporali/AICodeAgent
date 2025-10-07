import os
import argparse
import sys 
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


# API and client definition
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Missing GEMINI_API_KEY in environment. Aborting.")
    sys.exit(1)
client = genai.Client(api_key=api_key)

# Generate run number
run_id = init_run_session()

# Extract user prompt and specifics
parser = argparse.ArgumentParser(description="LLM code analyzer and debugger")

parser.add_argument(
    "prompt",
    nargs="?",
    help="Prompt da inviare al modello"
)

parser.add_argument(
    "--verbose",
    action="store_true",
    help="Stampa dettagli extra"
)

parser.add_argument(
    "--I_O",
    action="store_true",
    help="Stampa messages (LLM input) e function response args (LLM output)"
)

parser.add_argument(
    "--reset",
    action="store_true",
    help="Reset the run summary of the previous run"
)

args = parser.parse_args()

if not args.prompt:
    print("No prompt provided")
    sys.exit(1)


# Define LLM's input arguments
model = "gemini-2.0-flash-001"
user_prompt = args.prompt

# Load previus run information
prev_summary_path = prev_run_summary_path(run_id)

# If previous run present, append information as first message
messages = []
gating_state = {}

if prev_summary_path and not args.reset:
    prev_context, gating_state = prev_proposal(prev_summary_path)
    messages.append(types.Content(role="user", parts=[types.Part(text=prev_context)]))

messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

available_functions = types.Tool(
    function_declarations=[
        schemas.schema_get_files_info,
        schemas.schema_get_file_content,
        schemas.schema_run_python_file,
        schemas.schema_propose_changes,
        schemas.schema_apply_changes
    ]
)

# Throttle block function call and save 
run_guard = {
    "block_apply_this_run": False,    
    "block_propose_this_run": False,  
    "saw_propose_this_run": False,
    "pending_apply_targets": None,
    "message": "",
    "next_action":"",
}

# Save variaibles
run_save = {
    "save_type":"Default",
    "save_message":"",
}

# Run stats tracker
run_stats = {
    "tool_calls": 0,
    "text_only": False,
    "propose_ok": 0,
    "apply_ok": 0,
    "read_ok": 0,           # get_file_content / get_files_info / run_python_file OK
    "transient_err": 0,     # UNAVAILABLE / RESOURCE_EXHAUSTED / timeout signal
    "flow_error": 0,        # apply_denied/mismatch ecc.
}

# System promtp
system_prompt = """
You are an AI agent for refactoring and debugging code.

### === Available operations ===
You can perform the following operations by generating appropriate function calls:
- List files and directories             # via get_files_info
- Read file contents                     # via get_file_content
- Execute Python files with arguments    # via run_python_file
- Propose changes or create files safely # via propose_changes (non-destructive preview)
- Apply real changes to files            # via apply_changes (requires user confirmation)

### === Previous state management ===
- Treat PREV_RUN_JSON as the canonical state (last user prompt, touched files, assistant’s last text).
- Use this state to infer the natural target; do not generate long plans.

### === Target inference (for modifications only) ===
When the user omits a specific file/path and the request implies editing or creating files, infer the target in this order:
1) last propose_changes target;
2) last get_file_content file;
3) last file explicitly named in assistant.last_text.
- If there is exactly one unambiguous candidate, use it.
- Otherwise, ask exactly one short clarifying question on a single line (no preamble) and stop.

### === Path constraints ===
- All operations take place inside the main 'code_to_fix/' directory.
- Do NOT include 'code_to_fix/' in paths; the system prepends it using 'working_directory' or 'directory'.

### === Action policy ===
- Default stance: do not apply destructive changes.
- You may always perform non-destructive actions that directly support the user’s request: list, read, and run code.
- Propose edits via propose_changes when your analysis identifies a specific fix/refactor (even if not explicitly requested).
- Default = minimal_fix: prefer the smallest patch that addresses the issue; no new features/renames unless explicitly requested.

### === APPLY CHANGES POLICY ===
- `apply_changes` is **non-creative**: it must reproduce **exactly** the last `propose_changes` from context (`PREV_RUN_JSON`), with the **same file_path set** and **identical content**.
- **Never** add/remove/alter files, lines, APIs, tests, or features beyond that proposal. Any deviation is an **error**.
- If **no valid proposal exists**, do **not** call `apply_changes`; generate a single `propose_changes` and **stop**.
- Before applying, **match** `file_path` and `content_len`. On any mismatch or ambiguity: ask **one brief question** or regenerate `propose_changes`, then **stop** (do not apply).
- After applying, provide a **one-line summary** of what was applied. Logs/diffs/backups are handled by the framework.

### === Exploration (read-only) ===
- For analyze/explain/review/bug-hunt: perform read-only exploration **without asking questions** until a small budget is reached (up to **5 files** or **~20kB** total).
- Exploration order: README*/docs/* → entrypoints (main.py/app.py/__main__.py) → core modules in project subfolders → any file referenced in PREV_RUN_JSON.

### === Read vs. Analyze ===
- If the user explicitly asks to show/read a file, call only get_file_content and return raw content (no extra commentary).
- If the user asks to analyze/search for bugs/explain behavior, you may read and/or run code and provide concise reasoning pointing to exact lines/symptoms.

### === Scope & safety ===
- Modify only files directly related to the issue/request.
- Never invent file names or content you cannot justify from context or analysis.
- Never restructure folders unless the structure is clearly the root cause and the user approves.
- Keep diffs minimal and scoped.

### === Ambiguity handling ===
- If anything remains ambiguous after target inference, ask exactly one short clarifying question on a single line, using the language of the user’s last message. Do not include plans, lists, or next steps.

### === Output discipline ===
- Do not output explanations after each individual propose_changes.
- When all previews for the current task are complete, provide one concise summary describing:
  • what is proposed,
  • why it is needed,
  • how each change works.
- Logs, diffs, and backups are handled by the framework; do not duplicate them.

### === Tests ===
- If tests exist, use them.
- If tests are relevant but missing, propose exactly one new test under code_to_fix/tests/test_<project>.py via propose_changes; apply it only after approval.

### === Language ===
- Default to the language used in the user’s last message.
"""

config=types.GenerateContentConfig(
    tools=[available_functions], system_instruction=system_prompt
)

# Iterative loop
cycle_number = 0

while cycle_number <= 15 :
    cycle_number += 1

    try:
        # Generate LLM's response
        print(f"---------------Iteration number:{cycle_number}----------------")
        if args.I_O:
            print("\n--- ULTIMI MESSAGGI ---")
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
            model = model,
            contents =  messages,
            config = config
        )

        # Add model response to the next message iteration
        messages.append(response.candidates[0].content)

        # Set variable to exit while cycle if it remains true
        only_text_response = True

        # List to store function responses
        function_response_list = []

        # Loop over each llm response parts (text + function or multifunction)
        for part in response.candidates[0].content.parts:
            if part.function_call:
                # Extract the function call and arguments
                function_call_part = types.FunctionCall(
                    name=part.function_call.name,
                    args=part.function_call.args
                )
                ##############################
                # === THROTTLE ===
                if run_guard["block_apply_this_run"] and function_call_part.name == "apply_changes":
                    throttle_payload = {
                        "ok": False,
                        "error": {
                            "type": "throttled",
                            "reason": "apply_blocked_this_run",
                            "message": run_guard["message"],
                            "next_action": run_guard["next_action"]
                        }
                    }
                    if args.I_O:
                        print(f"-> THROTTLE apply_changes: {throttle_payload['error']}")
                    function_response_list.append(
                        types.Part.from_function_response(name="apply_changes", response=throttle_payload)
                    )
                    only_text_response = False
                    continue

                if run_guard["block_propose_this_run"] and function_call_part.name == "propose_changes":
                    throttle_payload = {
                        "ok": False,
                        "error": {
                            "type": "throttled",
                            "reason": "propose_blocked_this_run",
                            "message": run_guard["message"],
                            "next_action": run_guard["next_action"]
                        }
                    }
                    if args.I_O:
                        print(f"-> THROTTLE propose_changes: {throttle_payload['error']}")
                    function_response_list.append(
                        types.Part.from_function_response(name="propose_changes", response=throttle_payload)
                    )
                    only_text_response = False
                    continue

                # === GATING for apply_changes ===
                if function_call_part.name == "apply_changes":
                    args_fc = function_call_part.args or {}
                    file_path = args_fc.get("file_path")
                    content = args_fc.get("content")
                    content_len = len(content) if isinstance(content, str) else None
                    if run_guard["pending_apply_targets"] == None:
                        allowed = gating_state.get("allowed_apply_targets", set())  # set of (file_path, content_len)
                        run_guard.setdefault("pending_apply_targets", set(allowed))
                    else:
                        allowed = run_guard["pending_apply_targets"]

                    deny_reason = None
                    if not allowed:
                        # No proposals in previous run
                        deny_reason = "no_previous_proposals"
                        # Block apply changes 
                        run_guard["block_apply_this_run"] = True
                        # Look if current run has done a previous proposal
                        if run_guard["saw_propose_this_run"]:
                            run_guard["block_propose_this_run"] = True
                            run_guard["message"] = "You can't apply changes yet, return to the user a text response explaining the proposed changes."
                            run_guard["next_action"] = "return_text_explanation"
                            run_save["save_type"] = "Error"
                            run_save["save_message"] = "Tried apply changes without a propose changes in the previous run resulting into an error"
                            
                        else:
                            # No current or previous proposal, save type error so to load last save_summary
                            run_guard["message"] = "Generate exactly one propose_changes preview; do NOT call apply_changes in this run."
                            run_guard["next_action"] = "create_proposal"
                    

                    elif not file_path or content_len is None:
                        # Missing mandatory inputs for a safe apply
                        deny_reason = "missing_content_or_path"
                        # Block propose changes for rest of the run, llm must launch apply correctly
                        run_guard["block_propose_this_run"] = True
                        run_guard["message"] = "apply_changes requires both file_path and content matching a prior proposal."
                        run_guard["next_action"] = "retry_apply_with_matching_proposal"

                    elif (file_path, content_len) not in allowed:
                        # Proposal mismatch (path or length)
                        deny_reason = "proposal_mismatch"
                        # Block next propose changes untill llm generate a valid apply changes
                        run_guard["block_propose_this_run"] = True 
                        run_guard["message"] = "The provided (file_path, content_len) does not match any proposal from the previous run."
                        run_guard["next_action"] = "retry_apply_with_matching_proposal"

                    if deny_reason:
                        # Do NOT call the tool; return a synthetic tool-response to guide the LLM
                        error_payload = {
                            "ok": False,
                            "error": {
                                "type": "apply_denied",
                                "reason": deny_reason,
                                "message": run_guard["message"],
                                "next_action": run_guard["next_action"] 
                            },
                        }
                        if allowed:
                            # provide a small hint on what would be accepted (cap to 5 for brevity)
                            sample = list(allowed)[:5]
                            error_payload["error"]["expected_any_of"] = [
                                {"file_path": fp, "content_len": cl} for (fp, cl) in sample
                            ]

                        if args.I_O:
                            print(f"-> DENY apply_changes: {error_payload['error']}")

                        function_response_list.append(
                            types.Part.from_function_response(
                                name="apply_changes",
                                response=error_payload,
                            )
                        )
                        only_text_response = False
                        continue  # skip calling the real tool
                    ##############################

                # Print for testing
                if args.I_O:
                    print(f"function arguments -> {function_call_part.args}")

                # Define hard coded function arguments
                # Snapshot of LLM generated function argument to be printed in summary 
                function_call_part.args["function_args"] = dict(function_call_part.args) 

                # Working directory is always rooted in './code_to_fix' for safety. The LLM only provides relative paths
                original_dir = function_call_part.args.get("working_directory", "")
                base_dir = "code_to_fix"
                if original_dir:
                    function_call_part.args["working_directory"] = os.path.join(base_dir, original_dir)
                else:
                    function_call_part.args["working_directory"] = base_dir

                # Insert run id number 
                function_call_part.args["run_id"] = run_id

                # Call the selected function 
                function_call_result = call_function(function_call_part, function_dict, verbose=args.verbose)

                # Extract result for printing
                function_response = function_call_result.parts[0].function_response.response
                if function_response is None:
                    raise Exception("No output from inputted function")
                if args.verbose:
                    print(f"-> {function_response}")
            
                # Add the function response to the list
                function_response_list.append(
                    types.Part.from_function_response( 
                        name=function_call_part.name,
                        response=function_response,
                    )
                )

                # Run statistics
                run_stats["tool_calls"] += 1
                # Evaluate call result
                res = function_response.get("result") if isinstance(function_response, dict) else function_response
                status_ok = (isinstance(res, str) and not res.startswith("Error:") and "TIMEOUT" not in res and "timed out" not in res) or not isinstance(res, str)

                name = function_call_part.name
                if status_ok:
                    if name == "propose_changes": run_stats["propose_ok"] += 1
                    elif name == "apply_changes": run_stats["apply_ok"] += 1
                    elif name in ("get_file_content","get_files_info","run_python_file"): run_stats["read_ok"] += 1
                else:
                    if name == "apply_changes":
                        run_stats["flow_error"] += 1

                #####################
                # Detect succesfull propose changes  
                if function_call_part.name == "propose_changes":
                    # Detect success from the tool's textual result
                    res_str = ""
                    if isinstance(function_response, dict):
                        res_str = function_response.get("result", "")
                    else:
                        res_str = str(function_response or "")

                    success = isinstance(res_str, str) and (
                        res_str.startswith("Save proposed changes to") or
                        res_str.startswith("Save proposed creation of")
                    )
                    if success:
                        run_guard["saw_propose_this_run"] = True
                        run_guard["block_apply_this_run"] = True

                # Detect succesfull apply changes       
                if function_call_part.name == "apply_changes":
                    # Detect success from the tool's textual result
                    res_str = ""
                    if isinstance(function_response, dict):
                        res_str = function_response.get("result", "")
                    else:
                        res_str = str(function_response or "")

                    success = isinstance(res_str, str) and (
                        res_str.startswith("Successfully wrote to") or
                        res_str.startswith("dry run is set to true")
                    )
                    if success:
                        # Case: Apply successfully generated 
                        # Ensure we have the pending set
                        if "pending_apply_targets" not in run_guard:
                            run_guard["pending_apply_targets"] = set(gating_state.get("allowed_apply_targets", set()))

                        # Remove the just-applied target from pending list
                        run_guard["pending_apply_targets"].discard((file_path, content_len))

                        # Verify if other apply targets are present
                        if run_guard["pending_apply_targets"]:
                            run_guard["block_apply_this_run"] = False # Unlock apply run if so
                            run_guard["block_propose_this_run"] = True
                            run_guard["message"] = "Call apply_changes on the pending proposals"
                            run_guard["next_action"] = "apply_pending_proposal"
                        else:
                            run_guard["block_apply_this_run"] = True  # Lock next apply run
                            # Enable new propose in the run
                            run_guard["block_propose_this_run"] = False 
                            run_guard["message"] = "No more pending proposal present, can't call apply_changes"
                            run_guard["next_action"] = "return_text_explanation"
                        if args.I_O:
                            print(f"-> APPLY success: applied {(file_path, content_len)}; "
                                  f"pending left={len(run_guard['pending_apply_targets'])}")
                    else:
                        # Apply non riuscito (FS/errori vari): non toccare i flag qui.
                        if args.I_O:
                            print("-> APPLY failed (no success signature): flags left unchanged")
                    #######################

                # Found a function call → continue the iteration loop
                only_text_response = False

            # Skip plain text parts (already handled or not actionable)
            elif part.text: 
                pass

        # Print specifics
        um = getattr(response, "usage_metadata", None)
        if args.verbose and um:
            print(f"User prompt: {user_prompt}")
            print(f"Prompt tokens: {um.prompt_token_count}")
            print(f"Response tokens: {um.candidates_token_count}")
            
        # If the llm respond with only text, stop the cycle and print reponse
        if only_text_response:
            print(response.text)
            break

        # Add the function response to the message for the next iteration
        if function_response_list:
            messages.append(
                types.Content(
                    role='tool',
                    parts=function_response_list # <--- Change this from [function_response_list] to function_response_list
                )
            )

    except Exception as e:
        # Error if the LLM is temporarily unavailable
        if "UNAVAILABLE" in str(e):
            print("Gemini is temporarily unavailable, wait 5 seconds...")
            time.sleep(5)  
            continue

        # Error if we called gemini more than 15 times in 1 minute, free version limitation (errore 429)
        if "RESOURCE_EXHAUSTED" in str(e):
            print("Request per minute limit exceeded, wait 60 seconds...")
            time.sleep(60) 
            continue

         # Error if the LLM got an invalid input, probable code error present (errore 400)
        if "INVALID_ARGUMENT" in str(e):
            print("Code error, try again")
            sys.exit()

        # All error are appended to the message for the next iteration
        error_message = types.Content(
            role="tool",
            parts=[
                types.Part(text="An error occurred during the execution of the loop. Below is the error. Adjust your behavior accordingly: " + str(e))
            ]
        )
        messages.append(error_message)

        if args.verbose:
            print("EXCEPTION while block:", e)

# Save configuration
if run_guard["save_type"] == "Default":  # decidi solo se non già fissato
    any_useful = (run_stats["propose_ok"] or run_stats["apply_ok"] or run_stats["read_ok"])
    only_transient = (run_stats["transient_err"] > 0 and not any_useful and run_stats["tool_calls"] == 0 and not run_stats["text_only"])

    # 2) Discard_run — solo errori transitori per tutta la run
    if only_transient:
        run_guard["save_type"] = "Discard_run"

    # 4) Additional_run — nessuna tool call utile, ma testo o Q/A che vuoi “portare avanti”
    elif run_stats["text_only"] and not any_useful and run_stats["tool_calls"] == 0:
        run_guard["save_type"] = "Additional_run"

    # 3) Error — errore di flusso LLM (es. apply chiamato male) e nessun esito utile
    elif run_stats["flow_error"] and not any_useful:
        run_guard["save_type"] = "Error"

    # 1) Default — il resto (almeno qualcosa di utile successo)
    else:
        run_guard["save_type"] = "Default"

# Save the text response in a file for next llm run
match run_save["save_type"]:
    case "Default":
            # Save current run summary
            save_run_info(messages, run_id)
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
        cur_path = save_run_info(messages, run_id)

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

            # Merge metadata
            "header": {
                "run_id": run_id,
                "ts": time.time(),
                "mode": "Additional_run"
            },

            # The two runs
            "previous_summary": base_prev,
            "current_summary": cur_summary,  
        }

        # 4) Summary run as merged of two runs
        dst_dir = os.path.join("__ai_outputs__", run_id)
        os.makedirs(dst_dir, exist_ok=True)
        with open(os.path.join(dst_dir, "run_summary.json"), "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    case _:
        raise ValueError(f"run_save_type non valido: {run_guard['save_type']!r}")
