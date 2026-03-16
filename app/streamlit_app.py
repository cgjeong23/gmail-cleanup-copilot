from __future__ import annotations

from pathlib import Path
import sys
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

import pandas as pd
import streamlit as st
from src.gmail.client import get_gmail_service
from src.actions.filter_actions import (
    list_message_ids_by_sender,
    preview_messages_by_sender,
)
from src.actions.trash_actions import move_messages_to_trash
from src.storage.decisions import append_action_log

DATA_PATH = Path("data/outputs/cleanup_candidates.csv")
ACTION_LOG_PATH = Path("data/logs/action_logs.jsonl")

def load_candidates(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)

    # Defensive cleanup
    for col in [
        "sender_email",
        "sender_domain",
        "last_seen",
        "sample_subject",
        "label",
        "override",
        "reasons",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)

    for col in ["message_count", "unsubscribe_count", "score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def split_reasons(reason_text: str) -> list[str]:
    if not reason_text or not str(reason_text).strip():
        return []

    parts = [p.strip() for p in str(reason_text).split("|")]
    return [p for p in parts if p]


def render_metrics(df: pd.DataFrame) -> None:
    total = len(df)
    cleanup_count = int((df["label"] == "cleanup").sum()) if "label" in df.columns else 0
    review_count = int((df["label"] == "review").sum()) if "label" in df.columns else 0
    keep_count = int((df["label"] == "keep").sum()) if "label" in df.columns else 0
    override_count = int((df["override"].fillna("") != "").sum()) if "override" in df.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Senders", total)
    c2.metric("Cleanup", cleanup_count)
    c3.metric("Review", review_count)
    c4.metric("Keep", keep_count)
    c5.metric("Overrides", override_count)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")

    label_options = ["all"] + sorted(df["label"].dropna().unique().tolist()) if "label" in df.columns else ["all"]
    selected_label = st.sidebar.selectbox("Label", label_options, index=0)

    domain_options = ["all"] + sorted(df["sender_domain"].dropna().unique().tolist()) if "sender_domain" in df.columns else ["all"]
    selected_domain = st.sidebar.selectbox("Domain", domain_options, index=0)

    min_score = 0
    max_score = int(df["score"].max()) if "score" in df.columns and not df.empty else 10
    selected_score = st.sidebar.slider("Minimum score", min_value=0, max_value=max_score if max_score > 0 else 10, value=0)

    search_text = st.sidebar.text_input("Search sender or subject")

    filtered = df.copy()

    if selected_label != "all":
        filtered = filtered[filtered["label"] == selected_label]

    if selected_domain != "all":
        filtered = filtered[filtered["sender_domain"] == selected_domain]

    if "score" in filtered.columns:
        filtered = filtered[filtered["score"] >= selected_score]

    if search_text.strip():
        q = search_text.strip().lower()
        filtered = filtered[
            filtered["sender_email"].str.lower().str.contains(q, na=False)
            | filtered["sender_domain"].str.lower().str.contains(q, na=False)
            | filtered["sample_subject"].str.lower().str.contains(q, na=False)
        ]

    return filtered


def render_table(df: pd.DataFrame, title: str) -> None:
    st.subheader(title)

    if df.empty:
        st.info("No senders found for this view.")
        return

    display_cols = [
        "sender_email",
        "sender_domain",
        "score",
        "label",
        "message_count",
        "unsubscribe_count",
        "override",
        "reasons",
        "sample_subject",
        "last_seen",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True,
    )


def render_sender_detail(df: pd.DataFrame) -> None:
    st.subheader("Sender Detail")

    if df.empty:
        st.info("No sender available.")
        return

    sender_list = df["sender_email"].dropna().tolist()
    selected_sender = st.selectbox("Select a sender", sender_list)

    row = df[df["sender_email"] == selected_sender].iloc[0]

    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"### {row['sender_email']}")
        st.write(f"**Domain:** {row.get('sender_domain', '')}")
        st.write(f"**Sample subject:** {row.get('sample_subject', '')}")
        st.write(f"**Last seen:** {row.get('last_seen', '')}")

    with right:
        st.metric("Score", int(row.get("score", 0)))
        st.write(f"**Label:** {row.get('label', '')}")
        override_value = row.get("override", "")
        st.write(f"**Override:** {override_value if override_value else '-'}")
        st.write(f"**Message count:** {int(row.get('message_count', 0))}")
        st.write(f"**Unsubscribe count:** {int(row.get('unsubscribe_count', 0))}")

    reasons = split_reasons(row.get("reasons", ""))

    st.markdown("**Reasons**")
    if reasons:
        for reason in reasons:
            st.markdown(f"- {reason}")
    else:
        st.write("No reasons available.")

