"""Convert TaskUpdateRequest into Marvin's setters format for /doc/update."""

import time

from .models import TaskUpdateRequest

# Map snake_case model fields to Marvin camelCase API keys
_FIELD_MAP: dict[str, str] = {
    "title": "title",
    "due_date": "dueDate",
    "scheduled_date": "day",
    "note": "note",
    "label_ids": "labelIds",
    "priority": "priority",
    "parent_id": "parentId",
    "is_starred": "isStarred",
    "is_frogged": "isFrogged",
    "time_estimate": "timeEstimate",
    "backburner": "backburner",
}

# Fields for which Marvin also expects a fieldUpdates.<key> timestamp entry
_TRACKED_FIELDS: set[str] = {
    "dueDate",
    "day",
    "timeEstimate",
    "labelIds",
    "priority",
    "isStarred",
    "isFrogged",
    "backburner",
}


def build_setters(update: TaskUpdateRequest) -> list[dict]:
    """Convert a TaskUpdateRequest into Marvin's setters array format.

    Returns a list of {"key": ..., "val": ...} dicts ready to pass to /doc/update.
    Only includes fields that are not None. Appends fieldUpdates.<key> timestamp
    entries for tracked fields, and always appends updatedAt.

    Timestamps are in milliseconds since epoch (UTC).
    """
    now_ms = int(time.time() * 1000)
    setters: list[dict] = []

    for model_field, marvin_key in _FIELD_MAP.items():
        value = getattr(update, model_field)
        if value is None:
            continue
        # Convert time_estimate from minutes to milliseconds for Marvin
        if model_field == "time_estimate":
            value = value * 60 * 1000
        setters.append({"key": marvin_key, "val": value})
        if marvin_key in _TRACKED_FIELDS:
            setters.append({"key": f"fieldUpdates.{marvin_key}", "val": now_ms})

    setters.append({"key": "updatedAt", "val": now_ms})
    return setters
