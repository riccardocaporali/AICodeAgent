# ---- IMPORTS & INTERNALS -----------------------------------------------------
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from aicodeagent.functions.core.save_run_info import save_run_info
from aicodeagent.functions.fs.get_project_root import get_project_root
from aicodeagent.functions.pipeline.options import PipelineOptions
from aicodeagent.llm_client import FileLLMClient, RealLLMClient
from aicodeagent.pipeline import run_pipeline

# ---- CLI ARGS PARSING --------------------------------------------------------
# - CLI parser for user prompt and debug flags
parser = argparse.ArgumentParser(
    description="LLM code analyzer and debugger",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("prompt", nargs="?", help="Prompt to send to the model")

parser.add_argument("--verbose", action="store_true", help="Print extra diagnostics")

parser.add_argument(
    "--I_O",
    action="store_true",
    help="Print messages (LLM input) and function response args (LLM output)",
)

parser.add_argument(
    "--reset", action="store_true", help="Reset the previous run summary"
)

parser.add_argument("--demo", action="store_true", help="Access to bugged demo file")

parser.add_argument("--offline", action="store_true", help="Use canned llm")

args = parser.parse_args()

# Validate user input (stderr + non-zero exit code)
if not args.prompt:
    print("No prompt provided", file=sys.stderr)
    sys.exit(1)

if args.offline:
    p = Path("tests/integration/data/canned_llm")
    llm = FileLLMClient(canned_dir=p)
else:
    llm = RealLLMClient()

# ---- USER PROMPT & OPTIONS & PATH-----------------------------------------------------
user_prompt = args.prompt

options = PipelineOptions(
    verbose=args.verbose,
    I_O=args.I_O,
    reset=args.reset,
    demo=args.demo,
)
project_root = Path(get_project_root(__file__))

# ---- CALL PIPELINE----------------------------------------------------
result = run_pipeline(user_prompt, llm, options, project_root)

run_id = result["run_id"]
messages = result["messages"]
save_type = result["save_type"]
extra_data = result["extra_data"]
prev_summary_path = result["prev_summary_path"]
proposed_content = result["proposed_content"]

# ---- PERSIST RUN SUMMARY ------------------------------------------------------
match save_type:

    case "Default":
        # Save current run summary normally
        save_run_info(messages, run_id, extra_data)

    case "Discard_run":
        # Copy previous summary if available
        if prev_summary_path:
            dst_dir = Path("__ai_outputs__") / run_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prev_summary_path, dst_dir / "run_summary.json")

    case "Error":
        # Load previous summary if present
        base = {}
        if prev_summary_path and Path(prev_summary_path).exists():
            try:
                with open(prev_summary_path, "r", encoding="utf-8") as f:
                    base = json.load(f) or {}
            except Exception:
                base = {}

        # Add this run as error
        ar = base.setdefault("additional_runs", [])
        ar.append(
            {
                "run_id": run_id,
                "type": "error",
                "ts": int(time.time()),
                "message": "Invalid apply; resume from previous proposals.",
            }
        )

        dst_dir = Path("__ai_outputs__") / run_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        with open(dst_dir / "run_summary.json", "w", encoding="utf-8") as f:
            json.dump(base, f, indent=2, ensure_ascii=False)

    case "Additional_run":
        # Save current run
        cur_path = save_run_info(messages, run_id, extra_data)

        # Load previous run
        base_prev = {}
        if prev_summary_path and Path(prev_summary_path).exists():
            try:
                with open(prev_summary_path, "r", encoding="utf-8") as f:
                    base_prev = json.load(f) or {}
            except Exception:
                base_prev = {}

        # Load current run
        with open(cur_path, "r", encoding="utf-8") as f:
            cur_summary = json.load(f) or {}

        # Merge two runs
        merged = {
            "proposals": base_prev.get("proposals", []),
            "header": {
                "run_id": run_id,
                "ts": time.time(),
                "mode": "Additional_run",
            },
            "previous_summary": base_prev,
            "current_summary": cur_summary,
        }

        dst_dir = Path("__ai_outputs__") / run_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        with open(dst_dir / "run_summary.json", "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)

    case "propose_run":
        # Save proposal run
        save_run_info(messages, run_id, proposed_content, extra_data)

    case _:
        raise ValueError(f"Invalid save_type: {save_type!r}")
