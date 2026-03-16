# src/trash_actions.py
from __future__ import annotations

from typing import Any


def move_messages_to_trash(
    service: Any,
    message_ids: list[str],
) -> dict:
    """
    Move a list of Gmail message IDs to trash.

    Returns summary stats.
    """

    trashed = 0
    failed: list[str] = []

    for message_id in message_ids:
        try:
            (
                service.users()
                .messages()
                .trash(
                    userId="me",
                    id=message_id,
                )
                .execute()
            )

            trashed += 1

        except Exception:
            failed.append(message_id)

    return {
        "requested": len(message_ids),
        "trashed": trashed,
        "failed": len(failed),
        "failed_ids": failed,
    }