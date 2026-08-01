"""
app.workshop — Quality Attribute Workshop module.

A conversational elicitation feature for identifying architecture
characteristics from unstructured stakeholder inputs such as meeting
notes, email threads, and partial requirements.

Follows the SEI Quality Attribute Workshop (QAW) method documented
in CMU/SEI-2001-TR-020 and Bass, Clements, Kazman "Software
Architecture in Practice" 4th ed., SEI/Addison-Wesley 2021,
chapters 2-3.

This package is intentionally isolated from app.pipeline and
app.tools. It shares only the LLM client and prompt loader
infrastructure from the broader app package.
"""

from app.workshop.agent import QualityAttributeWorkshopAgent

__all__ = ["QualityAttributeWorkshopAgent"]
