"""Pydantic request models for Amazing Marvin MCP operations."""

from pydantic import BaseModel, Field


class TaskUpdateRequest(BaseModel):
    """Friendly task update — converted to Marvin setters format internally.

    Pass only the fields you want to change; omitted fields (None) are left untouched.

    Limitation: None means "leave unchanged", so there is currently no way to clear a field
    (e.g. remove a due date) via this model. Use update_document with explicit setters instead.
    """

    item_id: str
    title: str | None = None
    due_date: str | None = Field(default=None, description="YYYY-MM-DD")
    scheduled_date: str | None = Field(
        default=None, description="YYYY-MM-DD (maps to 'day' in Marvin)"
    )
    note: str | None = None
    label_ids: list[str] | None = None
    priority: str | None = None
    parent_id: str | None = None
    is_starred: bool | None = None
    is_frogged: bool | None = None
    time_estimate: int | None = Field(default=None, description="Time estimate in minutes")
    backburner: bool | None = None
