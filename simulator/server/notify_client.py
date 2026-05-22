"""Deprecated simulator notification hook.

Backend ingest APIs now write data and publish SSE events. The simulator keeps
this no-op function only so older route code can call notify(...) without
creating duplicate backend events.
"""


def notify(entity: str, action: str, payload: dict) -> None:
    return None
