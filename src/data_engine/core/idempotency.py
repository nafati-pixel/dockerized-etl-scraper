from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence


def make_idempotency_key(data: Mapping[str, Any], key_fields: Sequence[str]) -> str:
    """
    Deterministic key from the fields that actually identify a record in
    the DESTINATION (e.g. ("order_id",)) - not the whole record, so two
    extractions of the same logical row produce the SAME key even if
    unrelated fields (e.g. a "last_seen" timestamp) differ between them.

    key_fields is passed in by the caller, not hardcoded here - what
    identifies a record is a property of the destination table, which
    this generic module has no business assuming.

    Raises KeyError loudly if a key field is missing - a silently wrong
    idempotency key (e.g. falling back to str(None)) risks silent
    duplicate rows or accidental overwrites of unrelated records, which
    is far worse than a crash.
    """
    try:
        parts = [str(data[field]) for field in key_fields]
    except KeyError as exc:
        raise KeyError(
            f"Cannot build idempotency key: field {exc} missing from "
            f"record. Expected key_fields={list(key_fields)}."
        ) from exc

    raw = "|".join(parts)
    # sha256, not Python's built-in hash() - hash() is salted per-process
    # for security reasons and is NOT stable across processes/runs, which
    # would make keys computed by the original run and a later replay
    # run (different process) disagree.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
