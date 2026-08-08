from __future__ import annotations

import re


def normalize_time(text: str, current_turn: int | None = None) -> int | None:
    match = re.search(r"\bturn\s+(\d+)\b", text.casefold())
    if match:
        return int(match.group(1))
    match = re.search(r"\b(20\d\d)-(\d\d)-(\d\d)\b", text)
    if match:
        return int("".join(match.groups()))
    if text.casefold().strip() in {"now", "current"}:
        return current_turn
    return None
