"""Format ArchitectureContext into a human-readable Markdown response.

Produces rich Markdown (with GFM tables, blockquotes, code fences, and
nested headings) that is rendered by the UI's ``react-markdown`` +
``remark-gfm`` pipeline.
"""

from __future__ import annotations

import re
from typing import Any

from app.models import ArchitectureContext


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


def format_response(ctx: ArchitectureContext) -> str:
    """Convert the pipeline context into a readable architecture report.

    Sections are only included when the corresponding context field is
    populated.
    """
    sections: list[str] = []
    sections.append("# Architecture Analysis Report\n")

    if ctx.parsed_entities:
        sections.extend(_fmt_parsed(ctx.parsed_entities))

    _has_challenges = (
        ctx.missing_requirements
        or ctx.ambiguities
        or ctx.hidden_assumptions
        or ctx.clarifying_questions
    )
    if _has_challenges:
        sections.extend(_fmt_challenges(ctx))

    if ctx.characteristics:
        sections.extend(_fmt_characteristics(ctx.characteristics))

    if ctx.characteristic_conflicts:
        sections.extend(_fmt_conflicts(ctx.characteristic_conflicts))

    if ctx.architecture_design:
        sections.extend(_fmt_architecture(ctx.architecture_design))

    if ctx.trade_offs:
        sections.extend(_fmt_tradeoffs(ctx.trade_offs))

    if ctx.weaknesses:
        sections.extend(_fmt_weaknesses(ctx.weaknesses))

    if ctx.fmea_risks:
        sections.extend(_fmt_fmea(ctx.fmea_risks))

    if ctx.review_findings:
        sections.extend(_fmt_review(ctx.review_findings))

    if ctx.governance_score is not None:
        sections.append(f"**Governance Score**: {ctx.governance_score}/100\n")

    return "\n".join(sections).strip() + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# Section formatters
# ═══════════════════════════════════════════════════════════════════════════


def _fmt_parsed(entities: dict[str, Any]) -> list[str]:
    """Format parsed requirement entities with tables for structured data."""
    lines: list[str] = ["## Parsed Requirements\n"]

    # --- Domain / system type intro line ---
    domain = entities.get("domain", "")
    sys_type = entities.get("system_type", "")
    if domain or sys_type:
        parts: list[str] = []
        if domain:
            parts.append(f"**Domain:** {_title(domain)}")
        if sys_type:
            parts.append(f"**System Type:** {_title(sys_type)}")
        lines.append(" · ".join(parts) + "\n")

    # --- Functional Requirements as table ---
    func_reqs = entities.get("functional_requirements", [])
    if func_reqs:
        lines.append("### Functional Requirements\n")
        if func_reqs and isinstance(func_reqs[0], dict):
            lines.append("| ID | Requirement | Priority |")
            lines.append("|:---|:---|:---|")
            for fr in func_reqs:
                fid = fr.get("id", "—")
                desc = fr.get("description", fr.get("content", str(fr)))
                pri = str(fr.get("priority", "—")).upper()
                lines.append(f"| {fid} | {desc} | {pri} |")
        else:
            for fr in func_reqs:
                lines.append(f"- {fr}")
        lines.append("")

    # --- Constraints as table ---
    constraints = entities.get("constraints", [])
    if constraints:
        lines.append("### Constraints\n")
        if isinstance(constraints[0], dict):
            lines.append("| Constraint | Type |")
            lines.append("|:---|:---|")
            for c in constraints:
                desc = c.get("description", str(c))
                ctype = _title(c.get("type", "—"))
                lines.append(f"| {desc} | {ctype} |")
        else:
            for c in constraints:
                lines.append(f"- {c}")
        lines.append("")

    # --- Integration Points as table ---
    integrations = entities.get("integration_points", [])
    if integrations:
        lines.append("### Integration Points\n")
        if isinstance(integrations[0], dict):
            lines.append("| System | Direction | Protocol |")
            lines.append("|:---|:---|:---|")
            for ip in integrations:
                sys_name = ip.get("system", "—")
                direction = ip.get("direction", "—")
                proto = ip.get("protocol", "—")
                lines.append(
                    f"| {sys_name} | {_title(direction)} | {_title(proto)} |"
                )
        else:
            for ip in integrations:
                lines.append(f"- {ip}")
        lines.append("")

    # --- Quality Signals as inline badges ---
    signals = entities.get("quality_signals", [])
    if signals:
        lines.append("### Quality Signals\n")
        lines.append(" · ".join(f"`{s}`" for s in signals) + "\n")

    # --- Ambiguous Terms as inline badges ---
    terms = entities.get("ambiguous_terms", [])
    if terms:
        lines.append("### Ambiguous Terms\n")
        lines.append(" · ".join(f"`{t}`" for t in terms) + "\n")

    # --- Any remaining keys (fallback) ---
    _handled = {
        "domain", "system_type", "functional_requirements", "constraints",
        "integration_points", "quality_signals", "ambiguous_terms",
    }
    for key, value in entities.items():
        if key in _handled:
            continue
        if isinstance(value, list):
            lines.append(f"### {_title(key)}\n")
            for item in value:
                lines.append(f"- {_format_item(item)}")
            lines.append("")
        elif isinstance(value, dict):
            lines.append(f"### {_title(key)}\n")
            for k, v in value.items():
                lines.append(f"- **{_title(k)}**: {v}")
            lines.append("")
        else:
            lines.append(f"**{_title(key)}**: {value}\n")

    return lines


