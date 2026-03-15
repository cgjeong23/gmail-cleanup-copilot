# src/analysis/rank_candidates.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.analysis.scoring_rules import score_sender


def load_user_rules(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def rank_cleanup_candidates(
    sender_summary_df: pd.DataFrame,
    user_rules: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    rows = []

    for record in sender_summary_df.to_dict(orient="records"):
        result = score_sender(record, user_rules=user_rules)

        rows.append({
            "sender_email": result.sender_email,
            "sender_domain": result.sender_domain,
            "message_count": record.get("message_count", 0),
            "last_seen": record.get("last_seen", ""),
            "sample_subject": record.get("sample_subject", ""),
            "unsubscribe_count": record.get("unsubscribe_count", 0),
            "score": result.score,
            "label": result.label,
            "override": result.override or "",
            "reasons": " | ".join(result.reasons),
        })

    ranked = pd.DataFrame(rows)

    # Sort priority:
    # 1) score desc
    # 2) message_count desc
    # 3) last_seen desc if sortable
    if "last_seen" in ranked.columns:
        ranked["last_seen_sort"] = pd.to_datetime(ranked["last_seen"], errors="coerce")
    else:
        ranked["last_seen_sort"] = pd.NaT

    ranked = ranked.sort_values(
        by=["score", "message_count", "last_seen_sort"],
        ascending=[False, False, False],
        kind="stable",
    ).reset_index(drop=True)

    ranked = ranked.drop(columns=["last_seen_sort"])

    return ranked


def run_ranking_pipeline(
    sender_summary_path: Path,
    output_path: Path,
    user_rules_path: Path | None = None,
) -> pd.DataFrame:
    sender_summary_df = pd.read_csv(sender_summary_path)
    user_rules = load_user_rules(user_rules_path) if user_rules_path else {}

    ranked_df = rank_cleanup_candidates(sender_summary_df, user_rules=user_rules)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ranked_df.to_csv(output_path, index=False)

    return ranked_df