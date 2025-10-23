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
# - Locate previous run summary; extract PREV_RUN_JSON
# - Seed `messages` with previous context (if any) and current user prompt
prev_summary_path = prev_run_summary_path(run_id)

messages = []

if prev_summary_path and not args.reset:
    prev_context, _ = prev_proposal(prev_summary_path)
    messages.append(types.Content(role="user", parts=[types.Part(text=prev_context)]))

messages.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))

# ---- TOOL DECLARATIONS (FUNCTION SCHEMAS) ------------------------------------
# - Register available tools for the model: list/read/run/propose/apply
available_functions = types.Tool(
    function_declarations=[
        schemas.schema_get_files_info,
        schemas.schema_get_file_content,
        schemas.schema_run_python_file,
        schemas.schema_propose_changes,
        schemas.schema_apply_changes,
    ]
)

# ---- GUARDS & TRACKERS INIT --------------------------------------------------
# - Propose content variable
proposed_content = None

# - Throttle/gating guard (per-run)
run_guard = {
    "block_apply_this_run": False,
    "block_propose_this_run": False,
    "message": "",
    "next_action": "",
}

# - Save policy state (final save-type decision + collected flow errors)
run_save = {
    "save_type": "Default",
    "flow_errors": [],   # collected throttled/apply_denied entries with minimal context
}

# - Run stats (aggregated at end-of-run for save-type decision)
run_stats = {
    "tool_calls": 0,
    "text_only": False,
    "propose_ok": False,
    "apply_ok": 0,
    "read_ok": 0,        # get_file_content / get_files_info / run_python_file OK
    "transient_err": 0,  # UNAVAILABLE / RESOURCE_EXHAUSTED / timeouts
    "flow_error": 0,     # apply_denied / throttled (policy blocks)
}

# - Call order tracker (to detect HARD/SOFT recovery after first flow block)
run_order = {
    "call_idx": 0,
    "flow_first_idx": None,
    "recovered_after_flow": False,  # HARD: propose/apply OK after block
    "recovered_soft": False,        # SOFT: read/run OK after block
}

# ---- SYSTEM PROMPT & MODEL CONFIG -------------------------------------------
# - Define model id, system instruction, and tool config
model = "gemini-2.0-flash-001"

