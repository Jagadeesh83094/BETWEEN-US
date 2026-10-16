"""Unit tests for the analysis engine (no network). Run: python3 test_engine.py"""
import json

import services.analysis as an
import services.sarvam_client as sc

VALID = {
    "shared_facts": [
        {"statement": "They discussed a weekend plan.", "evidence_a": "weekend ke plan",
         "evidence_b": "us weekend", "confidence": "high"}
    ],
    "person_a": {"explicitly_stated_feelings": ["bura laga"],
                 "stated_needs": ["clear answer"], "interpretations_to_confirm": ["felt ignored?"]},
    "person_b": {"explicitly_stated_feelings": ["hurt"], "stated_needs": ["time to think"],
                 "interpretations_to_confirm": ["was blamed?"]},
    "divergence_point": {"moment": "'dekhte hain'", "person_a_reading": "a no",
                         "person_b_reading": "needs time", "why_it_may_have_diverged": "timing"},
    "ambiguous_phrases": [
        {"phrase": "dekhte hain", "language": "Hinglish", "possible_meaning_a": "no",
         "possible_meaning_b": "let's see", "note": "polite deferral"}
    ],
    "questions_for_a_to_ask_b": ["What did you mean by dekhte hain?"],
    "questions_for_b_to_ask_a": ["Did you feel I was ignoring you?"],
    "reworded_concerns": {"person_a": "I want clarity", "person_b": "I want time"},
    "remaining_open_points": ["Neither agreed a date."],
}


def test_valid():
    sc.chat_json = lambda messages, **kw: json.dumps(VALID)
    out = an.analyze_accounts("a text", "b text")
    assert out["divergence_point"]["moment"] == "'dekhte hain'"
    assert out["shared_facts"][0]["confidence"] == "high"
    assert out["person_a"]["explicitly_stated_feelings"] == ["bura laga"]
    print("PASS valid JSON path")


def test_markdown_fenced():
    sc.chat_json = lambda messages, **kw: "```json\n" + json.dumps(VALID) + "\n```"
    out = an.analyze_accounts("a", "b")
    assert out["ambiguous_phrases"][0]["phrase"] == "dekhte hain"
    print("PASS fenced-JSON stripping")


def test_retry_then_valid():
    seq = iter(["this is not json at all", json.dumps(VALID)])
    sc.chat_json = lambda messages, **kw: next(seq)
    out = an.analyze_accounts("a", "b")
    assert out["remaining_open_points"] == ["Neither agreed a date."]
    print("PASS malformed -> retry -> valid")


def test_hard_fail():
    sc.chat_json = lambda messages, **kw: "still not json"
    try:
        an.analyze_accounts("a", "b")
    except an.AnalysisValidationError:
        print("PASS unparseable -> AnalysisValidationError")
        return
    raise AssertionError("expected AnalysisValidationError")


def test_coerce_missing_keys():
    sc.chat_json = lambda messages, **kw: json.dumps({"shared_facts": []})
    out = an.analyze_accounts("a", "b")  # missing keys tolerated after retry
    assert out["person_a"]["stated_needs"] == []
    assert out["reworded_concerns"]["person_a"] == "not enough information"
    print("PASS missing keys coerced to safe defaults")


if __name__ == "__main__":
    test_valid()
    test_markdown_fenced()
    test_retry_then_valid()
    test_hard_fail()
    test_coerce_missing_keys()
    print("ALL ENGINE TESTS PASSED")
