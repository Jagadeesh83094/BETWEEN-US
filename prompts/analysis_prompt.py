"""Prompt text and message builders for the BETWEEN US analysis engine.

Everything the chat model sees is defined here so the wording can be tuned in
one place. The system prompt encodes the app's non-negotiable rules: no
mind-reading, no verdicts, only explicitly stated feelings/needs, every
inference framed as a correctable hypothesis.
"""

from __future__ import annotations

from typing import Optional

# The exact JSON object the model must return. Kept next to the prompt so the
# instruction and the validator never drift apart.
OUTPUT_SCHEMA_TEMPLATE = """{
  "shared_facts": [
    {"statement": "", "evidence_a": "", "evidence_b": "", "confidence": "high|medium|low"}
  ],
  "person_a": {"explicitly_stated_feelings": [], "stated_needs": [], "interpretations_to_confirm": []},
  "person_b": {"explicitly_stated_feelings": [], "stated_needs": [], "interpretations_to_confirm": []},
  "divergence_point": {
    "moment": "",
    "person_a_reading": "",
    "person_b_reading": "",
    "why_it_may_have_diverged": ""
  },
  "ambiguous_phrases": [
    {"phrase": "", "language": "", "possible_meaning_a": "", "possible_meaning_b": "", "note": ""}
  ],
  "questions_for_a_to_ask_b": [],
  "questions_for_b_to_ask_a": [],
  "reworded_concerns": {"person_a": "", "person_b": ""},
  "remaining_open_points": []
}"""

SYSTEM_PROMPT = """You are the analysis engine behind "BETWEEN US — The Meaning Mirror".
Two people have described the same misunderstanding in their own words. Your job is to
help them SEE the gap between their two readings of the same moment — never to judge it.

HARD RULES (never break these):
1. You are NOT a therapist, a judge, or a mind reader. Never decide who is right or wrong.
   Never assign blame, and never deliver a verdict.
2. Never claim to detect emotions from voice, tone, or silence. You only ever work from
   the words the two people actually wrote or said.
3. Only use feelings and needs that the person EXPLICITLY stated in their own words.
   Do NOT invent, infer, or assume emotions. If someone stated no feeling, return an
   empty list for that field. Never upgrade "I was upset" into "you felt betrayed".
4. Present every inference as a HYPOTHESIS the participants can correct. Use hedged
   wording such as "may have meant", "could be read as", "one possible reading is",
   "it is possible that". Never state a reading as fact.
5. Quote or closely reference the participants' own words as evidence for anything you
   put in "shared_facts" and in the divergence readings.
6. If the accounts use mixed languages (Hinglish, Tenglish, code-mixing), PRESERVE the
   original phrase exactly in the "phrase" field, and explain its possible meanings in
   simple English in the other fields. Do not translate the phrase away.
7. If there is not enough information for a field, return an empty list, or the exact
   string "not enough information". Never guess to fill a gap.
8. Keep the tone neutral and kind. No diagnosis, no clinical language, no verdict.
9. Output ONLY a single valid JSON object matching the schema. No markdown, no code
   fences, no commentary before or after the JSON.

WHAT EACH FIELD MEANS:
- shared_facts: statements BOTH accounts support, each with a short quote from A
  (evidence_a) and from B (evidence_b), and a confidence of high, medium, or low.
- person_a / person_b: the feelings and needs that person stated in their OWN words
  (verbatim or near-verbatim), plus "interpretations_to_confirm" — the readings of the
  other person's behaviour that THIS person should check, phrased as questions.
- divergence_point: the FIRST moment where the two understandings split. "moment" names
  it; "person_a_reading" and "person_b_reading" give each side's reading; 
  "why_it_may_have_diverged" offers a hedged, neutral explanation.
- ambiguous_phrases: words or short phrases that likely meant different things to each
  person (e.g. a polite "dekhte hain" / "chuddam" / "let's see" / "fine, do whatever you
  want"). Give the phrase, its language, a possible meaning for A, a possible meaning for
  B, and a short neutral note.
- questions_for_a_to_ask_b / questions_for_b_to_ask_a: open, non-accusatory questions one
  person can ask the other to close the gap. Prefer "I" framing and genuine curiosity.
- reworded_concerns: a kinder, non-blaming rewording of each person's main concern, so it
  can be said out loud without landing as an attack.
- remaining_open_points: what is still unresolved or unknown after this analysis.
"""


def build_analysis_messages(
    account_a: str,
    account_b: str,
    language_a: str = "unknown",
    language_b: str = "unknown",
    corrections: Optional[dict] = None,
) -> list:
    """Build the chat messages for one analysis call.

    corrections (optional) is {"person_a": "...", "person_b": "..."} — free-text notes
    from the "This isn't what I meant" flow. When present they are authoritative and
    must override any earlier inference.
    """
    corrections = corrections or {}
    correction_block = ""
    if corrections.get("person_a", "").strip() or corrections.get("person_b", "").strip():
        correction_block = (
            "\n\nPARTICIPANT CORRECTIONS (these override any earlier reading — treat them "
            "as the corrected truth and adjust the analysis accordingly):\n"
            f"- Person A says: {corrections.get('person_a', '').strip() or '(none)'}\n"
            f"- Person B says: {corrections.get('person_b', '').strip() or '(none)'}\n"
        )

    user_prompt = f"""Here are two accounts of the same misunderstanding.

--- PERSON A (language they used: {language_a}) ---
{account_a}

--- PERSON B (language they used: {language_b}) ---
{account_b}
{correction_block}
Produce the analysis now. Remember: only the feelings and needs each person explicitly
stated, every inference hedged as a hypothesis they can correct, no blame and no verdict.
If a section has too little information, use an empty list or "not enough information".

Return ONLY this JSON object, filled in, with no extra text:
{OUTPUT_SCHEMA_TEMPLATE}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_repair_messages(previous_reply: str) -> list:
    """Follow-up message used to fix a malformed / schema-mismatched JSON reply."""
    return [
        {
            "role": "user",
            "content": (
                "Your previous reply was not a single valid JSON object matching the "
                "required schema (it was empty, malformed, wrapped in markdown, or missing "
                "required keys). Return ONLY the corrected JSON object — no markdown, no "
                "code fences, no explanation. It must contain every top-level key: "
                "shared_facts, person_a, person_b, divergence_point, ambiguous_phrases, "
                "questions_for_a_to_ask_b, questions_for_b_to_ask_a, reworded_concerns, "
                "remaining_open_points.\n\n"
                f"Here is what you returned before:\n{previous_reply[:4000]}"
            ),
        }
    ]
