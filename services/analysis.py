"""The analysis engine: one chat call, strict JSON validation, one retry.

Flow (services.sarvam_client.chat_json is the only API call used):
  1. Build messages from prompts.analysis_prompt.
  2. Call the model once.
  3. Parse + validate the JSON. On malformed output, retry ONCE with a repair
     message. If it still fails, raise AnalysisValidationError and the UI shows a
     friendly error with a retry button.
  4. Coerce the validated object so every field the UI reads is guaranteed to
     exist (missing sub-fields become empty lists / neutral defaults rather than
     crashing the results screen).
"""

from __future__ import annotations

import json
import re
from typing import Optional

from prompts.analysis_prompt import build_analysis_messages, build_repair_messages

from . import sarvam_client

# Top-level keys we require in a well-formed reply.
REQUIRED_TOP_KEYS = [
    "shared_facts",
    "person_a",
    "person_b",
    "divergence_point",
    "ambiguous_phrases",
    "questions_for_a_to_ask_b",
    "questions_for_b_to_ask_a",
    "reworded_concerns",
    "remaining_open_points",
]

_NOT_ENOUGH = "not enough information"


class AnalysisValidationError(RuntimeError):
    """Raised when the model's JSON cannot be parsed/validated after one retry."""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` fences the model sometimes adds despite instructions."""
    text = text.strip()
    fence = re.match(r"^```[a-zA-Z0-9]*\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def parse_json_safely(text: str) -> dict:
    """Best-effort JSON parse: strip fences, then fall back to the outermost {...}."""
    if text is None:
        raise ValueError("empty model reply")
    cleaned = _strip_code_fences(text)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        obj = json.loads(cleaned[start : end + 1])
    if not isinstance(obj, dict):
        raise ValueError("model reply was not a JSON object")
    return obj


def missing_top_keys(obj: dict) -> list:
    return [k for k in REQUIRED_TOP_KEYS if k not in obj]


# ---------------------------------------------------------------------------
# Coercion — guarantee the shape the UI expects
# ---------------------------------------------------------------------------
def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, "", _NOT_ENOUGH):
        return []
    return [value]


def _as_str(value) -> str:
    if value is None:
        return _NOT_ENOUGH
    if isinstance(value, str):
        return value.strip() or _NOT_ENOUGH
    return str(value)


def _coerce_person(value) -> dict:
    value = value if isinstance(value, dict) else {}
    return {
        "explicitly_stated_feelings": _as_list(value.get("explicitly_stated_feelings")),
        "stated_needs": _as_list(value.get("stated_needs")),
        "interpretations_to_confirm": _as_list(value.get("interpretations_to_confirm")),
    }


def coerce_result(obj: dict) -> dict:
    """Fill every field the results screen reads, without inventing content."""
    obj = obj if isinstance(obj, dict) else {}

    shared_facts = []
    for item in _as_list(obj.get("shared_facts")):
        if isinstance(item, dict):
            shared_facts.append(
                {
                    "statement": _as_str(item.get("statement")),
                    "evidence_a": _as_str(item.get("evidence_a")),
                    "evidence_b": _as_str(item.get("evidence_b")),
                    "confidence": _as_str(item.get("confidence")).lower()
                    if _as_str(item.get("confidence")).lower() in ("high", "medium", "low")
                    else "medium",
                }
            )

    ambiguous = []
    for item in _as_list(obj.get("ambiguous_phrases")):
        if isinstance(item, dict):
            ambiguous.append(
                {
                    "phrase": _as_str(item.get("phrase")),
                    "language": _as_str(item.get("language")),
                    "possible_meaning_a": _as_str(item.get("possible_meaning_a")),
                    "possible_meaning_b": _as_str(item.get("possible_meaning_b")),
                    "note": _as_str(item.get("note")),
                }
            )

    div = obj.get("divergence_point")
    div = div if isinstance(div, dict) else {}
    divergence_point = {
        "moment": _as_str(div.get("moment")),
        "person_a_reading": _as_str(div.get("person_a_reading")),
        "person_b_reading": _as_str(div.get("person_b_reading")),
        "why_it_may_have_diverged": _as_str(div.get("why_it_may_have_diverged")),
    }

    reworded = obj.get("reworded_concerns")
    reworded = reworded if isinstance(reworded, dict) else {}

    return {
        "shared_facts": shared_facts,
        "person_a": _coerce_person(obj.get("person_a")),
        "person_b": _coerce_person(obj.get("person_b")),
        "divergence_point": divergence_point,
        "ambiguous_phrases": ambiguous,
        "questions_for_a_to_ask_b": _as_list(obj.get("questions_for_a_to_ask_b")),
        "questions_for_b_to_ask_a": _as_list(obj.get("questions_for_b_to_ask_a")),
        "reworded_concerns": {
            "person_a": _as_str(reworded.get("person_a")),
            "person_b": _as_str(reworded.get("person_b")),
        },
        "remaining_open_points": _as_list(obj.get("remaining_open_points")),
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def analyze_accounts(
    account_a: str,
    account_b: str,
    language_a: str = "unknown",
    language_b: str = "unknown",
    corrections: Optional[dict] = None,
) -> dict:
    """Run the full analysis. Returns a coerced result dict.

    Raises sarvam_client.AnalysisAPIError for API/network problems and
    AnalysisValidationError when the model won't return usable JSON.
    """
    account_a = (account_a or "").strip()
    account_b = (account_b or "").strip()
    if not account_a or not account_b:
        raise ValueError("Both accounts are required before analysis.")

    messages = build_analysis_messages(
        account_a, account_b, language_a, language_b, corrections
    )

    # --- Attempt 1 ---
    raw = sarvam_client.chat_json(messages)
    try:
        obj = parse_json_safely(raw)
        if missing_top_keys(obj):
            raise ValueError(f"missing keys: {missing_top_keys(obj)}")
    except (ValueError, json.JSONDecodeError):
        # --- Attempt 2 (the single allowed retry) ---
        repair = messages + [
            {"role": "assistant", "content": raw[:4000]},
            *build_repair_messages(raw),
        ]
        raw2 = sarvam_client.chat_json(repair)
        try:
            obj = parse_json_safely(raw2)
        except (ValueError, json.JSONDecodeError) as exc:
            raise AnalysisValidationError(
                "We couldn't read the analysis this time. Please try again."
            ) from exc

    # Missing keys after the retry are tolerated: coerce fills neutral defaults
    # rather than failing, so the participants still get whatever was produced.
    return coerce_result(obj)
