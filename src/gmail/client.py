from __future__ import annotations

from googleapiclient.discovery import build
from googleapiclient.discovery import Resource

from src.auth.gmail_auth import get_credentials


def get_gmail_service() -> Resource:
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    return service