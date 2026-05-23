"""Architecture tests for LLM provider boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3] / "app"


def test_tools_no_openai_import() -> None:
    """Tool modules do not import provider SDKs directly."""
    violations = _imports_in_tree(APP_ROOT / "tools", {"openai", "httpx"})

    assert violations == []


def test_workshop_no_direct_llm_calls() -> None:
    """Workshop modules do not import provider SDKs directly."""
    violations = _imports_in_tree(APP_ROOT / "workshop", {"openai", "httpx"})

    assert violations == []


def test_llm_complete_calls_include_stage_name() -> None:
    """Every LLMClient.complete call in tools and workshop passes stage_name."""
    violations: list[str] = []
    for root in (APP_ROOT / "tools", APP_ROOT / "workshop"):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if _is_complete_call(node) and not _has_stage_name(node):
                    violations.append(f"{path}:{node.lineno}")

    assert violations == []


def _imports_in_tree(root: Path, forbidden_modules: set[str]) -> list[str]:
    """Return files that import forbidden modules."""
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_modules:
                        violations.append(f"{path}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module in forbidden_modules:
                    violations.append(f"{path}:{node.lineno}")
    return violations


def _is_complete_call(node: ast.AST) -> bool:
    """Return True when an AST node is a call to an object's complete method."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "complete"
    )


def _has_stage_name(node: ast.Call) -> bool:
    """Return True when a complete call passes stage_name as a keyword."""
    return any(keyword.arg == "stage_name" for keyword in node.keywords)
