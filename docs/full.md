# Summary

AiCodeAgent is a fully sandboxed, auditable, reversible LLM-driven refactoring engine.  
The system operates through a strict propose/apply workflow, a secure file-system boundary,  
and a complete snapshot/backup/diff logging layer ensuring full reproducibility and safety.

This document provides a complete technical overview of:

- Architecture and directory structure  
- Design Philosophy / Goals — rationale behind sandboxing, the two-run workflow, and the safety-first architecture.
- LLM interaction model (messages, tools, system prompt, loop)  
- Tooling layer and functions exposed to the model  
- Internal controls (gating, proposal tracking, sandbox enforcement)  
- Snapshot & backup system and audit outputs  
- Output directory structure and run artifacts  
- Error handling & recovery logic  
- CLI usage  
- Demo environment  
- Testing strategy (unit, integration, E2E with real LLM)  
- Development notes (uv, pytest, ruff, workflows)

All components follow a deterministic, multi-layer safety design to ensure safe code modifications,  
complete traceability, and reliable autonomous operation.

---

# Table of Contents

- [System Architecture](#system-architecture)
- [Design Philosophy / Goals](#design-philosophy--goals)
- [How It Works](#how-it-works)
- [LLM Interaction Model](#llm-interaction-model)
  - [3.1 LLM Invocation](#31-llm-invocation)
  - [3.2 Message Structure](#32-message-structure)
  - [3.3 Tool Configuration & System Prompt](#33-tool-configuration--system-prompt)
  - [3.4 Interaction Loop](#34-interaction-loop)
- [Tooling Layer (functions/llm_calls)](#tooling-layer-functionsllm_calls)
  - [File inspection](#file-inspection)
  - [Execution tools](#execution-tools)
  - [Proposal / Apply logic](#proposal--apply-logic)
- [Internal Controls Overview](#internal-controls-overview)
  - [Run-level gating](#run-level-gating)
  - [Secure File-System Layer](#secure-file-system-layer)
  - [Proposal Tracking & Anti-Duplicate Logic](#proposal-tracking--anti-duplicate-logic)
- [Snapshot & Backup System](#snapshot--backup-system)
  - [save_backup](#save_backup)
  - [save_diffs](#save_diffs)
  - [save_file](#save_file)
  - [save_logs](#save_logs)
  - [save_summary_entry](#save_summary_entry)
  - [save_run_info](#save_run_info)
- [Output Directory Structure](#output-directory-structure)
  - [run_summary.json](#run_summaryjson)
  - [diffs/](#diffs)
  - [backups/](#backups)
  - [actions.log](#actionslog)
  - [summary.txt](#summarytxt)
  - [llm_message](#llm_message)
- [Error Handling & Recovery](#error-handling--recovery)
  - [Transient errors](#transient-errors)
  - [Save-type classification](#save-type-classification)
  - [Default / Additional / Propose / Discard](#default--additional--propose--discard)
- [CLI Usage](#cli-usage)
- [Overall Flow](#overall-flow)
- [Role in the System (Audit + Recovery)](#role-in-the-system-audit--recovery)
- [Demo & Example Projects](#demo--example-projects)
- [Testing Strategy](#testing-strategy)
  - [Unit](#unit)
  - [Integration](#integration)
  - [E2E](#e2e)
  - [Canned](#canned)
- [Development Notes](#development-notes)
  - [Requirements](#requirements)
  - [uv dev workflow](#uv-dev-workflow)
  - [ruff](#ruff)
  - [test layering](#test-layering)

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
├── __ai_outputs__/                           # Structured outputs (logs, backups, summaries, diffs)

```
# Design Philosophy / Goals

AiCodeAgent is designed around strict engineering principles that guarantee safety, determinism, and complete auditability while allowing an LLM to assist in refactoring.

## 1. Safety by Construction
All operations occur inside a sandbox (`code_to_fix/`, demo, or test).  
Path normalization, secure‑path enforcement, and directory boundary checks guarantee the model cannot access or modify anything outside controlled areas.

## 2. Two‑Run Pattern (Propose → Apply)
The system enforces a mandatory two‑step workflow:
- **Run 1:** Analyze code and produce a proposal (non‑destructive).
- **Run 2:** Apply the previously saved proposal.

This eliminates destructive edits, prevents infinite loops, and ensures every applied change has a verifiable history.

## 3. Full Auditability & Reproducibility
Each run generates:
- diffs
- backups
- logs
- summary entries
- run_summary.json
- last LLM message

This creates a replayable execution trace suitable for debugging, validation, and forensic analysis.

## 4. Predictable Autonomy
The LLM can operate autonomously but only within strict, deterministic boundaries:
- only declared tools are accessible  
- propose and apply are gated and limited  
- apply is only possible with a verified proposal  
- msg loop is capped and strictly structured  

This provides autonomy without compromising safety or reliability.


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
# LLM Interaction Model

This section describes how AiCodeAgent interacts with the LLM during each run:  
how the model is called, how messages are structured, and how tools + system prompt are configured.

---

## 1. How the LLM Is Called

AiCodeAgent interacts with the LLM through a dedicated backend interface defined in `llm_client.py`.

### 1.1 LLM client abstraction
Two interchangeable backends exist:

- RealLLMClient → real calls to **Gemini 2.0 Flash**
- FileLLMClient → loads pre-saved JSON responses (“canned responses”) for deterministic tests

Both expose a unified method:

```
llm.complete(model=model, messages=messages, config=config)
```

### 1.2 Real LLM call
Real calls use:

```
response = self.client.models.generate_content(
    model=model,
    contents=messages,
    config=config
)
```

Where:

- `model = "gemini-2.0-flash-001"`
- `messages = list of Content objects (system + user + model + tool)`
- `config = GenerateContentConfig(tools=[...], system_instruction=system_prompt)`

### 1.3 Canned LLM calls
FileLLMClient hashes the message content:

```
sha1(role + text_of_all_parts)
```

and loads:

```
response_<hash>.json
```

from the canned directory, simulating an LLM response deterministically.

---

## 2. Message Structure

AiCodeAgent constructs a structured conversation for each run.  
Only three roles are used: `system`, `user`, `model`, `tool`.

### 2.1 System message

Provided to the model via:

```
GenerateContentConfig(system_instruction=system_prompt)
```

Defined in `system_prompt.py`, it includes:

- allowed tools
- strict rules for propose/apply workflow
- working-directory constraints
- safety constraints
- required behavior patterns

The system message never appears inside `messages`.  
It is injected through the config.

---

### 2.2 User messages

User messages are appended directly:

```
messages.append(Content(role="user", parts=[Part(text=prompt)]))
```

If a previous run saved a proposal, the context from that proposal is added as an additional user message:

```
messages.append(Content(role="user", parts=[Part(text=prev_context)]))
```

This maintains continuity across runs.

---

### 2.3 Model messages

An LLM response is appended as:

```
messages.append(response.candidates[0].content)
```

A model message can contain:

- plain text
- one or more function_call parts
- any combination of the above

Internal structure example:

```
[model]
  part.text: "Found an issue in calculator.py"
  part.function_call: name=get_file_content, args={...}
```

---

### 2.4 Tool messages

When the model triggers a tool call, AiCodeAgent executes the Python function and returns:

```
Content(role="tool", parts=[Part.from_function_response(...)])
```

This tool message is appended to `messages` and fed back to the LLM on the next iteration.

This creates a loop:

```
model → tool → model → tool → ...
```

until a pure-text message ends the cycle.

---

## 3. Tool Configuration & System Prompt Integration

Tool availability is managed dynamically based on run state.

### 3.1 Tool schemas

All tools are declared in `functions_schemas.py` using:

```
types.FunctionDeclaration(...)
```

Each includes:

- name
- description
- parameters schema (object type, property names, required fields)

### 3.2 Dynamic registration of conclude_edit

`conclude_edit` is ONLY registered if a previous proposal exists:

```
if has_prev_proposal:
    fn_decls.append(schema_conclude_edit)
```

This ensures the LLM cannot even attempt to call conclude_edit unless it is valid to do so.

---

### 3.3 GenerateContentConfig

Before calling the model:

```
config = GenerateContentConfig(
    tools=[available_functions],
    system_instruction=system_prompt
)
```

Where:

- system_prompt contains all behavioral rules  
- tools exposes only the allowed function declarations  

The model receives:
- the system behavior definition
- the allowed function signatures
- the conversation history

Everything else is blocked.

---

## 4. Interaction Loop Overview

During a run, AiCodeAgent executes an iterative cycle.

### Loop iteration steps

1. Send messages + system prompt + tool config to the LLM  
2. Receive text or function_calls  
3. For each function_call:
   - normalize paths & enforce sandbox rules
   - inject run_id, working_directory
   - optionally inject proposal data
   - execute the Python function
   - create tool response message
4. Append tool result to `messages`
5. Repeat until:
   - pure text only, or
   - proposal throttling, or
   - apply done, or
   - loop count exceeds 15 iterations

---

## 5. Summary

The LLM interaction model is built on:

- A stable system instruction enforcing safe editing
- Structured messages (user, model, tool)
- Dynamic tool exposure based on previous run state
- Iterative LLM → Tool → LLM loop
- Strict sandboxing and gated apply logic

Together, this creates a robust, reversible, auditable LLM-driven refactoring workflow.

# Tooling Layer (functions/llm_calls)

The Tooling Layer defines all Python-side functions that the LLM is allowed to call during a run.  
These tools act as a controlled interface to the sandboxed filesystem and to the code-editing workflow.  
They live in:

```
aicodeagent/functions/llm_calls/
```

---

## 1. `get_files_info`

**Purpose:**  
List files and directories under the project root (`code_to_fix/`) with metadata.

**What it does:**  
- Returns file names, directory names, and size information.  
- Operates strictly inside the sandbox via secure-path checks.

**When to use:**  
- At the beginning of analysis.  
- To discover file structure instead of asking the user.  
- Whenever the model needs to understand the project layout.

---

## 2. `get_file_content`

**Purpose:**  
Read the content of a file inside `code_to_fix/`.

**What it does:**  
- Returns the full file content as text.  
- Applies working-directory normalization and secure-path enforcement.

**When to use:**  
- Before proposing a fix.  
- To inspect a file’s current implementation.  
- While performing static analysis or debugging.

---

## 3. `run_python_file`

**Purpose:**  
Execute a Python script in the sandbox and capture stdout, stderr, and exit code.

**What it does:**  
- Runs the file in a restricted environment.  
- Detects run-time errors, exceptions, or incorrect outputs.

**When to use:**  
- When the user wants debugging, behavioral testing, or validation.  
- To confirm that a bug exists before proposing a fix.

---

## 4. `propose_changes`

**Purpose:**  
Generate non-destructive code edits.

**What it does:**  
- Creates a preview rewrite of the target file.  
- Saves proposed content and diff under `__ai_outputs__/run_<id>/`.  
- Does not modify files.

**When to use:**  
- When the user explicitly requests a code modification.  
- After analyzing a target file and determining a fix.  
- At most once per run.

**Pipeline rules:**  
- After a successful proposal, all further tool calls are throttled.  
- The LLM must stop and wait for the next run.

---

## 5. `conclude_edit` (restricted)

**Purpose:**  
Apply the last approved proposal saved from the previous run.

**What it does:**  
- Loads file_path, content, and working_directory from the previous proposal.  
- Writes changes to disk safely.

**When to use:**  
- Only in a run *after* a proposal was made.  
- Only if the user explicitly requests apply.  
- Only if a valid proposal exists.

**Pipeline guarantees:**  
- Takes no arguments.  
- Cannot be called in the same run as a proposal.  
- Cannot be duplicated.

---

## Summary Table

| Tool               | Purpose                                | When to Use                                                | Restrictions |
|--------------------|------------------------------------------|-------------------------------------------------------------|--------------|
| `get_files_info`   | Explore project structure                | File discovery, initial analysis                           | No editing |
| `get_file_content` | Read file content                        | Inspection before proposing fixes                          | No write operations |
| `run_python_file`  | Execute code, collect outputs/errors     | Behavioral debugging, runtime checks                       | Sandbox only |
| `propose_changes`  | Preview edit (non-destructive)           | When proposing one fix for one file                        | Max 1 per run |
| `conclude_edit`    | Apply previously approved proposal       | Only if previous proposal exists and user asked to apply   | No arguments, strong gating |


# Internal Controls Overview

The agent implements multiple internal control layers to keep each LLM-driven run safe, sandboxed, and auditable.  
These controls ensure that:

- only registered tools can be invoked  
- all edits follow a strict propose/apply flow  
- the model cannot bypass the sandbox or apply edits without a prior proposal  
- every run is tagged with a save type and can be resumed or inspected later  

The control system is composed of:

- **Run-level gating** — strict flow between `propose_changes`, `conclude_edit`, and text output  
- **Secure working-directory normalization** — all operations forced under `code_to_fix/` (or demo/test sandbox)  
- **Proposal tracking** — ensures every apply is tied to an existing proposal  

---

## 1. Run-level gating

Run-level gating is implemented directly in the pipeline loop and controls how the LLM uses the tools during a single run.

### Throttle after a proposal
Once a `propose_changes` call succeeds (`propose_ok >= 1`), any further tool call in the same run is **blocked**.  
The agent emits a synthetic tool response (`propose_changes → throttled`) and forces the model to:

- reply with **text only**  
- summarize the proposal  
- ask for approval for the next run  

### Two-step propose/apply flow
`conclude_edit` is **never** allowed in the same run where a proposal was made.  
If the model calls `conclude_edit` with `propose_ok >= 1`, the agent emits:

- `apply_denied (same_run_apply_not_allowed)`

and instructs the model to:

- summarize the proposed edits  
- stop the current run  
- rely on the next run to apply the changes  

### No double apply in the same run
If `conclude_edit` already succeeded (`apply_ok >= 1`), any additional call is denied with:

- `apply_denied (duplicate_apply_this_run)`  

### No apply without a previous proposal
When `conclude_edit` is invoked, the agent injects file path, content, and working directory from the last saved proposal (`last_prop`).  
If no valid proposal exists, the call is denied with:

- `no_previous_proposals`

and the model is forced to fall back to a text-only explanation.

### Text-only redirect for missing project root
If the model keeps asking *“where is the project root / which folder / path”*, the pipeline intercepts pure-text messages and injects:

> The project root is `code_to_fix/`. Use `get_files_info` on `.` or the mentioned subfolder.

This forces the model to use `get_files_info` instead of looping on vague text.

---

# 2. Secure File-System Layer

The system applies strict file-system protection to prevent the model from reading or modifying anything outside the sandbox.  
This is enforced through three combined mechanisms: **working-directory normalization**, **path enforcement**, and **safety checks** during all tool calls.

---

## 2.1 Working-directory normalization

Every tool that accepts a path (`get_file_content`, `get_files_info`, `propose_changes`, `conclude_edit`) receives a `working_directory` parameter from the LLM.  
The pipeline **ignores** whatever the model provides and applies the following rule:

- In **demo mode**, this is forced to:  
  `project_root/__demo_sandbox__/code_to_fix/calculator_bugged`

- In **test mode**, it is forced to the temporary test sandbox.

- In **normal mode**, it is always forced to `./code_to_fix`.

**Effect:**  
The LLM cannot choose an arbitrary path.  
Any working directory given by the model is rewritten into an absolute, sandbox-confined path.

---

## 2.2 Path enforcement (sandbox boundary)

On top of normalization, each tool applies an additional security layer via `get_secure_path`, which:

- blocks absolute paths such as `/etc/passwd`  
- blocks directory-traversal (`..`)  
- blocks symbolic links pointing outside the sandbox  
- guarantees that the resolved path is always under `code_to_fix/`

If any check fails, the tool call returns a controlled error and performs **no operation**.

**Effect:**  
The LLM cannot access system files or project files outside the sandbox, even with malicious or mistaken input.

---

## 2.3 Read/write isolation

All read/write operations (including `conclude_edit`) execute only after:

- working directory is normalized into the sandbox  
- `file_path` is validated through secure-path enforcement  
- file content is consistent with the last saved proposal  

`conclude_edit` performs the final write **only if**:

- a valid previous proposal exists  
- `(file_path, content)` exactly match the stored proposal  
- the final resolved path passed all security checks  

**Effect:**  
No file can be written without a prior proposal, and no write can occur outside the sandbox.

---

## 2.4 Demo & Test sandbox replication

When the user enables `--demo`:

- the entire mini-repository is copied into `__demo_sandbox__/`
- all operations (read, propose, apply) are executed only on the copy

When running with `--test`, the same logic applies using a temporary E2E test sandbox.

**Effect:**  
The real project files are never modified.

# 3. Proposal Tracking & Anti-Duplicate Logic

The system enforces strict control over proposal management to ensure that every `conclude_edit` is tied to a specific, verifiable, and non-repeated proposal.
This prevents infinite loops, unauthorized edits, and inconsistencies between what the model proposes and what the system actually writes.

---

## 3.1 Retrieving the previous proposal

At the beginning of each run, the pipeline executes:

```python
prev_context, last_prop = prev_proposal(prev_summary_path)
```

This retrieves the last valid proposal, including:

- `file_path`
- `content`
- `working_directory`
- originating `run_id`

If a valid proposal exists, the system:

- injects the context automatically into the conversation
- enables `conclude_edit` only when a proposal is available (`has_prev_proposal = True`)

**Effect:**  
The model can apply edits only if a previously saved proposal exists.

---

## 3.2 Apply constrained to the saved proposal

When the LLM calls `conclude_edit`, the pipeline ignores all arguments provided by the model.
Instead, it overwrites them with the values stored in the previous proposal:

- file path
- content
- normalized working directory

```python
function_call_part.args["file_path"] = fp
function_call_part.args["content"] = ct
function_call_part.args["working_directory"] = str(wd)
```

**Effect:**  
The model cannot modify the target file or content when applying changes.
Only the validated proposal can be applied.

---

## 3.3 Automatic denial of apply without a proposal

If:

- `last_prop` does not exist, or
- `file_path` / `content` are missing, or
- the saved proposal is inconsistent,

then the pipeline issues:

```python
emit("conclude_edit", "apply_denied", "no_previous_proposals", ...)
stop_after_tool = True
```

**Effect:**  
The LLM cannot apply spontaneous or ungrounded modifications.

---

## 3.4 Anti-duplicate apply

The pipeline tracks how many successful `conclude_edit` operations occurred in the run:

```python
if run_stats["apply_ok"] >= 1:
    deny_duplicate_apply
```

If the model attempts a second apply in the same run, it is immediately blocked.

**Effect:**  
Only one apply per run is allowed, preventing file corruption and undefined behavior.

---

## 3.5 Anti-duplicate proposal (loop prevention)

If the model attempts to generate more than one proposal in the same run:

- after the first successful proposal (`propose_ok >= 1`), all further tool calls are blocked
- the system forces the model into a **text-only** response requiring it to:
  - summarize the proposal
  - request confirmation for applying it in the next run

There is no hash-comparison mechanism.
The pipeline enforces structural gating that guarantees:

- exactly one proposal per run
- no redundant proposals
- no propose → propose → propose loops

---

## 3.6 Persistence and auditability

Every proposal is stored in:

```
__ai_outputs__/run_<id>/run_summary.json
```

Each entry includes:

- proposed content
- diff / patch
- context messages
- working directory
- timestamp

**Effect:**  
All modification steps are fully traceable, reproducible, and auditable.

# Snapshot & Backup System

AiCodeAgent maintains a complete **snapshot, backup, diff, and run-summary logging system** to guarantee:

- full auditability  
- reproducible changes  
- run-level inspectability  
- safety in case of errors  
- manual rollback capability  

All artifacts are stored under:

```
__ai_outputs__/run_<id>/
```

with the structure:

```
backups/
diffs/
actions.log
summary.txt
run_summary.json
llm_message
```

---

## 1. `save_backup`

**File:** `core/save_backup.py`  
**Role:** create a versioned copy of the original file before any real modification is applied.

### How it works

- Uses **get_secure_path** → guarantees the backup path stays inside the safe directory.  
- Uses **get_versioned_path** → generates incremental versions  
  (`file.py`, `file.py.1`, `file.py.2`, …).  
- Copies the source file via `shutil.copy2`.

### Target path

```
__ai_outputs__/run_<id>/backups/<filename>.<N?>
```

### Why it is critical

- Ensures no modification can destroy the original data.  
- Enables complete audit and manual rollback.  
- Used only by **conclude_edit** (never during dry-run).

---

## 2. `save_diffs`

**File:** `core/save_diffs.py`  
**Role:** save the full diff generated between the original file and the proposed content.

### How it works

- Validates and normalizes the output path (`get_secure_path` + `get_versioned_path`).  
- Writes the diff using **unified_diff** format.

### Target path

```
__ai_outputs__/run_<id>/diffs/<filename>.diff
```

(versioned as required)

### Why it is critical

- Acts as the technical audit trail of all changes.  
- Essential for inspecting proposals before applying them.  
- Provides the bridge between `propose_changes` and `conclude_edit`.

---

## 3. `save_file` (central entrypoint)

**File:** `core/save_file.py`  
**Role:** orchestrate backup, diff creation, logging, and summary generation when the system updates a file.

### Internal pipeline

When invoked with:

- **source_path + content:**  
  - compute diff between original and new content  
  - create backup (if not dry-run)  
  - write final file  

- **content only:**  
  - treat as new file, diff vs empty  

### Output artifacts

- backup (if applicable)  
- diff  
- log entry → `actions.log`  
- summary entry → `summary.txt`  

### Storage locations

```
__ai_outputs__/run_<id>/backups/
__ai_outputs__/run_<id>/diffs/
__ai_outputs__/run_<id>/actions.log
__ai_outputs__/run_<id>/summary.txt
```

---

## 4. `save_logs`

**File:** `core/save_logs.py`  
**Role:** record every tool operation executed during a run.

### Log entry includes

- timestamp  
- tool name  
- result (OK / ERROR / TIMEOUT)  
- target file (if any)  
- execution details  
- clipped stdout/stderr or content preview (~500 chars)

### Target path

```
__ai_outputs__/run_<id>/actions.log
```

### Importance

- Provides complete traceability  
- Critical for debugging run behavior  
- Ensures reproducibility and transparency  

---

## 5. `save_summary_entry`

**File:** `core/save_summary_entry.py`  
**Role:** generate a **human-readable summary** of a tool action, including diffs and log context.

### Generated content

- function header (`propose_changes`, `conclude_edit`, etc.)  
- associated log entry  
- human-readable diff (via `make_human_readable_diff`)  
- arguments passed to the tool  
- separators between entries  

### Target path

```
__ai_outputs__/run_<id>/summary.txt
```

### Why it exists

- Immediate human-readable audit format  
- Useful for quick inspection without parsing JSON or multiple diff files  

---

## 6. `save_run_info`

**File:** `core/save_run_info.py`  
**Role:** build a structured, machine-readable ledger of the run as a final JSON snapshot.

### Stored data (examples)

- last user prompt  
- last assistant text  
- list of tool calls (up to latest N)  
- extracted error/status info  
- recorded proposals  
- content digests  
- injected data for `conclude_edit` (wd, file_path, lengths)  

### Output files

```
__ai_outputs__/run_<id>/run_summary.json
__ai_outputs__/run_<id>/llm_message
```

### Critical role

- Forms the state for restoring context in the next run  
- Enables full audit and reproducibility  
- Supports gating logic by recording valid proposals  

---

# Output Directory Structure

Each AiCodeAgent execution creates an isolated output folder:

```
__ai_outputs__/run_<id>/
```

This directory contains all artifacts required for auditing, debugging, reproducibility, and safe code recovery.

---

## 1. run_summary.json

A structured JSON snapshot of the run.

**Contains:**
- user prompt (cleaned and normalized)
- last assistant text
- list of tool calls with status (OK / ERROR / TIMEOUT)
- arguments and metadata extracted from the tool responses
- recorded proposals (file path, working directory, content length, digest)
- injected data used by `conclude_edit` (wd, file_path, content_len)

**Purpose:**  
Machine-readable ledger used for:
- context restoration in the next run  
- proposal integrity verification  
- audit and reproducibility  

---

## 2. diffs/

Directory storing unified diff patches:

```
__ai_outputs__/run_<id>/diffs/<file>.diff
```

**Each patch includes:**
- unified diff format (`--- original`, `+++ modified`)
- line-by-line modifications
- versioned filenames (`file.py`, `file.py.1`, ...)

**Purpose:**  
Technical audit trail of changes, used for human review before apply.

---

## 3. backups/

Contains versioned backups of original files before modifications:

```
__ai_outputs__/run_<id>/backups/<file>.<n?>
```

**Purpose:**  
Guarantee that original data is preserved before writing updates.  
Enables manual rollback and forensic inspection.

---

## 4. actions.log

Plain-text chronological execution log.

**Includes:**
- timestamps  
- tool name  
- result (OK / ERROR / TIMEOUT)  
- file involved  
- execution details  
- clipped stdout/stderr or content (~500 chars)

**Purpose:**  
Traceability, debugging, and transparency of tool operations.

---

## 5. summary.txt

Human-readable summary combining:

- function header (propose_changes / conclude_edit / etc.)
- associated log line
- readable diff (via `make_human_readable_diff`)
- arguments provided to the tool

**Purpose:**  
Quick inspection without diving into JSON or raw diffs.

---

## 6. llm_message

Contains the last text message produced by the LLM.

**Purpose:**  
Explainability and post-run reasoning review.

---

# Error Handling & Recovery

AiCodeAgent implements a structured error‑handling and recovery system to ensure that every run is safely terminated, recorded, and classified.

This mechanism prevents partial writes, guarantees auditability, and maintains consistent run history across interrupted or inconsistent flows.

---

## Error Sources

The system identifies three major classes of failures:

### 1. **Transient errors**
Examples:
- API rate limits (`RESOURCE_EXHAUSTED`)
- Temporary unavailability (`UNAVAILABLE`)
- Formatting/argument errors (`INVALID_ARGUMENT`)

These increment:  
`run_stats["transient_err"]`.

Transient errors do **not** immediately terminate the run; the loop may retry or fall back to a text‑only message.

---

## End‑of‑Run Classification

At the end of the pipeline, the system assigns a `save_type` to the run.  
This determines how the run is stored under `__ai_outputs__/run_<id>/`.

### ### Decision Logic

```
if only_transient:
    Discard_run
elif text_only and no tool_calls:
    Additional_run
elif propose_ok >= 1:
    propose_run
else:
    Default
```

---

## Save-Type Definitions

### **Discard_run**
Triggered when:
- at least one transient error occurred
- no useful operation (`propose_ok == 0`, `apply_ok == 0`, `read_ok == 0`)
- zero tool calls
- response not classified as text-only

Meaning:  
**The model never produced anything usable → run is discarded.**

No `run_summary.json` is saved.

---

### **Additional_run**
Triggered when:
- the run produced *only text*
- no tool calls occurred

Meaning:  
A valid descriptive run (clarifications, narrative, explanations) that extends context  
but performs no action.

Saved with:
- `run_summary.json`
- `llm_message`

Useful for:
- multi-step reasoning  
- asking for user confirmation  
- model explanations

---

### **propose_run**
Triggered when:
- at least one successful `propose_changes` occurred

Meaning:  
A proposal run that must be preserved for future `conclude_edit`.

Files saved:
- diffs/
- summary entries
- proposal digest in `run_summary.json`

This run becomes the **only source of truth** for the next apply.

---

### **Default**
Triggered when:
- the run executed read operations or debugging tasks  
  (`get_file_content`, `get_files_info`, `run_python_file`)
- no proposals were made

Meaning:  
A standard informative run.  
Saved normally with full metadata.

---

## Recovery Behavior

### If the model fails mid-run
- The run becomes either `Discard_run` or `Additional_run`
- No filesystem writes are performed
- The next run starts cleanly with stored history (if any)

### If the model repeatedly fails
The pipeline continues:
- retrying transient errors
- falling back to text-only messages
- always saving the safest possible run format

### If apply fails (`conclude_edit`)
The system:
- blocks the write
- logs the denial
- preserves the previous proposal
- forces the model to explain the error in plain text

---

## Guarantees

This recovery system ensures:

- No corrupted writes
- No accidental apply without proposal
- No lost proposal context
- Deterministic run history
- Fully inspectable audit chain

It forms the reliability backbone of AiCodeAgent’s autonomous execution model.

# CLI Usage

AiCodeAgent provides a minimal CLI interface that controls sandbox mode, test mode, run visibility, and verbosity.

## Flags Overview

| Flag | Description | Typical Use |
|------|-------------|--------------|
| `--demo` | Enables **demo sandbox mode**. Copies the `examples/minirepo` into `__demo_sandbox__/` and runs entirely on the copy. | Safe public demos, tutorials, workshops. |
| `--test` | Enables **test sandbox mode**. Used by automated E2E tests, ensuring that all operations run inside an isolated temporary directory. | CI pipelines, pytest E2E runs. |
| `--reset` | Disables loading previous proposals. The run starts as if it were the first one. | When previous proposal state must be ignored. |
| `--I_O` | Prints every LLM iteration (“Iteration #1, #2…”) with inputs/outputs and tool calls. | Debugging LLM behavior, inspecting message flow. |
| `--verbose` | Prints low-level internals: injected args, conclude_edit rewrite, function results, traceback on errors. | Deep debugging; development mode. |

## Behavior Summary

- `--demo` and `--test` rewrite the **working directory** so the agent never touches real project files.
- `--reset` prevents the agent from applying a proposal created in previous runs.
- `--I_O` is the recommended switch for understanding the LLM reasoning loop.
- `--verbose` is noisy but essential for diagnosing pipeline issues.


# Overall Flow

## When the system applies an edit (`conclude_edit`)

1. Backup original file  
2. Generate diff against new version  
3. Write updated file  
4. Append log entry  
5. Append human-readable summary entry  
6. Update `run_summary.json`  

## When the system proposes a change (`propose_changes`)

1. No backup created  
2. Generate diff vs original file  
3. Append log entry  
4. Append summary entry  
5. Update `run_summary.json` as a **proposal run**  

---

# Role in the System (Audit + Recovery)

| Component           | Function                               | Audit / Recovery Type          |
|---------------------|-----------------------------------------|--------------------------------|
| `backups/`          | preserves original file state           | rollback                       |
| `diffs/`            | shows line-by-line modifications        | technical audit                |
| `actions.log`       | chronological tool registry             | debugging / traceability       |
| `summary.txt`       | human-readable diffs & logs             | human audit                    |
| `run_summary.json`  | structured ledger of the run            | reproducibility / replay       |
| `llm_message`       | last model output text                  | explainability                 |

---

This layer forms the core infrastructure for:

- safety of code modifications  
- post-hoc analysis  
- multi-level debugging  
- manual recovery  

# Demo & Example Projects

AiCodeAgent includes a self-contained demo environment designed for safe experimentation without touching real project files.

## 1. What `examples/minirepo` Contains

```
examples/minirepo/
└── code_to_fix/
    └── calculator_bugged/
        ├── main.py
        ├── tests.py
        ├── lorem.txt
        └── pkg/
            ├── calculator.py      # contains the precedence bug
            ├── render.py
            └── morelorem.txt
```

**Key features:**

- A deliberately buggy calculator implementation (wrong operator precedence).
- A small package layout (subdirectory + multiple files).
- Minimal test script (`tests.py`).
- Neutral text files to test file-listing behavior.

This repo is small enough for an LLM to analyze, but complex enough to test:

- directory navigation  
- file discovery  
- bug detection  
- proposing fixes  
- applying patches  
- verifying run outputs  

---

## 2. How to Use the Demo

Run AiCodeAgent in demo mode:

```
uv run aicodeagent "Analyze the calculator app and propose fixes" --demo
```

Behavior:

- The entire `examples/minirepo` directory is copied into:
  ```
  __demo_sandbox__/code_to_fix/
  ```
- All operations (read, propose, apply) run only on the **copied** version.
- Backups, diffs, logs, and summaries are still written to the usual:
  ```
  __ai_outputs__/run_<id>/
  ```

To apply the last approved proposal:

```
uv run aicodeagent "Apply last approved proposal" --demo
```

Using the demo ensures safe public demonstrations, tutorials, or workshops without modifying real code.

---

# Testing Strategy

AiCodeAgent includes a multi-layer test suite covering unit, integration, and end-to-end behavior.

## 1. Unit Tests

Location:
```
tests/unit/
```

Covers each LLM-callable tool in isolation:

- `get_files_info`
- `get_file_content`
- `run_python_file`
- `propose_changes`
- `conclude_edit`

These tests check:

- secure-path enforcement  
- correct output formatting  
- correct write behavior  
- error handling  
- dry-run behavior  

Example (simplified):
- write a file, call `conclude_edit`, assert the file is modified

## 2. Integration Tests (No LLM)

Location:
```
tests/integration/
```

These tests validate:

- pipeline structure  
- message assembly  
- tool dispatch  
- non-LLM code paths  
- canned responses (when available)  

They run with static data and confirm that the logic surrounding the LLM behaves deterministically.

## 3. End-to-End Tests (Real LLM)

Location:
```
tests/e2e/
```

These use `RealLLMClient` and a temporary sandbox (`--test` behavior).

They simulate real scenarios:

- discovering buggy code  
- reading files  
- identifying the precedence bug  
- proposing a patch  
- navigating subdirectories  
- handling gating logic  
- applying diffs (second run)

Tests also classify failures:

- “hard fail” → real breakage  
- “soft fail / xfail” → LLM produced reasonable but incomplete reasoning  

This makes the test suite robust against LLM stochasticity.

## 4. Canned Tests (Deterministic)

Location:
```
tests/integration/data/canned_llm/`
```

Some canned responses exist, but canned testing is limited because:

- hashing logic must match exactly  
- small changes in prompts alter the hash  
- real LLM runs provide better reliability for this project  

(You correctly chose to rely mostly on real e2e runs.)

---

# Development Notes

Internal guidelines and infrastructure for contributing, debugging, and running AiCodeAgent.

## 1. Requirements

- **Python ≥ 3.12**
- `uv` as the primary environment manager
- Google GenAI SDK (`google-genai==1.12.1`)

Install all dependencies:

```
uv sync
```

## 2. Development Dependency Group

Defined in `pyproject.toml`:

```
[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "ruff>=0.14.6",
]
```

Install dev tools:

```
uv sync --group dev
```

## 3. Code Formatting & Linting

Configured in `ruff.toml`:

```
line-length = 88
target-version = "py312"

[lint]
select = ["E", "F", "W"]
ignore = ["E501"]
fixable = ["ALL"]
```

Run formatting:

```
ruff check --fix
```

## 4. Project Layout & Entrypoints

Entrypoint defined in `pyproject.toml`:

```
[project.scripts]
aicodeagent = "aicodeagent.cli:main"
```

Main development workflow:

- run pipeline via CLI
- use `--demo` or `--test` modes for safe experiments
- inspect `__ai_outputs__/run_<id>/` for debugging

## 5. Recommended Workflow

1. Edit or refactor code in `src/aicodeagent/`
2. Run unit tests:
   ```
   pytest tests/unit
   ```
3. Run integration tests:
   ```
   pytest tests/integration
   ```
4. Run full e2e tests (requires valid API key):
   ```
   pytest tests/e2e -m llm
   ```
5. Use `--I_O` during debugging to inspect LLM iteration-by-iteration.
6. Keep a clean separation between:
   - core logic  
   - LLM calls  
   - test sandboxes  
   - demo environment  
