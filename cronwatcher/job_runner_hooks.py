"""Pre/post run hooks for jobs."""
from dataclasses import dataclass, field
from typing import Callable, List

HookFn = Callable[[str], None]


@dataclass
class HookRegistry:
    _pre: List[HookFn] = field(default_factory=list)
    _post: List[HookFn] = field(default_factory=list)
    _failure: List[HookFn] = field(default_factory=list)

    def register_pre(self, fn: HookFn) -> None:
        """Register a hook to run before a job."""
        self._pre.append(fn)

    def register_post(self, fn: HookFn) -> None:
        """Register a hook to run after a successful job."""
        self._post.append(fn)

    def register_failure(self, fn: HookFn) -> None:
        """Register a hook to run after a failed job."""
        self._failure.append(fn)

    def run_pre(self, job_name: str) -> None:
        for fn in self._pre:
            fn(job_name)

    def run_post(self, job_name: str) -> None:
        for fn in self._post:
            fn(job_name)

    def run_failure(self, job_name: str) -> None:
        for fn in self._failure:
            fn(job_name)

    def clear(self) -> None:
        self._pre.clear()
        self._post.clear()
        self._failure.clear()

    def __repr__(self) -> str:
        return (
            f"HookRegistry(pre={len(self._pre)}, "
            f"post={len(self._post)}, failure={len(self._failure)})"
        )
