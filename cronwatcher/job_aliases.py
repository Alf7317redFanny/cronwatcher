"""Job alias management — map short names to canonical job names."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class AliasIndex:
    """Bidirectional mapping between aliases and canonical job names."""

    _path: Path
    _aliases: Dict[str, str] = field(default_factory=dict)  # alias -> canonical
    _reverse: Dict[str, List[str]] = field(default_factory=dict)  # canonical -> aliases

    def __post_init__(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._aliases = raw.get("aliases", {})
            self._rebuild_reverse()

    def _save(self) -> None:
        self._path.write_text(json.dumps({"aliases": self._aliases}, indent=2))

    def _rebuild_reverse(self) -> None:
        self._reverse = {}
        for alias, canonical in self._aliases.items():
            self._reverse.setdefault(canonical, []).append(alias)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def add(self, alias: str, canonical: str) -> None:
        """Register *alias* as a short name for *canonical*."""
        alias = alias.strip()
        canonical = canonical.strip()
        if not alias:
            raise ValueError("alias must not be blank")
        if not canonical:
            raise ValueError("canonical job name must not be blank")
        if alias == canonical:
            raise ValueError("alias must differ from the canonical name")
        if alias in self._aliases and self._aliases[alias] != canonical:
            raise ValueError(
                f"alias '{alias}' already mapped to '{self._aliases[alias]}'"
            )
        self._aliases[alias] = canonical
        self._reverse.setdefault(canonical, [])
        if alias not in self._reverse[canonical]:
            self._reverse[canonical].append(alias)
        self._save()

    def remove(self, alias: str) -> None:
        """Delete an alias mapping."""
        if alias not in self._aliases:
            raise KeyError(f"alias '{alias}' not found")
        canonical = self._aliases.pop(alias)
        self._reverse.get(canonical, []).remove(alias) if canonical in self._reverse else None
        self._save()

    def resolve(self, alias: str) -> Optional[str]:
        """Return canonical name for *alias*, or None if unknown."""
        return self._aliases.get(alias)

    def aliases_for(self, canonical: str) -> List[str]:
        """Return all aliases registered for a canonical job name."""
        return list(self._reverse.get(canonical, []))

    def all_aliases(self) -> Dict[str, str]:
        """Return a copy of the full alias mapping."""
        return dict(self._aliases)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AliasIndex(entries={len(self._aliases)}, path={self._path})"
