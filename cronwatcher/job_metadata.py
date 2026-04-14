"""Job metadata store — attach arbitrary key/value pairs to jobs.

Distinct from labels (single-value) and annotations (string-value notes);
metadata holds structured values (str, int, float, bool) useful for
runtime configuration or reporting enrichment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

# Supported scalar types for metadata values
MetaValue = Union[str, int, float, bool]


@dataclass
class MetadataIndex:
    """In-memory index of metadata entries keyed by job name."""

    _data: Dict[str, Dict[str, MetaValue]] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def set(self, job_name: str, key: str, value: MetaValue) -> None:
        """Set *key* to *value* for *job_name*, overwriting any existing entry."""
        if not job_name:
            raise ValueError("job_name must not be empty")
        if not key:
            raise ValueError("key must not be empty")
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(
                f"Metadata values must be str, int, float, or bool; got {type(value).__name__!r}"
            )
        self._data.setdefault(job_name, {})[key] = value

    def delete(self, job_name: str, key: str) -> bool:
        """Remove *key* from *job_name*.  Returns True if the key existed."""
        entry = self._data.get(job_name, {})
        if key in entry:
            del entry[key]
            if not entry:
                del self._data[job_name]
            return True
        return False

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get(self, job_name: str, key: str, default: Optional[MetaValue] = None) -> Optional[MetaValue]:
        """Return the value for *key* on *job_name*, or *default* if absent."""
        return self._data.get(job_name, {}).get(key, default)

    def all_for_job(self, job_name: str) -> Dict[str, MetaValue]:
        """Return a copy of all metadata for *job_name*."""
        return dict(self._data.get(job_name, {}))

    def jobs_with_key(self, key: str) -> List[str]:
        """Return sorted list of job names that have *key* set."""
        return sorted(name for name, meta in self._data.items() if key in meta)

    def jobs_with_value(self, key: str, value: MetaValue) -> List[str]:
        """Return sorted list of job names where *key* equals *value*."""
        return sorted(
            name for name, meta in self._data.items() if meta.get(key) == value
        )

    def all_keys(self) -> List[str]:
        """Return a sorted, deduplicated list of every key in use."""
        keys: set[str] = set()
        for meta in self._data.values():
            keys.update(meta.keys())
        return sorted(keys)

    def __iter__(self) -> Iterator[str]:
        """Iterate over job names that have at least one metadata entry."""
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Union[str, Path]) -> None:
        """Persist the index to *path* as JSON."""
        Path(path).write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Union[str, Path]) -> "MetadataIndex": 
        """Load an index from *path*.  Returns an empty index if the file is absent."""
        p = Path(path)
        instance = cls()
        if p.exists():
            raw: Any = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for job_name, meta in raw.items():
                    if isinstance(meta, dict):
                        for k, v in meta.items():
                            if isinstance(v, (str, int, float, bool)):
                                instance._data.setdefault(job_name, {})[k] = v
        return instance