# System prompt
system_prompt = """
You are an AI agent for refactoring and debugging code.

## Core tools
You can call:
- get_files_info → list files
- get_file_content → read files
- run_python_file → execute files
- propose_changes → preview edits (non-destructive). Saves the full proposed content into PREV_RUN_JSON.
- apply_changes → apply the last approved proposal from PREV_RUN_JSON. Call with NO arguments.

All paths are inside 'code_to_fix/'. Do NOT include that prefix.

## Behavior rules
1) Read-only tasks (examine, inspect, analyze, review, search for bugs)
   - Use ONLY get_files_info, get_file_content, and run_python_file.
   - Do NOT call propose_changes or apply_changes unless the user explicitly asks to modify code.

2) Proposing edits
   - Call propose_changes only when you have a concrete fix/refactor for a specific file.
   - Exactly ONE proposal per run. After a successful proposal, DO NOT call propose_changes again in the same run.
   - Keep diffs minimal and scoped to the target file.

3) Applying edits (new behavior)
   - apply_changes is NON-CREATIVE and takes NO parameters.
   - When called, the tool loads file_path and content from the last saved proposal in PREV_RUN_JSON and writes it.
   - If there is no valid previous proposal, DO NOT try to fabricate arguments. Return a brief text explaining that a proposal is required or that no changes can be applied, and STOP.

4) Error handling
   - If any tool returns error.type = "throttled" or indicates a missing or invalid proposal:
     • reason = "no_previous_proposals" → make exactly one propose_changes, then STOP.  
     • reason = "proposal_missing_content_or_path" or "proposal_mismatch" → regenerate one valid propose_changes, then STOP.
   - If propose_changes is blocked for this run, DO NOT attempt it again; return a brief textual summary of the intended change.

5) Scope & clarity
   - Touch only files directly relevant to the user request.
   - If the target file is unclear, ask ONE short clarifying question and STOP.
   - All files and directories are inside 'code_to_fix/' by default.

6) Output
   - Provide short, direct summaries of what you found or proposed.
   - Do not echo large code blocks unless strictly necessary for the fix.

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

        # ---- HANDLER: FUNCTION CALL PARTS THROTTLE ------------------------
        # Loop over each LLM response part (text + single/multi function calls)
        for part in response.candidates[0].content.parts:
            if part.function_call:
                # Extract the function call and arguments
                function_call_part = types.FunctionCall(
                    name=part.function_call.name,
                    args=part.function_call.args
                )
                run_order["call_idx"] += 1

                # ---- THROTTLE --------------------------------------------------------
                if run_guard["block_apply_this_run"] and function_call_part.name == "apply_changes":
                    throttle_payload = {
                        "ok": False,
                        "error": {
                            "type": "throttled",
                            "reason": "apply_blocked_this_run",
                            "message": run_guard["message"],
                            "next_action": run_guard["next_action"],
                        },
                    }
                    if args.I_O:
                        print(f"-> THROTTLE apply_changes: {throttle_payload['error']}")
                    function_response_list.append(
                        types.Part.from_function_response(name="apply_changes", response=throttle_payload)
                    )
                    run_stats["flow_error"] += 1
                    if run_order["flow_first_idx"] is None:
                        run_order["flow_first_idx"] = run_order["call_idx"]
                    only_text_response = False
                    run_save["flow_errors"].append({
                        "idx": run_order["call_idx"],
                        "type": "throttled",
                        "reason": throttle_payload["error"]["reason"],
                        "message": throttle_payload["error"]["message"],
                    })
                    continue

                if run_guard["block_propose_this_run"] and function_call_part.name == "propose_changes":
                    throttle_payload = {
                        "ok": False,
                        "error": {
                            "type": "throttled",
                            "reason": "propose_blocked_this_run",
                            "message": run_guard["message"],
                            "next_action": run_guard["next_action"],
                        },
                    }
                    if args.I_O:
                        print(f"-> THROTTLE propose_changes: {throttle_payload['error']}")
                    function_response_list.append(
                        types.Part.from_function_response(name="propose_changes", response=throttle_payload)
                    )
                    run_stats["flow_error"] += 1
                    if run_order["flow_first_idx"] is None:
                        run_order["flow_first_idx"] = run_order["call_idx"]
                    only_text_response = False
                    run_save["flow_errors"].append({
                        "idx": run_order["call_idx"],
                        "type": "throttled",
                        "reason": throttle_payload["error"]["reason"],
                        "message": throttle_payload["error"]["message"],
                    })
                    continue
                # ----------------------------------------------------------------------

                # ---- NORMALIZE ARGS & DISPATCH --------------------------------------
                # Debug print (optional)
                if args.I_O:
                    print(f"function arguments -> {function_call_part.args}")

                # Keep a snapshot of raw LLM args for summary/debug
                function_call_part.args["function_args"] = dict(function_call_part.args)

                # Normalize working directory inside sandboxed root
                original_dir = function_call_part.args.get("working_directory", "")
                base_dir = "code_to_fix"
                if original_dir:
                    function_call_part.args["working_directory"] = os.path.join(base_dir, original_dir)
                else:
                    function_call_part.args["working_directory"] = base_dir

                # Attach run_id for downstream logging
                function_call_part.args["run_id"] = run_id
                if function_call_part.name == "apply_changes" and not args.reset:
                    try:
                        if prev_summary_path and os.path.exists(prev_summary_path):
                            with open(prev_summary_path, "r", encoding="utf-8") as _f:
                                _prev = json.load(_f) or {}
                            _props = _prev.get("proposals") or []
                            _p = next(
                                (p for p in reversed(_props)
                                if p.get("file_path") and (p.get("content") is not None)),
                                None
                            )
                            if _p:
                                _content = _p["content"]
                                _file_path = _p["file_path"]
                                function_call_part.args["file_path"] = _file_path
                                function_call_part.args["content"] = _content
                                # opzionale se hai già il digest nel proposal:
                                if "digest" in _p:
                                    function_call_part.args["digest"] = _p["digest"]
                            else:
                                raise RuntimeError(
                                    "Nessun proposal con contenuto disponibile. Esegui prima propose_changes."
                                )
                    except Exception as _e:
                        if args.verbose:
                            print(f"[apply_changes override skipped] {type(_e).__name__}: {_e}")

                # Dispatch selected tool
                function_call_result = call_function(function_call_part, function_dict, verbose=args.verbose)

                # Extract tool response payload
                function_response = function_call_result.parts[0].function_response.response
                if function_response is None:
                    raise Exception("No output from inputted function")

                if args.verbose:
                    print(f"-> {function_response}")

                # Accumulate to emit as a single 'tool' message at the end of the turn
                function_response_list.append(
                    types.Part.from_function_response(
                        name=function_call_part.name,
                        response=function_response,
                    )
                )

                # ---- STATS & RECOVERY TRACKING ---------------------------------------
                run_stats["tool_calls"] += 1

                # Evaluate call result (robusto per dict/str)
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
                        run_stats["propose_ok"] = True
                        # Extract proposed content from tool response
                        proposed_content = function_response.get("content") if isinstance(function_response, dict) else None
                        if proposed_content is None:
                            proposed_content = function_call_part.args.get("content")
                        run_guard["block_propose_this_run"] = True
                        run_guard["message"] = "A proposal was already created in this run."
                        run_guard["next_action"] = "return_text_explanation"
                        # Block apply this run
                        run_guard["block_apply_this_run"] = True  
                        run_guard["message"] = "Apply is disabled in the same run as a proposal. Use apply in a new run." 
                        run_guard["next_action"] = "return_text_explanation"  
                        # HARD recovery (useful propose/apply after first flow block)
                        if run_order["flow_first_idx"] is not None and run_order["call_idx"] > run_order["flow_first_idx"]:
                            run_order["recovered_after_flow"] = True
                    elif name == "apply_changes":
                        run_stats["apply_ok"] += 1
                        if run_order["flow_first_idx"] is not None and run_order["call_idx"] > run_order["flow_first_idx"]:
                            run_order["recovered_after_flow"] = True
                    elif name in ("get_file_content", "get_files_info", "run_python_file"):
                        run_stats["read_ok"] += 1
                        # SOFT recovery (useful read/run after first flow block)
                        if run_order["flow_first_idx"] is not None and run_order["call_idx"] > run_order["flow_first_idx"]:
                            run_order["recovered_soft"] = True
                else:
                    res_dict = function_response if isinstance(function_response, dict) else None
                    is_flow = (
                        res_dict
                        and res_dict.get("ok") is False
                        and res_dict.get("error", {}).get("type") in {"apply_denied", "throttled"}
                    )
                    if is_flow:
                        run_stats["flow_error"] += 1
                        if run_order["flow_first_idx"] is None:
                            run_order["flow_first_idx"] = run_order["call_idx"]
                    else:
                        run_stats["transient_err"] += 1

                # ---- SUCCESS HOOKS (PROPOSE/APPLY) -----------------------------------
                if function_call_part.name == "propose_changes":
                    # Detect success from tool result text
                    res_str = ""
                    if isinstance(function_response, dict):
                        res_str = function_response.get("result", "")
                    else:
                        res_str = str(function_response or "")

                    success = isinstance(res_str, str) and (
                        res_str.startswith("Save proposed changes to")
                        or res_str.startswith("Save proposed creation of")
                    )

                if function_call_part.name == "apply_changes":
                    # Detect success from tool result text
                    res_str = ""
                    if isinstance(function_response, dict):
                        res_str = function_response.get("result", "")
                    else:
                        res_str = str(function_response or "")

                    success = isinstance(res_str, str) and (
                        res_str.startswith("Successfully wrote to") or
                        res_str.startswith("dry run is set to true")
                    )
                    if success and args.I_O:
                        print("-> APPLY success")
                    elif args.I_O:
                        print("-> APPLY not successful (no success signature)")

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
            if re.search(r'(specify|which|what|where).{0,40}directory', txt):
                messages.append(types.Content(
                    role="user",
                    parts=[types.Part(text="The project root is 'code_to_fix/'. Use get_files_info on '.' or on the mentioned subfolder.")]
                ))
                continue  # Start a new cycle
            run_stats["text_only"] = True
            print(response.text)
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

# ---- SAVE-TYPE DECISION (END-OF-RUN) ------------------------------------------
if run_save["save_type"] == "Default":
    any_useful = (run_stats["propose_ok"] or run_stats["apply_ok"] or run_stats["read_ok"])
    only_transient = (run_stats["transient_err"] > 0 and not any_useful and run_stats["tool_calls"] == 0 and not run_stats["text_only"])

    # 1) Discard_run — only transient errors in all of the run
    if only_transient:
        run_save["save_type"] = "Discard_run"

    # 2) Recovered from error with soft function call
    elif (run_order["flow_first_idx"] is not None) and run_order.get("recovered_soft") and not (run_stats["propose_ok"] or run_stats["apply_ok"]):
        run_save["save_type"] = "Additional_run"

    # 3) Error — llm flow error
    elif (run_order["flow_first_idx"] is not None) and (not run_order["recovered_after_flow"]) and not any_useful:
        run_save["save_type"] = "Error"
        if run_save.get("flow_errors"):
            last = run_save["flow_errors"][-1]
            run_save["save_message"] = f"{last['type']}:{last['reason']} @call#{last['idx']} — {last['message']}"
        else:
            run_save["save_message"] = "Flow blocked and not recovered within the run."

    # 4) Additional_run — no relevant tool call, add previous run
    elif run_stats["text_only"] and run_stats["tool_calls"] == 0:
        run_save["save_type"] = "Additional_run"

    # 5) Propose_changes called
    elif run_stats["propose_ok"] == True:
        run_save["save_type"] = "propose_run"

    # 6) Default
    else:
        run_save["save_type"] = "Default"

# ---- PERSIST RUN SUMMARY ------------------------------------------------------
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
        save_run_info(messages, run_id, proposed_content)
    case _:
        raise ValueError(f"run_save_type non valido: {run_save['save_type']!r}")