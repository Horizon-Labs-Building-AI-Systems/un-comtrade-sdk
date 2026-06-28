"""Reference-entry metadata model (R01).

A `ReferenceEntry` represents one row of the reference
list served by M1 (`/files/v1/app/reference/ListofReferences.json`).
Per `008_METADATA_LAYER_SPEC.md` §2.1 each row carries:

- `category` (e.g. `"dataitem"`, `"reporter"`)
- `variable` (human-readable name)
- `description` (long form)
- `fileuri` (upstream URL)
"""

from __future__ import annotations

from dataclasses import dataclass

from ._base import BaseModel


@dataclass(frozen=True)
class ReferenceEntry(BaseModel):
    """R01 row of the reference list.

    Primary key: `(category, variable)` — both fields
    together identify the row. Validation enforces
    non-empty strings and a non-empty fileuri.
    """

    category: str
    variable: str
    description: str
    fileuri: str

    def __post_init__(self) -> None:
        for name in ("category", "variable", "description", "fileuri"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")


__all__ = ["ReferenceEntry"]