def _fmt_challenges(ctx: ArchitectureContext) -> list[str]:
    lines: list[str] = ["## Requirement Challenges\n"]

    # ── Missing Requirements ──
    if ctx.missing_requirements:
        lines.append("### Missing Requirements\n")
        for item in ctx.missing_requirements:
            if isinstance(item, dict) and "area" in item:
                area = item.get("area", "")
                desc = item.get("description", "")
                impact = item.get("impact_if_ignored", "")
                if area:
                    lines.append(f"#### {_title(area)}\n")
                lines.append(f"{desc}\n")
                if impact:
                    lines.append(f"> **Impact if ignored:** {impact}\n")
            else:
                lines.append(f"- {_format_item(item)}")
        lines.append("")

    # ── Ambiguities ──
    if ctx.ambiguities:
        lines.append("### Ambiguities\n")
        if isinstance(ctx.ambiguities[0], dict) and "term" in ctx.ambiguities[0]:
            lines.append("| Term | Context | Possible Interpretations |")
            lines.append("|:---|:---|:---|")
            for item in ctx.ambiguities:
                term = item.get("term", "—")
                context = item.get("context", "—")
                interps = item.get("possible_interpretations", [])
                interps_str = (
                    ", ".join(str(i) for i in interps)
                    if isinstance(interps, list) else str(interps)
                )
                lines.append(f"| {term} | {context} | {interps_str} |")
        else:
            for item in ctx.ambiguities:
                lines.append(f"- {_format_item(item)}")
        lines.append("")

    # ── Hidden Assumptions ──
    if ctx.hidden_assumptions:
        lines.append("### Hidden Assumptions\n")
        if (isinstance(ctx.hidden_assumptions[0], dict)
                and "assumption" in ctx.hidden_assumptions[0]):
            lines.append("| Assumption | Risk If Wrong |")
            lines.append("|:---|:---|")
            for item in ctx.hidden_assumptions:
                assumption = item.get("assumption", "—")
                risk = item.get("risk_if_wrong", "—")
                lines.append(f"| {assumption} | {risk} |")
        else:
            for item in ctx.hidden_assumptions:
                lines.append(f"- {_format_item(item)}")
        lines.append("")

    # ── Clarifying Questions ──
    if ctx.clarifying_questions:
        lines.append("### Clarifying Questions\n")
        for i, item in enumerate(ctx.clarifying_questions, 1):
            if isinstance(item, dict):
                question = item.get(
                    "question", item.get("description", str(item)))
                refs = item.get("references", "")
                blocks = item.get("blocks_decision", "")
                lines.append(f"{i}. **{question}**")
                if refs:
                    lines.append(f"   *References:* {refs}")
                if blocks:
                    lines.append(f"   > Blocks: {blocks}")
                lines.append("")
            else:
                lines.append(f"{i}. {item}")
        lines.append("")

    return lines


