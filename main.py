from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.gmail.client import get_gmail_service
from src.gmail.fetch_messages import get_message, list_message_ids
from src.gmail.parse_headers import parse_message_metadata
from src.analysis.aggregate_senders import aggregate_by_sender
from src.storage.export_csv import save_sender_summary


def main() -> None:
    service = get_gmail_service()

    message_ids = list_message_ids(
        service=service,
        query="newer_than:30d -in:chats",
        max_results=200,
    )

    rows = []
    for message_id in message_ids:
        raw_message = get_message(service=service, message_id=message_id)
        parsed = parse_message_metadata(raw_message)
        rows.append(parsed)

    # 1) message-level 확인용 출력
    df_messages = pd.DataFrame(rows)
    print("\n=== Message-level records ===")
    print(
        df_messages[["sender_email", "sender_domain", "subject", "date"]]
        .to_string(index=False)
    )

    # 2) sender-level 집계
    sender_summary = aggregate_by_sender(rows)

    # 3) sender-level 출력
    df_senders = pd.DataFrame(sender_summary)

    if not df_senders.empty:
        df_senders = df_senders.sort_values(
            by="message_count",
            ascending=False,
        )

        print("\n=== Sender-level summary ===")
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

    # 4) CSV 저장
    save_sender_summary(
        sender_summary,
        Path("data/processed/sender_summary.csv"),
    )


if __name__ == "__main__":
    main()