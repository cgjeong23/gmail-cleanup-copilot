from __future__ import annotations

from pathlib import Path
import sys
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.analysis.rank_candidates import run_ranking_pipeline
from src.reporting.generate_cleanup_report import generate_cleanup_reports


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    sender_summary_path = project_root / "data" / "processed" / "sender_summary.csv"
    cleanup_candidates_path = project_root / "data" / "outputs" / "cleanup_candidates.csv"
    user_rules_path = project_root / "data" / "user_rules.json"

    report_text_path = project_root / "data" / "reports" / "cleanup_report.txt"
    report_html_path = project_root / "data" / "reports" / "cleanup_report.html"

    run_ranking_pipeline(
        sender_summary_path=sender_summary_path,
        output_path=cleanup_candidates_path,
        user_rules_path=user_rules_path,
    )

    stats = generate_cleanup_reports(
        cleanup_candidates_path=cleanup_candidates_path,
        text_output_path=report_text_path,
        html_output_path=report_html_path,
        top_n=10,
    )

    print("Cleanup pipeline completed.")
    print(stats)
    print(f"Saved text report to: {report_text_path}")
    print(f"Saved HTML report to: {report_html_path}")


if __name__ == "__main__":
    main()