def _fmt_characteristics(chars: list[dict]) -> list[str]:
    lines: list[str] = ["## Quality Characteristics\n"]

    # Detect rich data (has justification field)
    if chars and isinstance(chars[0], dict) and "justification" in chars[0]:
        # Summary table
        lines.append(
            "| Characteristic | Measurable Target | Coverage | Tensions |")
        lines.append("|:---|:---|:---|:---|")
        for char in chars:
            name = _get_char_name(char)
            target = char.get("measurable_target", "—")
            coverage = _title(
                str(char.get("current_requirement_coverage", "—")))
            tensions = char.get("tensions_with", [])
            tensions_str = (
                ", ".join(str(t) for t in tensions)
                if isinstance(tensions, list) else str(tensions)
            )
            lines.append(
                f"| **{_title(name)}** | {target} | {coverage} | "
                f"{tensions_str} |"
            )
        lines.append("")

        # Detailed justifications
        for char in chars:
            name = _get_char_name(char)
            justification = char.get("justification", "")
            if justification:
                lines.append(f"> **{_title(name)}:** {justification}\n")
    else:
        for char in chars:
            lines.append(f"- {_format_item(char)}")
    lines.append("")
    return lines


def _fmt_conflicts(conflicts: list[dict]) -> list[str]:
    lines: list[str] = ["## Characteristic Conflicts\n"]

    for conflict in conflicts:
        if isinstance(conflict, dict) and "characteristic_a" in conflict:
            char_a = conflict.get("characteristic_a", "")
            char_b = conflict.get("characteristic_b", "")
            nature = conflict.get("nature", "").replace("_", " ").title()
            explanation = conflict.get("explanation", "")
            resolution = conflict.get("resolution_strategy", "")
            recommendation = conflict.get("priority_recommendation", "")

            lines.append(f"#### {_title(char_a)} vs {_title(char_b)}")
            lines.append(f"*{nature}*\n")
            if explanation:
                lines.append(f"{explanation}\n")
            if resolution:
                lines.append(f"**Resolution:** {resolution}\n")
            if recommendation:
                lines.append(f"> **Recommendation:** {recommendation}\n")
        else:
            lines.append(f"- {_format_item(conflict)}")
    lines.append("")
    return lines


