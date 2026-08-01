from __future__ import annotations

import pytest

from app.prompts.loader import load_prompt


class TestLoadPrompt:
    """Tests for the prompt loader."""

    def test_renders_template_variables(self):
        """load_prompt() renders template variables correctly."""
        result = load_prompt("requirement_parser", raw_requirements="Build an API")
        assert "Build an API" in result
        assert "{{ raw_requirements }}" not in result

    def test_raises_file_not_found_for_missing_template(self):
        """load_prompt() raises FileNotFoundError for missing template."""
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            load_prompt("nonexistent")

    def test_renders_parsed_entities_as_json(self):
        """load_prompt() renders parsed_entities as valid JSON via tojson filter."""
        entities = {
            "domain": "fintech",
            "system_type": "payment platform",
            "functional_requirements": [{"id": "FR-001", "description": "Accept payments"}],
        }
        result = load_prompt(
            "requirement_challenge",
            raw_requirements="Build payment system",
            parsed_entities=entities,
        )
        assert '"domain": "fintech"' in result or '"domain":"fintech"' in result
        assert "fintech" in result

    def test_stub_stage_template_renders(self):
        """load_prompt() renders the stub_stage template successfully."""
        result = load_prompt("stub_stage", stage_name="test_stage")
        assert "test_stage" in result

    def test_scenario_modeler_template_renders(self):
        """load_prompt() renders scenario_modeler with parsed_entities dict."""
        entities = {"domain": "healthcare", "system_type": "EHR platform"}
        result = load_prompt(
            "scenario_modeler",
            raw_requirements="Build EHR system",
            parsed_entities=entities,
        )
        assert "healthcare" in result
        assert "EHR" in result
