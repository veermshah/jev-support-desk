"""A keyword rule router, standing in for the hand-written routing rules most support desks start with.

It is the baseline the Jev router is evaluated against, and the source of `assigned_queue` when a ticket
arrives without one.
"""

import re

from jev_support_desk.tickets import Ticket

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("billing", re.compile(r"\b(invoice|charged?|refund|billing|payment|credit card|receipt)\b", re.I)),
    ("auth", re.compile(r"\b(401|403|unauthori[sz]ed|api key|bearer|forbidden)\b", re.I)),
    ("request_validation", re.compile(r"\b(422|unprocessable|validation|invalid request)\b", re.I)),
    ("rate_limits_capacity", re.compile(r"\b(429|529|rate limit|overloaded|throttl)", re.I)),
    ("bug_or_outage", re.compile(r"\b(500|502|503|outage|down|5xx)\b", re.I)),
    ("sdk_integration", re.compile(r"\b(sdk|pip|npm|import|langchain|openrouter|gateway)\b", re.I)),
    ("account_access", re.compile(r"\b(login|log in|sso|waitlist|console|password)\b", re.I)),
    ("model_behavior", re.compile(r"\b(wrong answer|confidence|probabilit|calibrat)", re.I)),
]

FALLBACK_QUEUE = "product_question"


def legacy_route(ticket: Ticket) -> str:
    text = f"{ticket.subject}\n{ticket.body}"
    for queue, pattern in RULES:
        if pattern.search(text):
            return queue
    return FALLBACK_QUEUE
