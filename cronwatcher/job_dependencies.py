"""Track inter-job dependencies and detect ordering violations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class DependencyError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class DependencyGraph:
    """Directed graph of job dependencies (job -> list of jobs it depends on)."""

    _deps: Dict[str, Set[str]] = field(default_factory=dict)

    def add_job(self, job_name: str) -> None:
        if job_name not in self._deps:
            self._deps[job_name] = set()

    def add_dependency(self, job_name: str, depends_on: str) -> None:
        """Register that *job_name* must run after *depends_on*."""
        self.add_job(job_name)
        self.add_job(depends_on)
        if job_name == depends_on:
            raise DependencyError(f"Job '{job_name}' cannot depend on itself.")
        self._deps[job_name].add(depends_on)
        if self._has_cycle():
            self._deps[job_name].discard(depends_on)
            raise DependencyError(
                f"Adding dependency '{job_name}' -> '{depends_on}' creates a cycle."
            )

    def dependencies_of(self, job_name: str) -> List[str]:
        """Return direct dependencies of a job."""
        return sorted(self._deps.get(job_name, set()))

    def dependents_of(self, job_name: str) -> List[str]:
        """Return jobs that directly depend on *job_name*."""
        return sorted(j for j, deps in self._deps.items() if job_name in deps)

    def execution_order(self) -> List[str]:
        """Return a topologically sorted list of all jobs."""
        visited: Set[str] = set()
        order: List[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in sorted(self._deps.get(name, set())):
                visit(dep)
            order.append(name)

        for job in sorted(self._deps):
            visit(job)
        return order

    def _has_cycle(self) -> bool:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            stack.add(node)
            for neighbor in self._deps.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in stack:
                    return True
            stack.discard(node)
            return False

        return any(dfs(n) for n in self._deps if n not in visited)

    def all_jobs(self) -> List[str]:
        return sorted(self._deps.keys())
