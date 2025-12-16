Contributing
============

Contributions are welcome. Please open issues for features/bugs and submit PRs to the `main` branch.

Development
- Create a virtualenv: `python -m venv .venv`
- Install requirements: `pip install -r requirements.txt`
- Run tests: `pytest -q`
- Run the app locally: `uvicorn app.main:app --reload`

Notes
- This project is intentionally minimal and CPU-friendly for easy demos and CI runs.
