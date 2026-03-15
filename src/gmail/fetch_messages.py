from __future__ import annotations

from typing import Any

from googleapiclient.discovery import Resource


def list_message_ids(
    service: Resource,
    user_id: str = "me",
    query: str = "newer_than:30d",
    max_results: int = 20,
) -> list[str]:
    """
    Return a list of Gmail message IDs matching the query.
    """
    response = (
        service.users()
        .messages()
        .list(
            userId=user_id,
            q=query,
            maxResults=max_results,
        )
        .execute()
    )

    messages = response.get("messages", [])
    return [m["id"] for m in messages]


def get_message(
    service: Resource,
    message_id: str,
    user_id: str = "me",
    format_: str = "metadata",
) -> dict[str, Any]:
    """
    Fetch a single Gmail message in metadata format.
    """
    return (
        service.users()
        .messages()
        .get(
            userId=user_id,
            id=message_id,
            format=format_,
        )
        .execute()
    )