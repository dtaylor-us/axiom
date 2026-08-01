"""Jinja2 prompt template loader for SpecWeaver tools."""

from __future__ import annotations

from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

log = structlog.get_logger()
_PROMPTS_DIR = Path(__file__).parent
_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_DIR)),
    autoescape=False,
    keep_trailing_newline=True,
)


def load_prompt(template_name: str, **kwargs: object) -> str:
    """
    Load and render a Jinja2 prompt template.

    Args:
        template_name: Template name without .j2 extension.
        **kwargs: Template variables.

    Returns:
        Rendered prompt text.

    Raises:
        FileNotFoundError: If the template file is absent.
    """
    try:
        template = _env.get_template(f"{template_name}.j2")
    except TemplateNotFound as exc:
        raise FileNotFoundError(
            f"Prompt template '{template_name}.j2' not found in {_PROMPTS_DIR}"
        ) from exc
    rendered = template.render(**kwargs)
    log.debug("prompt_loaded", template=template_name, rendered_length=len(rendered))
    return rendered
