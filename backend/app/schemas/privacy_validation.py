"""Privacy-aware validation helpers for student-entered free text.

These checks are deliberately narrow: they reject obvious contact identifiers from
narrative fields, not infer sensitive traits or classify a person's character. They are
not a substitute for data-loss prevention or human review.
"""
from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
# Reject ten or more digits separated only by common telephone formatting characters.
# Eight-digit dates and ordinary short scores are not matched.
_PHONE_OR_LONG_ID_RE = re.compile(r"(?<![A-Za-z0-9])(?:\+?\d[\s().-]*){10,13}(?![A-Za-z0-9])")


def validate_user_text(value: Any) -> Any:
    """Reject obvious contact identifiers from free-text user fields, preserving None.

    Dedicated project URLs remain supported in the URL field and are never fetched by the
    application. The error avoids echoing the submitted text back to the caller or logs.
    """
    if value is None or not isinstance(value, str):
        return value
    if _EMAIL_RE.search(value):
        raise ValueError("Please remove email addresses from this text. This prototype does not need personal contact details.")
    if _PHONE_OR_LONG_ID_RE.search(value):
        raise ValueError("Please remove phone numbers or long numeric identifiers from this text.")
    return value


def validate_text_tree(value: Any) -> Any:
    """Apply the same direct-identifier check to nested context values."""
    if isinstance(value, str):
        return validate_user_text(value)
    if isinstance(value, dict):
        for nested in value.values():
            validate_text_tree(nested)
        return value
    if isinstance(value, (list, tuple)):
        for nested in value:
            validate_text_tree(nested)
    return value
