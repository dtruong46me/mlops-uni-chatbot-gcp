from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Document:
    """A lightweight container for a text chunk and its metadata."""

    text: str
    metadata: Dict[str, Any]
