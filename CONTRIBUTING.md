# Contributing to Stegcore

## Dev environment

```bash
python -m venv stegcore_venv
source stegcore_venv/bin/activate      # Linux / macOS
stegcore_venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## Running the project

```bash
python main.py           # GUI
python cli.py wizard     # CLI wizard
```

## Code style

- PEP 8, 100-character line limit
- Every `.py` file — including empty package markers (`__init__.py`) — must open with the AGPL-3.0 header block:

```python
# Copyright (C) 2026 Daniel Iwugo
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License.
# See <https://www.gnu.org/licenses/> for details.
```

The CI licence-check job will fail the build if any tracked `.py` file is missing this header.

## Submitting a pull request

1. Fork the repo and branch off `dev`
2. Keep each PR to one logical change
3. Describe what changed and why in the PR body
4. Open the PR against `dev`, not `main`

## Branch conventions

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only — do not PR directly to `main` |
| `dev`  | Integration branch — target all PRs here |
