"""Job run archiver — moves old history records to a compressed archive file."""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from cronwatcher.history import History, RunRecord


@dataclass
class ArchivePolicy:
    """Policy controlling when records are eligible for archiving."""

    # Records older than this many days are archived.
    archive_after_days: int = 30
    # Maximum number of records to archive in a single pass (0 = unlimited).
    batch_size: int = 0

    def __post_init__(self) -> None:
        if self.archive_after_days < 1:
            raise ValueError("archive_after_days must be >= 1")
        if self.batch_size < 0:
            raise ValueError("batch_size must be >= 0")

    def cutoff(self, now: Optional[datetime] = None) -> datetime:
        """Return the datetime before which records are considered archivable."""
        now = now or datetime.utcnow()
        return now - timedelta(days=self.archive_after_days)


@dataclass
class ArchiveResult:
    """Summary of a single archive pass."""

    archived_count: int = 0
    archive_path: str = ""
    skipped_count: int = 0
    errors: List[str] = field(default_factory=list)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ArchiveResult(archived={self.archived_count}, "
            f"skipped={self.skipped_count}, errors={len(self.errors)})"
        )


class JobArchiver:
    """Archives old run records from a History store into a gzipped JSONL file.

    Each archive file is named by the UTC date of the archiving run, e.g.:
        runs_archive_2024-06-01.jsonl.gz
    """

    def __init__(
        self,
        history: History,
        archive_dir: str,
        policy: Optional[ArchivePolicy] = None,
    ) -> None:
        self._history = history
        self._archive_dir = Path(archive_dir)
        self._policy = policy or ArchivePolicy()
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def archive(self, now: Optional[datetime] = None) -> ArchiveResult:
        """Move eligible records out of the live history into a compressed archive.

        Returns an :class:`ArchiveResult` describing what happened.
        """
        now = now or datetime.utcnow()
        cutoff = self._policy.cutoff(now)
        result = ArchiveResult()

        eligible = self._collect_eligible(cutoff)
        if not eligible:
            return result

        if self._policy.batch_size > 0:
            to_archive = eligible[: self._policy.batch_size]
            result.skipped_count = len(eligible) - len(to_archive)
        else:
            to_archive = eligible

        archive_path = self._archive_path(now)
        result.archive_path = str(archive_path)

        try:
            self._write_archive(archive_path, to_archive)
        except OSError as exc:
            result.errors.append(f"write error: {exc}")
            return result

        # Remove archived records from live history.
        ids_to_remove = {r.run_id for r in to_archive}
        self._history._records = [
            r for r in self._history._records if r.run_id not in ids_to_remove
        ]
        try:
            self._history._persist()
        except Exception as exc:  # pragma: no cover
            result.errors.append(f"persist error after archive: {exc}")

        result.archived_count = len(to_archive)
        return result

    def list_archives(self) -> List[Path]:
        """Return sorted list of archive files in the archive directory."""
        return sorted(self._archive_dir.glob("runs_archive_*.jsonl.gz"))

    def load_archive(self, path: Path) -> List[RunRecord]:
        """Decompress and parse a single archive file into RunRecord objects."""
        records: List[RunRecord] = []
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(RunRecord(**data))
        return records

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_eligible(self, cutoff: datetime) -> List[RunRecord]:
        cutoff_ts = cutoff.timestamp()
        return [
            r
            for r in self._history._records
            if r.started_at < cutoff_ts
        ]

    def _archive_path(self, now: datetime) -> Path:
        date_str = now.strftime("%Y-%m-%d")
        filename = f"runs_archive_{date_str}.jsonl.gz"
        return self._archive_dir / filename

    def _write_archive(self, path: Path, records: List[RunRecord]) -> None:
        # Append to existing archive for the same date rather than overwrite.
        mode = "ab" if path.exists() else "wb"
        with gzip.open(path, mode) as fh:
            for record in records:
                line = json.dumps(record.__dict__) + "\n"
                fh.write(line.encode("utf-8"))