def _fmt_architecture(design: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Architecture Design\n"]

    # ── Style Selection ──
    style_sel = design.get("style_selection")
    if isinstance(style_sel, dict):
        lines.append("### Style Selection\n")

        scores = style_sel.get("style_scores", [])
        if scores:
            lines.append(
                "| Style | Score | Driving Characteristics "
                "| Vetoed | Veto Reason |"
            )
            lines.append("|:---|:---:|:---|:---:|:---|")
            for s in scores:
                style = s.get("style", "—")
                score = s.get("score", "—")
                drivers = s.get("driving_characteristics", [])
                drivers_str = (
                    ", ".join(str(d) for d in drivers)
                    if isinstance(drivers, list) else str(drivers)
                )
                vetoed = "Yes" if s.get("vetoed") else "No"
                veto_reason = s.get("veto_reason") or "—"
                lines.append(
                    f"| {style} | {score} | {drivers_str} "
                    f"| {vetoed} | {veto_reason} |"
                )
            lines.append("")

        selected = style_sel.get("selected_style", "")
        runner_up = style_sel.get("runner_up", "")
        rationale_sel = style_sel.get("selection_rationale", "")
        if selected:
            sel_line = f"**Selected:** {selected}"
            if runner_up:
                sel_line += f" · **Runner-up:** {runner_up}"
            lines.append(sel_line + "\n")
        if rationale_sel:
            lines.append(f"> {rationale_sel}\n")

    # ── Main info line ──
    style = design.get("style", "")
    domain = design.get("domain", "")
    sys_type = design.get("system_type", "")
    rationale = design.get("rationale", "")
    if style:
        intro: list[str] = [f"**Style:** {style}"]
        if domain:
            intro.append(f"**Domain:** {_title(domain)}")
        if sys_type:
            intro.append(f"**System Type:** {_title(sys_type)}")
        lines.append(" · ".join(intro) + "\n")
    if rationale:
        lines.append(f"{rationale}\n")

    # ── Components ──
    components = design.get("components", [])
    if components:
        lines.append("### Components\n")
        if isinstance(components[0], dict):
            for comp in components:
                name = comp.get("name", comp.get("title", "Unknown"))
                ctype = comp.get("type", "")
                responsibility = comp.get("responsibility", "")
                technology = comp.get("technology", "")
                tech_rationale = comp.get("technology_rationale", "")
                drivers = comp.get("characteristic_drivers", [])
                exposes = comp.get("exposes", [])
                depends_on = comp.get("depends_on", [])

                type_badge = f" `{ctype}`" if ctype else ""
                lines.append(f"#### {name}{type_badge}\n")
                if responsibility:
                    lines.append(f"{responsibility}\n")

                meta: list[str] = []
                if technology:
                    meta.append(f"**Technology:** {technology}")
                if tech_rationale:
                    meta.append(f"*{tech_rationale}*")
                if isinstance(drivers, list) and drivers:
                    meta.append(
                        "**Drivers:** "
                        + ", ".join(f"`{d}`" for d in drivers))
                if isinstance(exposes, list) and exposes:
                    meta.append(
                        "**Exposes:** "
                        + ", ".join(f"`{e}`" for e in exposes))
                if isinstance(depends_on, list) and depends_on:
                    meta.append(
                        "**Depends on:** "
                        + ", ".join(f"`{d}`" for d in depends_on))
                for m in meta:
                    lines.append(m)
                if meta:
                    lines.append("")
        else:
            for comp in components:
                lines.append(f"- {comp}")
            lines.append("")

    # ── Interactions ──
    interactions = design.get("interactions", [])
    if interactions:
        lines.append("### Interactions\n")
        if isinstance(interactions[0], dict):
            for interaction in interactions:
                desc = interaction.get("description", "")
                frm = interaction.get("from", "")
                to = interaction.get("to", "")
                pattern = interaction.get("pattern", "")
                rat = interaction.get("rationale", "")
                lines.append(f"- **{frm}** → **{to}** (`{pattern}`)")
                if desc:
                    lines.append(f"  {desc}")
                if rat:
                    lines.append(f"  *{rat}*")
            lines.append("")
        else:
            for interaction in interactions:
                lines.append(f"- {_format_item(interaction)}")
            lines.append("")

    # ── Primary Flow ──
    primary_flow = design.get("primary_flow")
    if isinstance(primary_flow, dict):
        lines.append("### Primary Flow\n")
        flow_desc = primary_flow.get("description", "")
        if flow_desc:
            lines.append(f"*{flow_desc}*\n")
        for step in primary_flow.get("steps", []):
            if isinstance(step, dict):
                num = step.get("step", "")
                comp = step.get("component", "")
                action = step.get("action", "")
                lines.append(f"{num}. **{comp}:** {action}")
            else:
                lines.append(f"- {step}")
        lines.append("")

    # ── Characteristic Coverage ──
    coverage = design.get("characteristic_coverage")
    if isinstance(coverage, dict):
        lines.append("### Characteristic Coverage\n")
        well = coverage.get("well_addressed", [])
        partial = coverage.get("partially_addressed", [])
        deferred = coverage.get("deferred", [])
        if well:
            lines.append(
                "**Well Addressed:** "
                + ", ".join(f"`{c}`" for c in well))
        if partial:
            lines.append(
                "**Partially Addressed:** "
                + ", ".join(f"`{c}`" for c in partial))
        if deferred:
            lines.append(
                "**Deferred:** "
                + ", ".join(f"`{c}`" for c in deferred))
        lines.append("")

    # ── When to Reconsider ──
    reconsider = design.get("when_to_reconsider_this_style", "")
    if reconsider:
        lines.append(f"> **When to Reconsider:** {reconsider}\n")

    # ── Fallback for unknown keys ──
    _handled = {
        "style_selection", "style", "domain", "system_type", "rationale",
        "components", "interactions", "primary_flow",
        "characteristic_coverage", "when_to_reconsider_this_style",
    }
    for key, value in design.items():
        if key in _handled:
            continue
        if isinstance(value, dict):
            lines.append(f"### {_title(key)}\n")
            _fmt_nested(value, lines, depth=0)
        elif isinstance(value, list):
            lines.append(f"### {_title(key)}\n")
            for item in value:
                lines.append(f"- {_format_item(item)}")
        else:
            lines.append(f"**{_title(key)}**: {value}")
        lines.append("")

    return lines


def _fmt_tradeoffs(tradeoffs: list[dict]) -> list[str]:
    lines: list[str] = ["## Trade-off Analysis\n"]

    for td in tradeoffs:
        if isinstance(td, dict) and "decision_id" in td:
            td_id = td.get("decision_id", "")
            decision = td.get("decision", "")
            optimises = td.get("optimises_characteristics", [])
            sacrifices = td.get("sacrifices_characteristics", [])
            acceptable = td.get("acceptable_because", "")
            context_dep = td.get("context_dependency", "")
            recommendation = td.get("recommendation", "")
            confidence = td.get("confidence", "")
            confidence_reason = td.get("confidence_reason", "")
            options = td.get("options_considered", [])

            lines.append(f"### {td_id}: {decision}\n")

            if isinstance(optimises, list) and optimises:
                lines.append(
                    "**Optimises:** "
                    + ", ".join(f"`{c}`" for c in optimises))
            if isinstance(sacrifices, list) and sacrifices:
                lines.append(
                    "**Sacrifices:** "
                    + ", ".join(f"`{c}`" for c in sacrifices))
            lines.append("")

            if options:
                lines.append("**Alternatives Considered:**\n")
                for opt in options:
                    if isinstance(opt, dict):
                        opt_name = opt.get("option", "")
                        rejected = opt.get("rejected_because", "")
                        lines.append(f"- ~~{opt_name}~~ — {rejected}")
                    else:
                        lines.append(f"- {opt}")
                lines.append("")

            if acceptable:
                lines.append(f"**Why acceptable:** {acceptable}\n")
            if context_dep:
                lines.append(
                    f"> **Context dependency:** {context_dep}\n")
            if recommendation:
                lines.append(f"**Recommendation:** {recommendation}\n")
            if confidence:
                suffix = f" ({confidence_reason})" if confidence_reason else ""
                lines.append(f"**Confidence:** {_title(confidence)}{suffix}\n")
        else:
            lines.append(f"- {_format_item(td)}")
    lines.append("")
    return lines


def _fmt_adl(rules: list[dict]) -> list[str]:
    lines: list[str] = ["## Architecture Definition Language (ADL)\n"]

    for rule in rules:
        if isinstance(rule, dict) and "adl_id" in rule:
            adl_id = rule.get("adl_id", "")
            metadata = rule.get("metadata", {})
            adl_source = rule.get("adl_source", "")
            char_enforced = rule.get("characteristic_enforced", "")
            enforcement = rule.get("enforcement_level", "soft")

            desc = (metadata.get("description", "")
                    if isinstance(metadata, dict) else "")
            requires = (metadata.get("requires", "")
                        if isinstance(metadata, dict) else "")

            enforcement_label = (
                "**Hard**" if enforcement == "hard" else "*Soft*")
            lines.append(f"### {adl_id}: {desc}\n")
            badge_parts = [f"**Enforcement:** {enforcement_label}"]
            if char_enforced:
                badge_parts.append(
                    f"**Characteristic:** `{char_enforced}`")
            if requires:
                badge_parts.append(f"**Requires:** {requires}")
            lines.append(" · ".join(badge_parts) + "\n")

            if adl_source:
                lines.append("```")
                lines.append(adl_source)
                lines.append("```\n")
        else:
            lines.append(f"- {_format_item(rule)}")
    lines.append("")
    return lines


def _fmt_weaknesses(weaknesses: list[dict]) -> list[str]:
    lines: list[str] = ["## Weakness Analysis\n"]

    for w in weaknesses:
        if isinstance(w, dict) and "id" in w:
            wid = w.get("id", "")
            desc = w.get("description", "")
            category = w.get("category", "")
            component = w.get("component_affected", "")
            severity = w.get("severity", "")
            likelihood = w.get("likelihood", "")
            effort = w.get("effort_to_fix", "")
            signals = w.get("early_warning_signals", [])
            mitigation = w.get("mitigation", "")
            linked = w.get("linked_characteristic", "")

            cat_str = (
                f" `{category.replace('_', ' ')}`" if category else "")
            lines.append(f"### {wid}{cat_str}\n")
            if desc:
                lines.append(f"{desc}\n")

            meta_rows: list[tuple[str, str]] = []
            if component:
                meta_rows.append(("Component", str(component)))
            if severity:
                meta_rows.append(("Severity", f"{severity}/5"))
            if likelihood:
                meta_rows.append(("Likelihood", f"{likelihood}/5"))
            if effort:
                meta_rows.append(("Effort to Fix", _title(str(effort))))
            if linked:
                meta_rows.append(("Linked Characteristic", str(linked)))
            if meta_rows:
                lines.append("| Attribute | Value |")
                lines.append("|:---|:---|")
                for lbl, val in meta_rows:
                    lines.append(f"| {lbl} | {val} |")
                lines.append("")

            if isinstance(signals, list) and signals:
                lines.append("**Early Warning Signals:**\n")
                for s in signals:
                    lines.append(f"- {s}")
                lines.append("")

            if mitigation:
                lines.append(f"> **Mitigation:** {mitigation}\n")
        else:
            lines.append(f"- {_format_item(w)}")
    lines.append("")
    return lines


def _fmt_fmea(risks: list[dict]) -> list[str]:
    lines: list[str] = ["## FMEA Risk Analysis\n"]

    for risk in risks:
        if isinstance(risk, dict) and (
            "rpn" in risk or "failure_mode" in risk
        ):
            mode = risk.get("failure_mode", risk.get("description", ""))
            rpn = risk.get("rpn", "")
            severity = risk.get("severity", "")
            occurrence = risk.get("occurrence", "")
            detection = risk.get("detection", "")
            effect = risk.get("effect", "")
            mitigation = risk.get(
                "recommended_action", risk.get("mitigation", ""))

            lines.append(f"### {mode}\n")
            meta: list[str] = []
            if severity:
                meta.append(f"Severity: {severity}")
            if occurrence:
                meta.append(f"Occurrence: {occurrence}")
            if detection:
                meta.append(f"Detection: {detection}")
            if rpn:
                meta.append(f"**RPN: {rpn}**")
            if meta:
                lines.append(" · ".join(meta) + "\n")
            if effect:
                lines.append(f"**Effect:** {effect}\n")
            if mitigation:
                lines.append(f"> **Recommended Action:** {mitigation}\n")
        else:
            lines.append(f"- {_format_item(risk)}")
    lines.append("")
    return lines


def _fmt_review(findings: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## Architecture Review\n"]

    challenge = findings.get("style_selection_challenge")
    if isinstance(challenge, dict):
        challenged = challenge.get("challenged", False)
        reason = challenge.get("reason", "")
        alt = challenge.get("recommended_alternative", "")

        lines.append("### Style Selection Challenge\n")
        if challenged:
            lines.append("**Challenged:** Yes\n")
            if reason:
                lines.append(f"{reason}\n")
            if alt:
                lines.append(f"**Recommended Alternative:** {alt}\n")
        else:
            lines.append(
                "**Challenged:** No — the style selection is "
                "well-justified.\n")

    # Handle any other top-level keys
    _handled = {"style_selection_challenge"}
    for key, value in findings.items():
        if key in _handled:
            continue
        if isinstance(value, dict):
            lines.append(f"### {_title(key)}\n")
            _fmt_nested(value, lines, depth=0)
        elif isinstance(value, list):
            lines.append(f"### {_title(key)}\n")
            for item in value:
                lines.append(f"- {_format_item(item)}")
        else:
            lines.append(f"**{_title(key)}**: {value}")
        lines.append("")

    return lines


# ═══════════════════════════════════════════════════════════════════════════
# Generic helpers  (also used by tests)
# ═══════════════════════════════════════════════════════════════════════════


def _title(key: str) -> str:
    """Convert snake_case or camelCase key to Title Case."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    return spaced.replace("_", " ").title()


def _format_item(item: object) -> str:
    """Format a single list item (dict, str, or other) for Markdown output."""
    if isinstance(item, dict):
        primary = item.get("description") or item.get("name") or item.get("title")
        if primary:
            extras = {k: v for k, v in item.items()
                      if k not in ("description", "name", "title") and v}
            if extras:
                parts = ", ".join(
                    f"{_title(k)}: {v}" for k, v in extras.items())
                return f"{primary} ({parts})"
            return str(primary)
        return ", ".join(f"{_title(k)}: {v}" for k, v in item.items())
    return str(item)


def _fmt_nested(data: dict, sections: list[str], depth: int) -> None:
    """Recursively format nested dicts for Markdown."""
    prefix = "  " * depth
    for key, value in data.items():
        if isinstance(value, dict):
            sections.append(f"{prefix}- **{_title(key)}**:")
            _fmt_nested(value, sections, depth + 1)
        elif isinstance(value, list):
            sections.append(f"{prefix}- **{_title(key)}**:")
            for item in value:
                if isinstance(item, dict):
                    sections.append(f"{prefix}  - {_format_item(item)}")
                else:
                    sections.append(f"{prefix}  - {item}")
        else:
            sections.append(f"{prefix}- **{_title(key)}**: {value}")


def _get_char_name(char: dict) -> str:
    """Extract the characteristic name from a dict."""
    return str(
        char.get("name", "")
        or char.get("description", "")
        or char.get("title", "—")
    )
