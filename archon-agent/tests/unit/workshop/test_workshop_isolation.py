"""
ADL-037 enforcement test: app.workshop MUST NOT import from app.pipeline or app.tools.

This test is also the basis for the fitness/adl-037-workshop-isolation.sh script.
"""
import ast
import os
import pytest

WORKSHOP_DIR = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "app", "workshop"
)

FORBIDDEN_MODULES = ("app.pipeline", "app.tools")


def _collect_imports(filepath: str) -> list[str]:
    """Return all imported module names from a Python file."""
    with open(filepath, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _get_workshop_files():
    """Return all .py files under app/workshop/."""
    result = []
    for root, _, files in os.walk(WORKSHOP_DIR):
        for f in files:
            if f.endswith(".py"):
                result.append(os.path.join(root, f))
    return result


@pytest.mark.parametrize("filepath", _get_workshop_files())
def test_no_forbidden_import(filepath):
    """Each workshop module must not import from app.pipeline or app.tools."""
    imports = _collect_imports(filepath)
    violations = [
        imp for imp in imports
        if any(imp == forbidden or imp.startswith(forbidden + ".")
               for forbidden in FORBIDDEN_MODULES)
    ]
    assert not violations, (
        f"{filepath} imports forbidden module(s): {violations}\n"
        f"ADL-037: app.workshop MUST NOT depend on app.pipeline or app.tools."
    )
