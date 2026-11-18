"""
Fallback rules for metadata fields whose primary catalogue column is empty.

Rules live in the bundled ``enriched_data/metadata_rules.csv`` so they can be
reviewed and extended without code changes. Each rule targets one output field
(``genre`` or ``period``), optionally restricted to a project (exact path or
umbrella prefix), and assigns ``value`` when the rule's ``field`` matches:

``any``
    always matches (project-level default).
``exact``
    the field equals ``match_value`` (case-insensitive, whitespace-collapsed).
``leading_token``
    the part of the field before the first comma equals ``match_value``
    (exact, so ``UCP 9/1`` does not match ``UCP 9/12``).
``nonempty``
    the field has any non-empty value.

Rules are tried in file order; the first match wins.
"""
from __future__ import annotations

from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_metadata_rules, normalize_project

logger = get_logger()

_rules: list[dict] | None = None


def clean_value(value) -> str:
    """Return ``value`` as a stripped string; ``""`` for None/NaN/'nan'."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    s = str(value).strip()
    return "" if s.lower() in ("nan", "none") else s


def _fold(s: str) -> str:
    return " ".join(s.casefold().split())


def _load_rules() -> list[dict]:
    global _rules
    if _rules is None:
        try:
            _rules = get_metadata_rules().to_dict("records")
        except Exception as e:
            logger.error(f"error loading metadata_rules.csv: {e}")
            _rules = []
    return _rules


def _project_matches(rule_project: str, project: str) -> bool:
    rule_project = normalize_project(rule_project)
    if not rule_project:
        return True
    project = normalize_project(project)
    return project == rule_project or project.startswith(rule_project + "/")


def _field_matches(rule: dict, metadata_dict: dict) -> bool:
    match = rule.get("match", "")
    if match == "any":
        return True
    field_value = clean_value(metadata_dict.get(rule.get("field", "")))
    if not field_value:
        return False
    if match == "nonempty":
        return True
    if match == "exact":
        return _fold(field_value) == _fold(rule.get("match_value", ""))
    if match == "leading_token":
        return field_value.split(",")[0].strip() == rule.get("match_value", "").strip()
    logger.warning(f"unknown rule match type {match!r} in metadata_rules.csv")
    return False


def apply_rules(target: str, metadata_dict: dict, project: str) -> tuple[str, str]:
    """Return ``(value, source)`` from the first matching rule for ``target``.

    ``source`` is ``"rule:<field>"`` (or ``"rule:project"`` for project-level
    defaults). Returns ``("", "")`` when no rule matches.
    """
    for rule in _load_rules():
        if rule.get("target") != target:
            continue
        if not _project_matches(rule.get("project", ""), project):
            continue
        if _field_matches(rule, metadata_dict):
            field = rule.get("field", "") or "project"
            return rule.get("value", ""), f"rule:{field}"
    return "", ""
