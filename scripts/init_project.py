from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRS = [
    "app",
    "src/auth",
    "src/gmail",
    "src/analysis",
    "src/actions",
    "src/storage",
    "src/models",
    "src/utils",
    "data/raw",
    "data/processed",
    "data/outputs",
    "logs",
    "tests",
    "docs"
]

FILES = [
    "main.py",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "app/streamlit_app.py",
    "src/auth/gmail_auth.py",
    "src/gmail/client.py",
    "src/gmail/fetch_messages.py",
    "src/gmail/parse_headers.py",
    "src/analysis/aggregate_senders.py",
    "src/analysis/scoring_rules.py",
    "src/analysis/rank_candidates.py",
    "src/actions/label_actions.py",
    "src/actions/trash_actions.py",
    "src/actions/filter_actions.py",
    "src/storage/save_json.py",
    "src/storage/export_csv.py",
    "src/storage/decisions.py",
    "src/models/schemas.py",
    "src/reporting/generate_cleanup_report.py",
    "src/utils/email_utils.py",
    "src/utils/logging_utils.py",
    "docs/architecture.md",
    "docs/decisions.md"
]


def create_dirs():
    for d in DIRS:
        path = ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"[DIR]  {path}")


def create_files():
    for f in FILES:
        path = ROOT / f
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            path.touch()
            print(f"[FILE] {path}")


def create_gitignore():
    path = ROOT / ".gitignore"

    content = """
venv/
__pycache__/
*.pyc
.env
token.json
credentials.json

data/raw/
data/processed/
data/outputs/

logs/
.DS_Store
"""

    path.write_text(content.strip())
    print("[INIT] .gitignore created")


def create_requirements():
    path = ROOT / "requirements.txt"

    content = """
google-api-python-client
google-auth
google-auth-oauthlib
google-auth-httplib2
pandas
pydantic
python-dotenv
streamlit
"""

    path.write_text(content.strip())
    print("[INIT] requirements.txt created")


def create_readme():
    path = ROOT / "README.md"

    content = """
# Gmail Cleanup Copilot

A human-in-the-loop Gmail cleanup assistant that identifies low-value senders,
explains why they were flagged, and lets the user review candidates before taking action.

## Features

- Gmail message ingestion
- Sender aggregation
- Cleanup candidate ranking
- Human approval before destructive actions

## Architecture

See docs/architecture.md
"""

    path.write_text(content.strip())
    print("[INIT] README.md created")


def main():
    print("Initializing project structure...\n")

    create_dirs()
    create_files()
    create_gitignore()
    create_requirements()
    create_readme()

    print("\nProject initialized successfully.")


if __name__ == "__main__":
    main()