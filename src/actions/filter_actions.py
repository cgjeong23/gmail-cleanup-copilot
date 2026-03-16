# src/filter_actions.py
from __future__ import annotations

from typing import Any


def build_sender_query(
    sender_email: str,
    newer_than_days: int | None = None,
    exclude_chats: bool = True,
    include_spam_trash: bool = False,
) -> str:
    """
    Build a Gmail search query for a specific sender email.
    Example:
        from:noreply@redditmail.com newer_than:30d -in:chats
    """
    parts: list[str] = [f"from:{sender_email.strip()}"]

    if newer_than_days is not None:
        parts.append(f"newer_than:{newer_than_days}d")

    if exclude_chats:
        parts.append("-in:chats")

    # note:
    # include_spam_trash is not part of q string;
    # it is used as a separate API parameter in messages.list
    return " ".join(parts)


def list_message_ids_by_sender(
    service: Any,
    sender_email: str,
    newer_than_days: int | None = 30,
    include_spam_trash: bool = False,
    max_results: int = 500,
) -> list[str]:
    """
    Return Gmail message IDs matching a sender email.
    Uses Gmail messages.list with q=from:...
    """
    query = build_sender_query(
        sender_email=sender_email,
        newer_than_days=newer_than_days,
        exclude_chats=True,
        include_spam_trash=include_spam_trash,
    )

    message_ids: list[str] = []
    page_token: str | None = None

    while True:
        request = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                includeSpamTrash=include_spam_trash,
                maxResults=min(max_results, 500),
                pageToken=page_token,
            )
        )

        response = request.execute()
        messages = response.get("messages", [])

        for msg in messages:
            msg_id = msg.get("id")
            if msg_id:
                message_ids.append(msg_id)
                if len(message_ids) >= max_results:
                    return message_ids

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return message_ids


def get_message_metadata_preview(
    service: Any,
    message_id: str,
) -> dict:
    """
    Fetch lightweight metadata preview for a single message.
    """
    response = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        )
        .execute()
    )

    headers = response.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers if "name" in h and "value" in h}

    return {
        "id": message_id,
        "from": header_map.get("from", ""),
        "subject": header_map.get("subject", ""),
        "date": header_map.get("date", ""),
        "thread_id": response.get("threadId", ""),
    }


def preview_messages_by_sender(
    service: Any,
    sender_email: str,
    newer_than_days: int | None = 30,
    include_spam_trash: bool = False,
    preview_limit: int = 5,
) -> list[dict]:
    """
    Find messages for a sender, then return lightweight previews
    for the first few matches.
    """
    message_ids = list_message_ids_by_sender(
        service=service,
        sender_email=sender_email,
        newer_than_days=newer_than_days,
        include_spam_trash=include_spam_trash,
        max_results=preview_limit,
    )

    previews: list[dict] = []
    for message_id in message_ids:
        previews.append(get_message_metadata_preview(service, message_id))

    return previews