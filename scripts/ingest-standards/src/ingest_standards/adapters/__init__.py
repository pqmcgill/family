"""Source-specific adapters that parse external data into StandardNodes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from ingest_standards.models import StandardNode


class Adapter(ABC):
    """Base class for source adapters.

    Each adapter knows how to parse one external format and yield
    canonical StandardNode objects.
    """

    @abstractmethod
    def fetch(self) -> Iterator[StandardNode]:
        """Fetch and parse standards from the source.

        Yields StandardNode objects in document order.
        """
        ...
