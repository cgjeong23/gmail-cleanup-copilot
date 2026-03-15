from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.gmail.client import get_gmail_service
from src.gmail.fetch_messages import get_message, list_message_ids
from src.gmail.parse_headers import parse_message_metadata
from src.analysis.aggregate_senders import aggregate_by_sender
from src.storage.export_csv import save_sender_summary
from src.analysis.rank_candidates import run_ranking_pipeline

def main() -> None:
    query = "newer_than:30d -in:chats"
    max_results = 200
    output_path = Path("data/processed/sender_summary.csv")

    service = get_gmail_service()

    # 1) Fetch + parse messages
    message_ids = list_message_ids(
        service=service,
        query=query,
        max_results=max_results,
    )

    rows = []
    for message_id in message_ids:
        raw_message = get_message(service=service, message_id=message_id)
        rows.append(parse_message_metadata(raw_message))

    # 2) Message-level preview
    '''
    df_messages = pd.DataFrame(rows)
    print("\n=== Message-level records ===")
    if df_messages.empty:
        print("No messages found.")
    else:
        print(
            df_messages[["sender_email", "sender_domain", "subject", "date"]]
            .to_string(index=False)
        )
    '''

    # 3) Sender-level aggregation
    sender_summary = aggregate_by_sender(rows)
    df_senders = pd.DataFrame(sender_summary)

    print("\n=== Sender-level summary ===")
    if df_senders.empty:
        print("No sender summary available.")
    else:
        df_senders = df_senders.sort_values(by="message_count", ascending=False)
        print(
            df_senders[
                [
                    "sender_email",
                    "sender_domain",
                    "message_count",
                    "last_seen",
                    "unsubscribe_count",
                    "sample_subject",
                ]
            ].to_string(index=False)
        )

    # 4) Save CSV
    save_sender_summary(sender_summary, output_path)
    print(f"\nSaved sender summary to: {output_path}")

    # 5) ranking 실행
    run_ranking_pipeline(
        sender_summary_path=Path("data/processed/sender_summary.csv"),
        output_path=Path("data/outputs/cleanup_candidates.csv"),
        user_rules_path=Path("data/user_rules.json"),
    )

if __name__ == "__main__":
    main()