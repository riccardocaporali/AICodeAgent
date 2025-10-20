# Code_Fixer – AI-Driven Code Refactoring Agent

Code_Fixer is an AI agent for automatic code analysis, debugging, and refactoring.  
It uses Google Gemini with function-calling to read, analyze, propose, and safely apply code edits inside a sandboxed environment.

Each session generates:
- detailed logs and statistics  
- diff and backup files  
- structured run summaries (`run_summary.json`) ensuring full continuity between runs

---

## Main Features

| Category | Description |
|-----------|-------------|
| Code analysis | Reads and interprets Python files inside `code_to_fix/` to detect bugs or refactoring opportunities. |
| Change proposals (preview) | Generates non-destructive previews via `propose_changes`. |
| Controlled application (apply) | Applies only previously proposed edits, verified by `(file_path, content_len)` or digest. |
| Full traceability | Each run creates a directory `__ai_outputs__/run_xxx/` containing logs, summaries, and backups. |
| Sandbox safety | All operations are restricted to the `code_to_fix/` folder, preventing accidental writes elsewhere. |

---

## System Architecture

code_fixer/
│
├── main.py # Main LLM loop (prompt, gating, summary)
│
├── functions/
│ ├── functions_schemas.py # Function schemas exposed to the model
│ ├── call_function.py # Dispatcher for function execution
│ ├── internal/
│ │ ├── init_run_session.py # Creates run_id and output folders
│ │ ├── save_run_info.py # Serializes run information
│ │ ├── prev_proposal.py # Loads previous proposals for gating
│ │ ├── prev_run_summary_path.py # Finds last run summary JSON
│ │ ├── save_file.py # Handles file saving and automatic backups
│ │ └── ... (other utilities)
│
├── code_to_fix/ # Sandboxed folder analyzed by the agent
│
└── ai_outputs/ # Structured outputs (logs, backups, summaries)

yaml
Copia codice

---

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/riccardocaporali/code_fixer.git
   cd code_fixer
Create a .env file with your Gemini API key:

bash
Copia codice
GEMINI_API_KEY=your_api_key_here
Install dependencies:

bash
Copia codice
pip install -r requirements.txt
Run a quick test:

bash
Copia codice
python main.py "Say hello"
How It Works
Each execution (run_id) represents one autonomous LLM session.

Analysis:

bash
Copia codice
python main.py "Find potential bugs in utils/math.py" --I_O
Propose changes:

bash
Copia codice
python main.py "Fix the bug you found" --I_O
Apply previously proposed edits:

bash
Copia codice
python main.py "Apply the proposed fix" --I_O
Proposals are saved in run_summary.json and reused in the next run for consistent apply validation.

Safety Mechanisms
Mechanism	Purpose
Throttle	Prevents multiple apply_changes or propose_changes calls in the same run.
Gating	Allows applying only edits that were explicitly proposed in a previous run.
Recovery	If the model flow fails, the run is saved as Error or Additional_run and can safely resume.

Run Save Types
Type	Meaning
Default	Valid run, fully saved.
Additional_run	Continuation or text-only run.
Error	Flow error in the model logic.
Discard_run	Transient errors only, nothing to save.

Testing
Run all tests with:

bash
Copia codice
pytest -v
License
Open-source project released under the MIT License.
Created by Riccardo Caporali – Aerospace Engineer & AI Developer.