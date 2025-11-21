## System Architecture
```text 
AiCodeAgent/
├── src/aicodeagent/
│   ├── main.py
│   ├── cli.py
│   ├── pipeline.py
│   ├── llm_client.py
│   │
│   ├── prompts/
│   │   └── system_prompt.py
│   │
│   ├── tools/
│   │
│   ├── functions/
│   │   ├── call_function.py
│   │   ├── functions_schemas.py
│   │   │
│   │   ├── fs/           # File-system operations
│   │   ├── core/         # Snapshots, diffs, save utilities
│   │   ├── pipeline/     # Init, summary, gating
│   │   └── llm_calls/    # Tools exposed to the LLM
│
├── code_to_fix/          # Sandbox
├── examples/             # Demo repository
├── tests/                # Unit, integration, e2e
│
├── ai_outputs/                           # Structured outputs (logs, backups, summaries, diffs)

```

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

```

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
