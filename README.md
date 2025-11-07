# AiCodeAgent – AI-Driven Code Refactoring Agent

AiCodeAgent is an AI-driven code refactoring agent designed for autonomous debugging, analysis, and self-contained code repair.
It uses Google Gemini with function-calling to read, analyze, propose, and safely apply code edits inside a sandboxed environment.

Each session generates:
- detailed logs and statistics  
- diff and backup files  
- structured run summaries (`run_summary.json`) ensuring full continuity between runs

---

## Main Features

| Category | Description |
|-----------|-------------|
| Code analysis | The agent can explore and inspect any file inside `code_to_fix/` using its built-in tools: `get_files_info`, `get_file_content`, and `run_python_file`. These allow it to list files, read source code, and execute scripts to observe runtime behavior. |
| Change proposals (preview) | Generates non-destructive previews via `propose_changes`, where the LLM suggests code modifications without altering files. |
| Controlled application (apply) | Applies only previously proposed edits, verified through `(file_path, content_len)` or digest checks for safety and consistency. |
| Full traceability | Each run creates a structured directory `ai_outputs/run_xxx/` containing logs, summaries, backups, and diffs for full auditability. |
| Sandbox safety | All operations are confined to the `code_to_fix/` folder, ensuring the LLM cannot access or modify files outside the sandbox. |

---

## System Architecture
```text
AiCodeAgent/
│
├── src/
│   └── aicodeagent/
│       ├── main.py                               # Main LLM loop (prompt, throttling/gating, summary)
│       │
│       ├── functions/
│       │   ├── functions_schemas.py              # Function schemas exposed to the model
│       │   ├── call_function.py                  # Dispatcher for function execution
│       │   │
│       │   ├── llm_calls/                        # Tools callable by the LLM (function-calling)
│       │   │   ├── conclude_edit.py
│       │   │   ├── get_file_content.py
│       │   │   ├── get_files_info.py
│       │   │   ├── propose_changes.py
│       │   │   └── run_python.py
│       │   │
│       │   └── internal/                         # Internal helpers (IO, persistence, guards, utils)
│       │       ├── clear_output_dirs.py
│       │       ├── get_secure_path.py
│       │       ├── get_versioned_path.py
│       │       ├── init_run_session.py
│       │       ├── make_human_readable.py
│       │       ├── prev_proposal.py
│       │       ├── prev_run_summary_path.py
│       │       ├── reset_test_env.py
│       │       ├── save_backup.py
│       │       ├── save_diffs.py
│       │       ├── save_file.py
│       │       ├── save_logs.py
│       │       ├── save_run_info.py
│       │       └── save_summary_entry.py
├── code_to_fix/                          # Sandboxed workspace analyzed by the agent
│
├── examples/
│   └── minirepo/
│       └── code_to_fix/
│           └── calculator_bugged/        # Demo project used in quickstart
│
├── ai_outputs/                           # Structured outputs (logs, backups, summaries, diffs)
│
└── tests/                                # Pytest-based test suite

```
## Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/riccardocaporali/AiCodeAgent.git
    cd AiCodeAgent
    ```

2. **Create a `.env` file with your Gemini API key**

    ```bash
    GEMINI_API_KEY=your_api_key_here
    ```

3. **Install dependencies using uv**

    ```bash
    uv sync
    ```

4. **Run a quick test**

    ```bash
    uv run aicodeagent "Hello"
    ```

---  

## Quick Demo

A ready-to-run demo is included to showcase the agent’s workflow.

```bash
bash demo_quickstart.sh

## How It Works

Each execution (`run_id`) represents one autonomous LLM session that analyzes code, detects issues, and proposes safe corrections inside the sandbox.

**Typical flow**
```bash
uv run aicodeagent "Analyze and fix the code"

During the run, the agent:
 • Inspects files under code_to_fix/
 • Identifies issues and proposes non-destructive changes
 • Saves diffs, logs, and summaries under __ai_outputs__/run_<id>/

To apply the last approved proposal:
uv run aicodeagent "Apply the proposed fix"

All proposals and metadata are stored in:
__ai_outputs__/run_<id>/run_summary.json
(for reproducibility and audit)


## Safety Mechanisms

| Mechanism | Purpose |
|----------|---------|
| Throttle | Prevents multiple `conclude_edit` or `propose_changes` calls in the same run. |
| Gating   | Allows applying only edits that were explicitly proposed in a previous run. |
| Recovery | If the model flow fails, the run is saved as `Error` or `Additional_run` and can safely resume. |

## Run Save Types

| Type            | Meaning                                                  |
|-----------------|----------------------------------------------------------|
| Default         | Valid run, fully saved.                                  |
| Additional_run  | Continuation or text-only run.                           |
| Propose_run     | Save proposal changes to the code for next run           |
| Error           | Flow error in the model logic.                           |
| Discard_run     | Transient errors only, nothing to save.                  |


## License

Open-source project released under the MIT License.  
Created by Riccardo Caporali – Aerospace Engineer & AI Developer.
