# src/analysis/scoring_rules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import re


DEFAULT_MARKETING_KEYWORDS = [
    "sale",
    "discount",
    "offer",
    "promo",
    "promotion",
    "deal",
    "save",
    "off",
    "coupon",
    "limited time",
    "last chance",
    "shop",
    "buy now",
    "special",
    "exclusive",
    "ticket",
    "travel",
    "booking",
    "newsletter",
    "digest",
    "update",
]

DEFAULT_PROTECTED_DOMAINS = {
    "accounts.google.com",
    "google.com",
    "mail.google.com",
    "github.com",
    "linkedin.com",
    "university.edu",
}

NOREPLY_PATTERNS = [
    r"^no-?reply@",
    r"^donotreply@",
    r"^do-?not-?reply@",
    r"^notifications?@",
    r"^updates?@",
]


@dataclass
class ScoreResult:
    sender_email: str
    sender_domain: str
    score: int
    label: str
    reasons: List[str]
    override: str | None = None


def normalize_rule_values(values: List[str] | None) -> set[str]:
    if not values:
        return set()
    return {str(v).strip().lower() for v in values if str(v).strip()}


def load_rule_sets(user_rules: Dict[str, Any] | None) -> Dict[str, set[str]]:
    user_rules = user_rules or {}

    always_cleanup = normalize_rule_values(user_rules.get("always_cleanup"))
    always_keep = normalize_rule_values(user_rules.get("always_keep"))
    protected_domains = normalize_rule_values(user_rules.get("protected_domains"))

    return {
        "always_cleanup": always_cleanup,
        "always_keep": always_keep,
        "protected_domains": protected_domains,
    }


def contains_marketing_keyword(subject: str, keywords: List[str]) -> List[str]:
    subject_l = (subject or "").lower()
    hits = [kw for kw in keywords if kw in subject_l]
    return hits


def matches_noreply(sender_email: str) -> bool:
    sender_email = (sender_email or "").lower().strip()
    return any(re.search(pattern, sender_email) for pattern in NOREPLY_PATTERNS)


def domain_matches(target: str, candidates: set[str]) -> bool:
    """
    Supports exact domain match or subdomain match.
    Example:
      target=mail.uber.com, candidate=uber.com -> True
    """
    target = (target or "").lower().strip()
    for c in candidates:
        if target == c or target.endswith(f".{c}"):
            return True
    return False


def email_or_domain_matches(sender_email: str, sender_domain: str, candidates: set[str]) -> bool:
    sender_email = (sender_email or "").lower().strip()
    sender_domain = (sender_domain or "").lower().strip()

    for c in candidates:
        if c == sender_email:
            return True
        if sender_domain == c or sender_domain.endswith(f".{c}"):
            return True
    return False


def label_from_score(score: int) -> str:
    if score >= 7:
        return "cleanup"
    if score >= 4:
        return "review"
    return "keep"


def score_sender(
    row: Dict[str, Any],
    user_rules: Dict[str, Any] | None = None,
    marketing_keywords: List[str] | None = None,
    protected_domains: set[str] | None = None,
) -> ScoreResult:
    """
    Expected row keys:
      - sender_email
      - sender_domain
      - message_count
      - last_seen
      - sample_subject
      - unsubscribe_count
    """
    sender_email = str(row.get("sender_email", "")).strip().lower()
    sender_domain = str(row.get("sender_domain", "")).strip().lower()
    message_count = int(row.get("message_count", 0) or 0)
    unsubscribe_count = int(row.get("unsubscribe_count", 0) or 0)
    sample_subject = str(row.get("sample_subject", "") or "").strip()

    keywords = marketing_keywords or DEFAULT_MARKETING_KEYWORDS
    base_protected = set(DEFAULT_PROTECTED_DOMAINS)
    if protected_domains:
        base_protected.update({d.lower() for d in protected_domains})

    rules = load_rule_sets(user_rules)

    # Merge user-provided protected domains too
    base_protected.update(rules["protected_domains"])

    reasons: List[str] = []

    # ---------------------------
    # 1) Override rules first
    # ---------------------------
    if email_or_domain_matches(sender_email, sender_domain, rules["always_keep"]):
        reasons.append("matched always_keep rule")
        return ScoreResult(
            sender_email=sender_email,
            sender_domain=sender_domain,
            score=0,
            label="keep",
            reasons=reasons,
            override="always_keep",
        )

    if email_or_domain_matches(sender_email, sender_domain, rules["always_cleanup"]):
        reasons.append("matched always_cleanup rule")
        return ScoreResult(
            sender_email=sender_email,
            sender_domain=sender_domain,
            score=10,
            label="cleanup",
            reasons=reasons,
            override="always_cleanup",
        )

    # ---------------------------
    # 2) Protected domain check
    # ---------------------------
    if domain_matches(sender_domain, base_protected):
        reasons.append("protected domain")
        return ScoreResult(
            sender_email=sender_email,
            sender_domain=sender_domain,
            score=0,
            label="keep",
            reasons=reasons,
            override="protected_domain",
        )

    # ---------------------------
    # 3) Rule-based scoring
    # ---------------------------
    score = 0

    # message frequency
    if message_count >= 20:
        score += 3
        reasons.append("very high email frequency")
    elif message_count >= 10:
        score += 2
        reasons.append("high email frequency")
    elif message_count >= 5:
        score += 1
        reasons.append("moderate email frequency")

    # unsubscribe signal
    if unsubscribe_count >= 2:
        score += 3
        reasons.append("unsubscribe header detected repeatedly")
    elif unsubscribe_count >= 1:
        score += 2
        reasons.append("unsubscribe header detected")

    # marketing subject signal
    keyword_hits = contains_marketing_keyword(sample_subject, keywords)
    if len(keyword_hits) >= 2:
        score += 2
        reasons.append(f"multiple marketing keywords in subject: {', '.join(keyword_hits[:3])}")
    elif len(keyword_hits) == 1:
        score += 1
        reasons.append(f"marketing keyword in subject: {keyword_hits[0]}")

    # noreply-ish sender signal
    if matches_noreply(sender_email):
        score += 2
        reasons.append("noreply-style sender pattern")

    # domain heuristics
    marketing_like_domains = [
        "newsletter",
        "news",
        "mail",
        "offers",
        "deals",
        "promo",
    ]
    if any(token in sender_domain for token in marketing_like_domains):
        score += 1
        reasons.append("marketing-like sender domain pattern")

    # safety cap
    score = max(0, min(score, 10))

    label = label_from_score(score)

    if not reasons:
        reasons.append("no strong cleanup signals detected")

    return ScoreResult(
        sender_email=sender_email,
        sender_domain=sender_domain,
        score=score,
        label=label,
        reasons=reasons,
        override=None,
    )