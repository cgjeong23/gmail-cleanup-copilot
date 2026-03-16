from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI()

PROJECT_ROOT = Path("/workspace")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run-cleanup")
def run_cleanup() -> dict:
    try:
        result = subprocess.run(
            ["python", "scripts/run_cleanup_pipeline.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))