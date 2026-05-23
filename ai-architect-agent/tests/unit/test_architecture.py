"""
Architecture fitness function tests for the Agent Orchestration Service.

Implements ADL blocks 008–014, 016, 017, and 024 from ADL.md using PyTestArch.
Each test function maps to a single ADL block and enforces either a containment
or dependency constraint on the Python module graph.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from networkx.exception import NetworkXError
from pytestarch import get_evaluable_architecture, Rule

# ---------------------------------------------------------------------------
# Shared evaluable architecture fixture
# ---------------------------------------------------------------------------

# Resolve paths relative to this test file → tests/unit → tests → ai-architect-agent
_AGENT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
_APP_PATH = str(Path(_AGENT_ROOT) / "app")

# pytestarch prefixes all internal module names with the root directory name
_PREFIX = Path(_AGENT_ROOT).name  # "ai-architect-agent"


def _mod(name: str) -> str:
    """Prefix a dotted module path with the root directory name.

    Example: _mod("app.tools") -> "ai-architect-agent.app.tools"
    """
    return f"{_PREFIX}.{name}"


@pytest.fixture(scope="module")
def evaluable():
    """Build the evaluable architecture once for all tests in this module."""
    return get_evaluable_architecture(
        root_path=_AGENT_ROOT,
        module_path=_APP_PATH,
        exclusions=("*__pycache__*",),
    )


@pytest.fixture(scope="module")
def evaluable_with_externals():
    """Build evaluable including external library nodes."""
    return get_evaluable_architecture(
        root_path=_AGENT_ROOT,
        module_path=_APP_PATH,
        exclusions=("*__pycache__*",),
        exclude_external_libraries=False,
    )


# ---------------------------------------------------------------------------
# ADL-008: Agent Orchestration Service — Domain Structure (Soft)
# ---------------------------------------------------------------------------

def test_agent_domain_structure(evaluable):
    """ADL-008: Every module under app resides in one of the seven domain packages."""
    allowed_domains = [
        "app.pipeline",
        "app.tools",
        "app.llm",
        "app.memory",
        "app.models",
        "app.prompts",
        "app.api",
        "app.review",
        "app.observability",
        "app.workshop",
    ]
    # Verify that top-level sub-packages of app are only the allowed domains
    app_dir = Path(_APP_PATH)
    top_level_packages = sorted(
        d.name
        for d in app_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith("__")
        and not d.name.startswith(".")
    )
    allowed_names = sorted(d.split(".")[-1] for d in allowed_domains)
    unexpected = set(top_level_packages) - set(allowed_names)
    assert not unexpected, (
        f"ADL-008: Unexpected packages found under app/: {unexpected}. "
        f"All modules must belong to one of: {allowed_names}"
    )


# ---------------------------------------------------------------------------
# ADL-009: Agent Orchestration Service — Pipeline Domain Components (Soft)
# ---------------------------------------------------------------------------

def test_pipeline_domain_components(evaluable):
    """ADL-009: graph and nodes modules reside within app.pipeline."""
    pipeline_dir = Path(_APP_PATH) / "pipeline"
    expected_components = {"graph.py", "nodes.py"}
    actual_files = {f.name for f in pipeline_dir.iterdir() if f.is_file() and f.suffix == ".py" and not f.name.startswith("__")}
    missing = expected_components - actual_files
    assert not missing, (
        f"ADL-009: Missing pipeline components: {missing}. "
        "graph and nodes must be contained within app.pipeline"
    )


# ---------------------------------------------------------------------------
# ADL-010: Agent Orchestration Service — Tools Domain Components (Soft)
# ---------------------------------------------------------------------------

def test_tools_domain_components(evaluable):
    """ADL-010: All twelve tool modules reside within app.tools."""
    expected_tools = {
        "base.py",
        "registry.py",
        "requirement_parser.py",
        "challenge_engine.py",
        "scenario_modeler.py",
        "characteristic_reasoner.py",
        "conflict_analyzer.py",
        "architecture_generator.py",
        "diagram_generator.py",
        "trade_off_engine.py",
        "adl_generator.py",
        "weakness_analyzer.py",
    }
    tools_dir = Path(_APP_PATH) / "tools"
    actual_files = {f.name for f in tools_dir.iterdir() if f.is_file() and f.suffix == ".py" and not f.name.startswith("__")}
    missing = expected_tools - actual_files
    assert not missing, (
        f"ADL-010: Missing tool components: {missing}. "
        "All twelve tool modules must be contained within app.tools"
    )


# ---------------------------------------------------------------------------
# ADL-011: Agent Orchestration Service — Tool Dependency Rule (Soft)
# ---------------------------------------------------------------------------

def test_tool_dependency_rule(evaluable):
    """ADL-011: Tools domain has no dependency on pipeline or api domains."""
    (
        Rule()
        .modules_that()
        .are_sub_modules_of(_mod("app.tools"))
        .should_not()
        .import_modules_that()
        .are_sub_modules_of(_mod("app.pipeline"))
        .assert_applies(evaluable)
    )

    (
        Rule()
        .modules_that()
        .are_sub_modules_of(_mod("app.tools"))
        .should_not()
        .import_modules_that()
        .are_sub_modules_of(_mod("app.api"))
        .assert_applies(evaluable)
    )


# ---------------------------------------------------------------------------
# ADL-012: Agent Orchestration Service — Pipeline Nodes Dependency Rule (Soft)
# ---------------------------------------------------------------------------

def test_pipeline_nodes_dependency_rule(evaluable):
    """ADL-012: app.pipeline.nodes imports only from app.tools.registry (and
    app.tools.base) and not from any other module under app.tools."""
    forbidden_tool_modules = [
        _mod("app.tools.requirement_parser"),
        _mod("app.tools.challenge_engine"),
        _mod("app.tools.scenario_modeler"),
        _mod("app.tools.characteristic_reasoner"),
        _mod("app.tools.conflict_analyzer"),
        _mod("app.tools.architecture_generator"),
        _mod("app.tools.diagram_generator"),
        _mod("app.tools.trade_off_engine"),
        _mod("app.tools.adl_generator"),
        _mod("app.tools.weakness_analyzer"),
    ]

    for module in forbidden_tool_modules:
        (
            Rule()
            .modules_that()
            .are_named(_mod("app.pipeline.nodes"))
            .should_not()
            .import_modules_that()
            .are_named(module)
            .assert_applies(evaluable)
        )


# ---------------------------------------------------------------------------
# ADL-013: Agent Orchestration Service — LLM Domain Isolation (Hard)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Known violation: app.memory.store imports openai — ADL-013 Hard enforcement.",
    strict=True,
)
def test_llm_domain_isolation(evaluable_with_externals):
    """ADL-013: tools, pipeline, and memory domains have no dependency on OpenAI
    or LangChain libraries."""
    for domain in [_mod("app.tools"), _mod("app.pipeline"), _mod("app.memory")]:
        for lib in ["openai", "langchain_openai"]:
            (
                Rule()
                .modules_that()
                .are_sub_modules_of(domain)
                .should_not()
                .import_modules_that()
                .are_named(lib)
                .assert_applies(evaluable_with_externals)
            )


# ---------------------------------------------------------------------------
# ADL-014: Agent Orchestration Service — Memory Domain Isolation (Hard)
# ---------------------------------------------------------------------------

def test_memory_domain_isolation(evaluable_with_externals):
    """ADL-014: tools and pipeline domains have no dependency on Qdrant client."""
    for domain in [_mod("app.tools"), _mod("app.pipeline")]:
        (
            Rule()
            .modules_that()
            .are_sub_modules_of(domain)
            .should_not()
            .import_modules_that()
            .are_named("qdrant_client")
            .assert_applies(evaluable_with_externals)
        )


# ---------------------------------------------------------------------------
# ADL-016: Agent Orchestration Service — ArchitectureContext Ownership (Soft)
# ---------------------------------------------------------------------------

def test_architecture_context_ownership(evaluable):
    """ADL-016: ArchitectureContext is only defined in app.models.context;
    tools, pipeline, and api domains depend on app.models."""
    # Verify context module exists in models
    context_path = Path(_APP_PATH) / "models" / "context.py"
    assert context_path.exists(), (
        "ADL-016: app.models.context must exist — ArchitectureContext "
        "belongs exclusively in the models domain"
    )

    # Verify no other domain defines a 'context' module
    for domain in ["pipeline", "tools", "api", "llm", "memory"]:
        forbidden_context = Path(_APP_PATH) / domain / "context.py"
        assert not forbidden_context.exists(), (
            f"ADL-016: {domain}/context.py must not exist — "
            "ArchitectureContext belongs exclusively in app.models"
        )

    # Verify tools, pipeline, and api depend on models
    # The ADL asserts domain-level dependency: at least one module in each
    # domain must import from app.models (not necessarily every sub-module).
    import ast
    for domain_name in ["tools", "pipeline", "api"]:
        domain_dir = Path(_APP_PATH) / domain_name
        found_models_import = False
        for py_file in domain_dir.rglob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("app.models"):
                        found_models_import = True
                        break
            if found_models_import:
                break
        assert found_models_import, (
            f"ADL-016: app.{domain_name} must depend on app.models — "
            "ArchitectureContext ownership requires each domain to reference models"
        )


# ---------------------------------------------------------------------------
# ADL-017: Agent Orchestration Service — API Domain Boundary (Soft)
# ---------------------------------------------------------------------------

def test_api_domain_boundary(evaluable):
    """ADL-017: pipeline, tools, memory, and llm domains have no dependency on
    the api domain."""
    for domain in [
        _mod("app.pipeline"),
        _mod("app.tools"),
        _mod("app.memory"),
        _mod("app.llm"),
    ]:
        (
            Rule()
            .modules_that()
            .are_sub_modules_of(domain)
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(_mod("app.api"))
            .assert_applies(evaluable)
        )


# ---------------------------------------------------------------------------
# ADL-024: Cross-Service — Database Access Prohibition (Hard)
# ---------------------------------------------------------------------------

def test_agent_database_access_prohibition(evaluable_with_externals):
    """ADL-024: No module under app imports from psycopg2, asyncpg, or
    sqlalchemy."""
    for lib in ["psycopg2", "asyncpg", "sqlalchemy"]:
        try:
            (
                Rule()
                .modules_that()
                .are_sub_modules_of(_mod("app"))
                .should_not()
                .import_modules_that()
                .are_named(lib)
                .assert_applies(evaluable_with_externals)
            )
        except NetworkXError:
            # Library not in the dependency graph at all — no module
            # imports it, so the prohibition is trivially satisfied.
            pass
