"""End-to-end smoke test of the Streamlit UI with Streamlit's AppTest.
No network / no API key needed: the analysis engine is stubbed.
Run: python3 test_app.py
"""
import json

import services.analysis as an

SAMPLE = {
    "shared_facts": [{"statement": "Weekend plan discussed.", "evidence_a": "weekend ke plan",
                      "evidence_b": "us weekend", "confidence": "high"}],
    "person_a": {"explicitly_stated_feelings": ["bura laga"], "stated_needs": ["clarity"],
                 "interpretations_to_confirm": ["felt ignored"]},
    "person_b": {"explicitly_stated_feelings": ["hurt"], "stated_needs": ["time"],
                 "interpretations_to_confirm": ["was blamed"]},
    "divergence_point": {"moment": "'dekhte hain'", "person_a_reading": "a no",
                         "person_b_reading": "needs time", "why_it_may_have_diverged": "timing"},
    "ambiguous_phrases": [{"phrase": "dekhte hain", "language": "Hinglish",
                           "possible_meaning_a": "no", "possible_meaning_b": "let's see",
                           "note": "polite deferral"}],
    "questions_for_a_to_ask_b": ["What did you mean by dekhte hain?"],
    "questions_for_b_to_ask_a": ["Did you feel I was ignoring you?"],
    "reworded_concerns": {"person_a": "I want clarity", "person_b": "I want time"},
    "remaining_open_points": ["No date agreed."],
}

# Stub the only network call BEFORE the app runs.
an.analyze_accounts = lambda *a, **k: SAMPLE

from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file("app.py", default_timeout=90).run()
assert not at.exception, at.exception

# 1. Home renders, Load demo present
assert any(b.key == "btn_demo" for b in at.button), "no Load demo button"
print("PASS home screen renders")

# 2. Load demo -> jumps to consent
at.button(key="btn_demo").click().run()
assert not at.exception, at.exception
assert any(c.key == "consent_a" for c in at.checkbox), "not on consent screen"
print("PASS demo loads and lands on consent screen")

# 3. Analyze disabled until both consents ticked
assert at.button(key="btn_analyze").disabled is True
at.checkbox(key="consent_a").set_value(True)
at.checkbox(key="consent_b").set_value(True)
at.run()
assert at.button(key="btn_analyze").disabled is False, "analyze still disabled after consent"
print("PASS analyze gated behind both consent boxes")

# 4. Analyze -> results screen
at.button(key="btn_analyze").click().run()
assert not at.exception, at.exception
md = "\n".join(m.value for m in at.markdown)
md += "\n" + "\n".join(s.value for s in at.subheader)
md += "\n" + "\n".join(c.value for c in at.caption)
assert "The meaning gap" in md, "results header missing"
assert "dekhte hain" in md, "ambiguous phrase not rendered"
assert "kinder way to say" in md, "reworded concerns missing"
print("PASS results screen renders the full Meaning Gap view")

# 5. Re-analyze with a correction path exists
assert any(b.key == "reanalyze_person_a" for b in at.button), "no correction button"
print("PASS 'This isn't what I meant' correction control present")

# 6. Manual typing flow also works (fresh app instance)
at2 = AppTest.from_file("app.py", default_timeout=90).run()
at2.button(key="btn_start").click().run()
assert any(b.key == "submit_a" for b in at2.button), "input A screen missing"
at2.text_area(key="text_a").set_value("I felt ignored when they said dekhte hain.")
at2.run()
assert at2.button(key="submit_a").disabled is False
at2.button(key="submit_a").click().run()          # -> pass screen
assert any(b.key == "pass_go" for b in at2.button), "pass screen missing"
at2.button(key="pass_go").click().run()            # -> input B
at2.text_area(key="text_b").set_value("I meant let's see, not no.")
at2.run()
at2.button(key="submit_b").click().run()           # -> consent
assert any(c.key == "consent_a" for c in at2.checkbox)
print("PASS full typed pass-the-phone flow (A -> pass -> B -> consent)")

print("ALL APP TESTS PASSED")
