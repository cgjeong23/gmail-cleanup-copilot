from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable


def aggregate_by_sender(messages: Iterable[dict]) -> list[dict]:
    """
    Aggregate message-level records into sender-level summaries.
    """

    senders: dict[str, dict] = {}

    for m in messages:

        sender = m["sender_email"].strip().lower()

        if sender not in senders:
            senders[sender] = {
                "sender_email": sender,
                "sender_domain": m["sender_domain"],
                "message_count": 0,
                "last_seen": m["date"],
                "sample_subject": m["subject"],
                "unsubscribe_count": 0,
            }

        senders[sender]["message_count"] += 1

        if m["has_unsubscribe"]:
            senders[sender]["unsubscribe_count"] += 1

        if m["date"] > senders[sender]["last_seen"]:
            senders[sender]["last_seen"] = m["date"]

    return list(senders.values())