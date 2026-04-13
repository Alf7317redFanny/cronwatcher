"""Tests for cronwatcher.job_dependencies."""
import pytest

from cronwatcher.job_dependencies import DependencyError, DependencyGraph


@pytest.fixture()
def graph() -> DependencyGraph:
    return DependencyGraph()


def test_add_job_registers_empty_deps(graph: DependencyGraph) -> None:
    graph.add_job("backup")
    assert "backup" in graph.all_jobs()
    assert graph.dependencies_of("backup") == []


def test_add_dependency_records_edge(graph: DependencyGraph) -> None:
    graph.add_dependency("report", "backup")
    assert "backup" in graph.dependencies_of("report")


def test_dependents_of(graph: DependencyGraph) -> None:
    graph.add_dependency("report", "backup")
    graph.add_dependency("email", "backup")
    assert graph.dependents_of("backup") == ["email", "report"]


def test_self_dependency_raises(graph: DependencyGraph) -> None:
    with pytest.raises(DependencyError, match="cannot depend on itself"):
        graph.add_dependency("backup", "backup")


def test_cycle_detection_raises(graph: DependencyGraph) -> None:
    graph.add_dependency("b", "a")
    graph.add_dependency("c", "b")
    with pytest.raises(DependencyError, match="creates a cycle"):
        graph.add_dependency("a", "c")


def test_cycle_does_not_corrupt_graph(graph: DependencyGraph) -> None:
    graph.add_dependency("b", "a")
    try:
        graph.add_dependency("a", "b")
    except DependencyError:
        pass
    # original edge must still be intact, bad edge must not be stored
    assert "a" in graph.dependencies_of("b")
    assert "b" not in graph.dependencies_of("a")


def test_execution_order_respects_deps(graph: DependencyGraph) -> None:
    graph.add_dependency("report", "backup")
    graph.add_dependency("email", "report")
    order = graph.execution_order()
    assert order.index("backup") < order.index("report")
    assert order.index("report") < order.index("email")


def test_execution_order_independent_jobs(graph: DependencyGraph) -> None:
    graph.add_job("alpha")
    graph.add_job("beta")
    order = graph.execution_order()
    assert set(order) == {"alpha", "beta"}


def test_all_jobs_sorted(graph: DependencyGraph) -> None:
    for name in ["z_job", "a_job", "m_job"]:
        graph.add_job(name)
    assert graph.all_jobs() == ["a_job", "m_job", "z_job"]


def test_unknown_job_returns_empty_deps(graph: DependencyGraph) -> None:
    assert graph.dependencies_of("nonexistent") == []


def test_unknown_job_returns_empty_dependents(graph: DependencyGraph) -> None:
    assert graph.dependents_of("nonexistent") == []
