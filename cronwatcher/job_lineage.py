"""Track job lineage — upstream/downstream data dependencies between jobs.

This is distinct from execution dependencies (job_dependencies.py) which
control run order. Lineage tracks data flow: which jobs produce outputs
consumed by other jobs, useful for impact analysis and audit trails.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class LineageEdge:
    """A directed data-flow edge from producer to consumer."""

    producer: str  # job name that produces the data
    consumer: str  # job name that consumes the data
    label: Optional[str] = None  # optional description, e.g. "daily_sales_csv"

    def to_dict(self) -> dict:
        return {
            "producer": self.producer,
            "consumer": self.consumer,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LineageEdge":
        return cls(
            producer=d["producer"],
            consumer=d["consumer"],
            label=d.get("label"),
        )

    def __repr__(self) -> str:
        lbl = f" [{self.label}]" if self.label else ""
        return f"LineageEdge({self.producer!r} -> {self.consumer!r}{lbl})"


class LineageError(Exception):
    """Raised when a lineage operation would create an invalid graph state."""


class LineageGraph:
    """Directed graph of data-flow relationships between jobs."""

    def __init__(self, state_file: Optional[Path] = None) -> None:
        self._state_file = state_file
        # producer -> list of edges leaving it
        self._edges: List[LineageEdge] = []
        if state_file:
            self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._state_file and self._state_file.exists():
            raw = json.loads(self._state_file.read_text())
            self._edges = [LineageEdge.from_dict(e) for e in raw.get("edges", [])]

    def _save(self) -> None:
        if self._state_file:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"edges": [e.to_dict() for e in self._edges]}
            self._state_file.write_text(json.dumps(payload, indent=2))

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_edge(self, producer: str, consumer: str, label: Optional[str] = None) -> LineageEdge:
        """Record that *consumer* reads data produced by *producer*."""
        if producer == consumer:
            raise LineageError(f"Job {producer!r} cannot be its own lineage dependency.")
        # Prevent duplicate edges (same producer+consumer pair)
        for existing in self._edges:
            if existing.producer == producer and existing.consumer == consumer:
                raise LineageError(
                    f"Lineage edge {producer!r} -> {consumer!r} already exists."
                )
        edge = LineageEdge(producer=producer, consumer=consumer, label=label)
        self._edges.append(edge)
        self._save()
        return edge

    def remove_edge(self, producer: str, consumer: str) -> bool:
        """Remove a lineage edge. Returns True if an edge was removed."""
        before = len(self._edges)
        self._edges = [
            e for e in self._edges
            if not (e.producer == producer and e.consumer == consumer)
        ]
        removed = len(self._edges) < before
        if removed:
            self._save()
        return removed

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def upstream_of(self, job: str) -> List[LineageEdge]:
        """Return edges where *job* is the consumer (i.e. its data sources)."""
        return [e for e in self._edges if e.consumer == job]

    def downstream_of(self, job: str) -> List[LineageEdge]:
        """Return edges where *job* is the producer (i.e. jobs that read its output)."""
        return [e for e in self._edges if e.producer == job]

    def all_upstream_jobs(self, job: str) -> Set[str]:
        """Recursively collect all transitive upstream job names."""
        visited: Set[str] = set()
        queue = [job]
        while queue:
            current = queue.pop()
            for edge in self.upstream_of(current):
                if edge.producer not in visited:
                    visited.add(edge.producer)
                    queue.append(edge.producer)
        return visited

    def all_downstream_jobs(self, job: str) -> Set[str]:
        """Recursively collect all transitive downstream job names."""
        visited: Set[str] = set()
        queue = [job]
        while queue:
            current = queue.pop()
            for edge in self.downstream_of(current):
                if edge.consumer not in visited:
                    visited.add(edge.consumer)
                    queue.append(edge.consumer)
        return visited

    def all_edges(self) -> List[LineageEdge]:
        """Return a copy of all registered edges."""
        return list(self._edges)

    def jobs(self) -> Set[str]:
        """Return the set of all job names referenced in the lineage graph."""
        names: Set[str] = set()
        for e in self._edges:
            names.add(e.producer)
            names.add(e.consumer)
        return names
