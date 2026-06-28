"""DataItem metadata model.

A `DataItem` represents a column / variable in the
upstream reference catalogue (e.g. `datasetCode`,
`reporterCode`, `flowCode`). It is the metadata-layer
analogue of E15 / R15 from `008_METADATA_LAYER_SPEC.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._base import BaseModel


@dataclass(frozen=True)
class DataItem(BaseModel):
    """A single reference-catalogue column / variable.

    Primary key: `data_item` (string). Validation per the
    upstream JSON shape (`dataItem` field).
    """

    data_item: str
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.data_item, str) or not self.data_item.strip():
            raise ValueError("data_item must be a non-empty string")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description must be a non-empty string")


__all__ = ["DataItem"]