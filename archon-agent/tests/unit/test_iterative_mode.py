"""Focused tests for iterative architecture refinement."""

import inspect

from app.api.agent import _seed_context_from_previous
from app.models import ArchitectureContext
from app.tools.architecture_generator import _format_component_list, ArchitectureGeneratorTool
from app.tools.requirement_parser import _summarise_previous_architecture, RequirementParserTool


def test_context_iterative_mode_defaults_false():
    assert ArchitectureContext().iterative_mode is False


def test_context_seeded_from_previous_architecture():
    ctx = ArchitectureContext(iterative_mode=True, previous_architecture={
        "characteristics": [{"name": "Availability"}],
        "trade_offs": [{"decision": "Consistency"}],
    })
    _seed_context_from_previous(ctx)
    assert ctx.characteristics == [{"name": "Availability"}]
    assert ctx.trade_offs == [{"decision": "Consistency"}]
    assert ctx.architecture_design == {}
    assert ctx.adl_blocks == []


def test_summarise_previous_architecture_non_empty():
    summary = _summarise_previous_architecture({"style": "Event-driven", "components": ["Orders"]})
    assert "Event-driven" in summary and "Orders" in summary


def test_summarise_caps_components_at_20():
    summary = _summarise_previous_architecture({"components": [f"component-{i}" for i in range(25)]})
    assert "component-19" in summary
    assert "component-20" not in summary


def test_requirement_parser_delta_prefix_in_iterative_mode():
    source = inspect.getsource(RequirementParserTool.run)
    assert "ITERATIVE MODE — DELTA UPDATE" in source
    assert "context.iterative_mode and context.previous_architecture" in source


def test_requirement_parser_no_delta_prefix_on_first_run():
    ctx = ArchitectureContext(raw_requirements="new system")
    assert not (ctx.iterative_mode and ctx.previous_architecture)


def test_architecture_generation_includes_previous_components():
    source = inspect.getsource(ArchitectureGeneratorTool.run)
    assert "ITERATIVE UPDATE — PRESERVE AND EXTEND" in source
    assert "_format_component_list" in source
    assert "Orders (service)" in _format_component_list([
        {"name": "Orders", "type": "service", "responsibility": "Handles orders"}
    ])


def test_context_handles_none_previous_architecture():
    ctx = ArchitectureContext(previous_architecture=None, iterative_mode=True)
    _seed_context_from_previous(ctx)
    assert ctx.characteristics == []
