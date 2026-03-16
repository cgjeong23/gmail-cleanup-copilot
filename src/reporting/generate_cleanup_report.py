from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

import pandas as pd
from datetime import datetime

now = datetime.now()
report_month = now.strftime("%B %Y")

@dataclass
class ReportSummary:
    total_senders: int
    cleanup_count: int
    review_count: int
    keep_count: int
    override_count: int
    total_candidate_messages: int


def load_cleanup_candidates(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"cleanup_candidates.csv not found: {path}")

    df = pd.read_csv(path)

    text_cols = [
        "sender_email",
        "sender_domain",
        "last_seen",
        "sample_subject",
        "label",
        "override",
        "reasons",
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    numeric_cols = ["message_count", "unsubscribe_count", "score"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def build_summary(df: pd.DataFrame) -> ReportSummary:
    total_senders = len(df)
    cleanup_count = int((df["label"] == "cleanup").sum()) if "label" in df.columns else 0
    review_count = int((df["label"] == "review").sum()) if "label" in df.columns else 0
    keep_count = int((df["label"] == "keep").sum()) if "label" in df.columns else 0
    override_count = int((df["override"] != "").sum()) if "override" in df.columns else 0

    if "message_count" in df.columns and "label" in df.columns:
        total_candidate_messages = int(
            df.loc[df["label"].isin(["cleanup", "review"]), "message_count"].sum()
        )
    else:
        total_candidate_messages = 0

    return ReportSummary(
        total_senders=total_senders,
        cleanup_count=cleanup_count,
        review_count=review_count,
        keep_count=keep_count,
        override_count=override_count,
        total_candidate_messages=total_candidate_messages,
    )


def get_top_candidates(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    ranked = df.copy()

    if "label" in ranked.columns:
        ranked = ranked[ranked["label"].isin(["cleanup", "review"])]

    sort_cols = [c for c in ["score", "message_count"] if c in ranked.columns]
    if sort_cols:
        ranked = ranked.sort_values(by=sort_cols, ascending=[False, False][: len(sort_cols)])

    return ranked.head(limit).reset_index(drop=True)


def split_reasons(reason_text: str) -> list[str]:
    if not reason_text or not str(reason_text).strip():
        return []
    return [part.strip() for part in str(reason_text).split("|") if part.strip()]


def build_text_report(
    df: pd.DataFrame,
    summary: ReportSummary,
    top_n: int = 10,
) -> str:
    top_df = get_top_candidates(df, limit=top_n)

    lines: list[str] = []
    lines.append(f"Gmail Cleanup Report — {report_month}")
    lines.append("")
    lines.append(f"Total senders analyzed: {summary.total_senders}")
    lines.append(f"Cleanup candidates: {summary.cleanup_count}")
    lines.append(f"Review candidates: {summary.review_count}")
    lines.append(f"Keep: {summary.keep_count}")
    lines.append(f"Overrides applied: {summary.override_count}")
    lines.append(f"Messages in cleanup/review queue: {summary.total_candidate_messages}")
    lines.append("")
    lines.append(f"Top {len(top_df)} ranked candidates:")

    if top_df.empty:
        lines.append("- No ranked candidates found.")
        return "\n".join(lines)

    for _, row in top_df.iterrows():
        sender_email = row.get("sender_email", "")
        score = int(row.get("score", 0))
        label = row.get("label", "")
        message_count = int(row.get("message_count", 0))
        reasons = split_reasons(row.get("reasons", ""))

        lines.append(
            f"- {sender_email} | score={score} | label={label} | messages={message_count}"
        )
        for reason in reasons[:3]:
            lines.append(f"  - {reason}")

    return "\n".join(lines)


def build_html_report(
    df: pd.DataFrame,
    summary: ReportSummary,
    top_n: int = 10,
    title: str = f"Gmail Cleanup Report — {report_month}"
) -> str:
    top_df = get_top_candidates(df, limit=top_n)

    metric_cards = f"""
    <div class="metrics">
      <div class="metric"><div class="metric-value">{summary.total_senders}</div><div class="metric-label">Total Senders</div></div>
      <div class="metric"><div class="metric-value">{summary.cleanup_count}</div><div class="metric-label">Cleanup</div></div>
      <div class="metric"><div class="metric-value">{summary.review_count}</div><div class="metric-label">Review</div></div>
      <div class="metric"><div class="metric-value">{summary.keep_count}</div><div class="metric-label">Keep</div></div>
      <div class="metric"><div class="metric-value">{summary.override_count}</div><div class="metric-label">Overrides</div></div>
    </div>
    """

    if top_df.empty:
        candidate_html = "<p>No ranked cleanup candidates found.</p>"
    else:
        items: list[str] = []
        for _, row in top_df.iterrows():
            sender_email = escape(str(row.get("sender_email", "")))
            sender_domain = escape(str(row.get("sender_domain", "")))
            score = int(row.get("score", 0))
            label = escape(str(row.get("label", "")))
            message_count = int(row.get("message_count", 0))
            last_seen = escape(str(row.get("last_seen", "")))
            subject = escape(str(row.get("sample_subject", "")))
            reasons = split_reasons(str(row.get("reasons", "")))

            reasons_html = "".join(
                f"<li>{escape(reason)}</li>" for reason in reasons[:4]
            ) or "<li>No reasons available.</li>"

            item = f"""
            <div class="candidate">
              <div class="candidate-header">
                <div>
                  <div class="sender">{sender_email}</div>
                  <div class="domain">{sender_domain}</div>
                </div>
                <div class="score-box">
                  <div class="score">{score}</div>
                  <div class="label">{label}</div>
                </div>
              </div>

              <div class="meta">
                <span><strong>Messages:</strong> {message_count}</span>
                <span><strong>Last seen:</strong> {last_seen}</span>
              </div>

              <div class="subject"><strong>Sample subject:</strong> {subject}</div>

              <div class="reasons">
                <strong>Reasons</strong>
                <ul>{reasons_html}</ul>
              </div>
            </div>
            """
            items.append(item)

        candidate_html = "\n".join(items)

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>{escape(title)}</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 40px;
          color: #222;
          line-height: 1.5;
          background: #fafafa;
        }}
        .container {{
          max-width: 980px;
          margin: 0 auto;
          background: white;
          padding: 32px;
          border-radius: 16px;
          box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        h1 {{
          margin-bottom: 8px;
        }}
        .subtitle {{
          color: #666;
          margin-bottom: 24px;
        }}
        .metrics {{
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 12px;
          margin-bottom: 28px;
        }}
        .metric {{
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
          background: #fcfcfc;
          text-align: center;
        }}
        .metric-value {{
          font-size: 28px;
          font-weight: bold;
        }}
        .metric-label {{
          color: #666;
          font-size: 14px;
          margin-top: 4px;
        }}
        .section-title {{
          margin-top: 30px;
          margin-bottom: 14px;
        }}
        .summary-box {{
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
          background: #f8fafc;
          margin-bottom: 24px;
        }}
        .candidate {{
          border: 1px solid #e5e7eb;
          border-radius: 14px;
          padding: 18px;
          margin-bottom: 16px;
          background: #fff;
        }}
        .candidate-header {{
          display: flex;
          justify-content: space-between;
          align-items: start;
          gap: 16px;
        }}
        .sender {{
          font-size: 18px;
          font-weight: bold;
        }}
        .domain {{
          color: #666;
          font-size: 14px;
        }}
        .score-box {{
          text-align: right;
          min-width: 80px;
        }}
        .score {{
          font-size: 28px;
          font-weight: bold;
        }}
        .label {{
          text-transform: uppercase;
          color: #555;
          font-size: 12px;
          letter-spacing: 0.08em;
        }}
        .meta {{
          display: flex;
          gap: 20px;
          margin-top: 12px;
          color: #333;
          font-size: 14px;
          flex-wrap: wrap;
        }}
        .subject {{
          margin-top: 10px;
        }}
        .reasons {{
          margin-top: 12px;
        }}
        ul {{
          margin-top: 8px;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <h1>{escape(title)}</h1>
        <div class="subtitle">Monthly inbox cleanup summary generated from ranked sender activity.</div>

        {metric_cards}

        <div class="summary-box">
          <p><strong>Messages in cleanup/review queue:</strong> {summary.total_candidate_messages}</p>
          <p><strong>Top section includes:</strong> highest-ranked cleanup and review candidates for manual review or automated follow-up.</p>
        </div>

        <h2 class="section-title">Top Ranked Candidates</h2>
        {candidate_html}
      </div>
    </body>
    </html>
    """
    return html.strip()


def save_report_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_report_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def generate_cleanup_reports(
    cleanup_candidates_path: Path,
    text_output_path: Path,
    html_output_path: Path,
    top_n: int = 10,
) -> dict[str, int]:
    df = load_cleanup_candidates(cleanup_candidates_path)
    summary = build_summary(df)

    text_report = build_text_report(df, summary=summary, top_n=top_n)
    html_report = build_html_report(df, summary=summary, top_n=top_n)

    save_report_text(text_output_path, text_report)
    save_report_html(html_output_path, html_report)

    return {
        "total_senders": summary.total_senders,
        "cleanup_count": summary.cleanup_count,
        "review_count": summary.review_count,
        "keep_count": summary.keep_count,
        "override_count": summary.override_count,
        "total_candidate_messages": summary.total_candidate_messages,
    }