def render_trash_action_panel(df: pd.DataFrame) -> None:
    st.subheader("Approved Cleanup Action")

    if df.empty:
        st.info("No sender available for actions.")
        return

    sender_list = df["sender_email"].dropna().tolist()
    selected_sender = st.selectbox(
        "Select a sender to review for trash action",
        sender_list,
        key="trash_sender_select",
    )

    newer_than_days = st.number_input(
        "Search window (days)",
        min_value=1,
        max_value=365,
        value=30,
        step=1,
    )

    preview_limit = st.slider(
        "Preview message count",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
    )

    if st.button("Preview affected emails", key="preview_trash_action"):
        try:
            service = get_gmail_service()

            message_ids = list_message_ids_by_sender(
                service=service,
                sender_email=selected_sender,
                newer_than_days=int(newer_than_days),
                include_spam_trash=False,
                max_results=500,
            )

            previews = preview_messages_by_sender(
                service=service,
                sender_email=selected_sender,
                newer_than_days=int(newer_than_days),
                include_spam_trash=False,
                preview_limit=int(preview_limit),
            )

            st.session_state["trash_selected_sender"] = selected_sender
            st.session_state["trash_message_ids"] = message_ids
            st.session_state["trash_previews"] = previews
            st.session_state["trash_search_window_days"] = int(newer_than_days)

        except Exception as e:
            st.error(f"Preview failed: {e}")

    selected_sender_state = st.session_state.get("trash_selected_sender")
    message_ids_state = st.session_state.get("trash_message_ids", [])
    previews_state = st.session_state.get("trash_previews", [])
    search_window_days_state = st.session_state.get("trash_search_window_days", 30)

    if selected_sender_state:
        st.markdown(f"**Selected sender:** {selected_sender_state}")
        st.write(f"**Matched messages:** {len(message_ids_state)}")

        if previews_state:
            preview_df = pd.DataFrame(previews_state)
            preview_cols = [c for c in ["id", "subject", "date"] if c in preview_df.columns]

            st.markdown("**Recent matching messages**")
            st.dataframe(
                preview_df[preview_cols],
                use_container_width=True,
                hide_index=True,
            )

        confirm = st.checkbox(
            f"I confirm I want to move messages from {selected_sender_state} to trash",
            key="trash_confirm_checkbox",
        )

        max_allowed = max(1, len(message_ids_state)) if message_ids_state else 1
        default_value = min(10, max_allowed)

        execute_limit = st.number_input(
            "Max messages to trash this run",
            min_value=1,
            max_value=max_allowed,
            value=default_value,
            step=1,
        )

        if st.button("Move to Trash", key="execute_trash_action"):
            if not confirm:
                st.warning("Please confirm before executing the trash action.")
                return

            if not message_ids_state:
                st.warning("No messages matched this sender.")
                return

            try:
                service = get_gmail_service()

                target_ids = message_ids_state[: int(execute_limit)]

                result = move_messages_to_trash(
                    service=service,
                    message_ids=target_ids,
                )

                append_action_log(
                    ACTION_LOG_PATH,
                    {
                        "action": "trash_sender_messages",
                        "sender_email": selected_sender_state,
                        "requested_count": result["requested"],
                        "trashed_count": result["trashed"],
                        "failed_count": result["failed"],
                        "failed_ids": result["failed_ids"],
                        "search_window_days": int(search_window_days_state),
                    },
                )

                st.success(
                    f"Moved {result['trashed']} / {result['requested']} messages to trash."
                )

                if result["failed"] > 0:
                    st.error(f"Failed to trash {result['failed']} messages.")

            except Exception as e:
                st.error(f"Trash action failed: {e}")

def main() -> None:
    st.set_page_config(
        page_title="Gmail Cleanup Copilot",
        page_icon="📬",
        layout="wide",
    )

    st.title("📬 Gmail Cleanup Copilot")
    st.caption("Human-in-the-loop cleanup recommendations from sender-level Gmail activity.")

    df = load_candidates(DATA_PATH)

    if df.empty:
        st.warning("No cleanup_candidates.csv found. Run the ranking pipeline first.")
        st.code("python main.py")
        return

    # sort for stable default view
    sort_cols = [c for c in ["score", "message_count"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=[False, False]).reset_index(drop=True)

    render_metrics(df)

    filtered_df = apply_filters(df)

    tab1, tab2, tab3 = st.tabs(["Cleanup Candidates", "Review Queue", "All Senders"])

    with tab1:
        cleanup_df = filtered_df[filtered_df["label"] == "cleanup"] if "label" in filtered_df.columns else filtered_df
        render_table(cleanup_df, "Top Cleanup Candidates")

    with tab2:
        review_df = filtered_df[filtered_df["label"] == "review"] if "label" in filtered_df.columns else pd.DataFrame()
        render_table(review_df, "Review Queue")

    with tab3:
        render_table(filtered_df, "All Ranked Senders")

    st.divider()
    render_sender_detail(filtered_df)

    st.divider()
    render_trash_action_panel(filtered_df)


if __name__ == "__main__":
    main()