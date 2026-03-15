from __future__ import annotations

import re
from email.utils import parseaddr
from typing import Any


HEADER_FROM = "From"
HEADER_SUBJECT = "Subject"
HEADER_DATE = "Date"
HEADER_LIST_UNSUBSCRIBE = "List-Unsubscribe"


def _header_map(message: dict[str, Any]) -> dict[str, str]:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    return {
        h.get("name", ""): h.get("value", "")
        for h in headers
        if h.get("name")
    }


def _extract_domain(email_address: str) -> str:
    if "@" not in email_address:
        return ""
    return email_address.split("@", 1)[1].lower().strip()


def parse_message_metadata(message: dict[str, Any]) -> dict[str, Any]:
    headers = _header_map(message)

    from_raw = headers.get(HEADER_FROM, "")
    subject = headers.get(HEADER_SUBJECT, "")
    date = headers.get(HEADER_DATE, "")
    unsubscribe = headers.get(HEADER_LIST_UNSUBSCRIBE, "")

    _, sender_email = parseaddr(from_raw)
    sender_email = sender_email.lower().strip()
    sender_domain = _extract_domain(sender_email)

    return {
        "message_id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "from_raw": from_raw,
        "sender_email": sender_email,
        "sender_domain": sender_domain,
        "subject": subject,
        "date": date,
        "snippet": message.get("snippet", ""),
        "label_ids": message.get("labelIds", []),
        "has_unsubscribe": bool(unsubscribe),
    }