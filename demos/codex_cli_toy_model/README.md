# Codex CLI — Toy modeling demo

This demo trains and evaluates a simple classifier on a scikit-learn toy dataset (Iris, Digits, or Wine).

Quick start

1. Create a virtual environment and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

2. Run the demo (defaults to Iris + Random Forest):

```bash
python run_toy_model.py --outdir demo_outputs
```

Outputs
- `demo_outputs/model.joblib` — trained model
- `demo_outputs/metrics.json` — accuracy and classification report

Using Codex CLI

This repository contains an integration helper `mcp_prompt_broker.integrations.codex_cli.run_codex_cli`.
If you have a local Codex CLI, set the environment variable `CODEX_CLI_CMD` to the executable and call that helper
from Python to programmatically ask Codex to edit or extend the demo. Example:

```python
from mcp_prompt_broker.integrations import codex_cli
res = codex_cli.run_codex_cli('Refactor run_toy_model.py to add cross-validation', timeout=60, env={'CODEX_CLI_CMD': 'codex-cli'})
print(res['stdout'])
```

This demo is intentionally simple so you can use it as a starting point for Codex-driven code generation or experiment workflows.
