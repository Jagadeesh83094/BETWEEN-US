"""BETWEEN US — The Meaning Mirror.

A single-device ("pass the phone") Streamlit app that helps two people see the
meaning gap between their two accounts of the same misunderstanding.

Run with:  streamlit run app.py

Design notes:
  * ONE browser session = ONE device that is physically passed between the two
    people. We never show one person's raw account to the other before consent.
  * Nothing is stored anywhere except st.session_state (in-memory, per session).
    Audio is transcribed on the fly and never written to disk by this app.
  * All API calls live in services/sarvam_client.py; prompts in prompts/.
"""

from __future__ import annotations

import html as _html

import streamlit as st
from dotenv import load_dotenv

from data.demo_accounts import DEMO_ACCOUNT_A, DEMO_ACCOUNT_B, DEMO_LANGUAGE
from services import analysis as analysis_engine
from services import sarvam_client as sarvam

load_dotenv()

st.set_page_config(
    page_title="BETWEEN US — The Meaning Mirror",
    page_icon="🪞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Styling — clean, readable, card-based, no clutter
# ---------------------------------------------------------------------------
CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"], .stApp { font-family: 'Inter', -apple-system, Segoe UI, Roboto, sans-serif; }
  .block-container { max-width: 880px; padding-top: 2.2rem; padding-bottom: 4rem; }

  .bu-tagline { font-size: 1.05rem; color: #5b5b7a; margin-top: -0.4rem; }
  .bu-hero h1 { font-size: 2.2rem; margin-bottom: 0.2rem; letter-spacing: -0.02em; }
  .bu-notice {
    background: #f5f5fb; border: 1px solid #e6e6f2; border-radius: 12px;
    padding: 0.8rem 1rem; font-size: 0.86rem; color: #4a4a66; margin: 0.6rem 0;
  }
  .bu-notice b { color: #33334d; }

  .bu-card {
    background: #ffffff; border: 1px solid #e8e8f2; border-radius: 14px;
    padding: 1rem 1.2rem; margin: 0.55rem 0; box-shadow: 0 1px 3px rgba(24,24,60,0.05);
  }
  .bu-card-title { font-weight: 700; font-size: 1.0rem; color: #22223a; margin-bottom: 0.45rem; }
  .bu-card-main { border-left: 5px solid #6c5ce7; background: #faf9ff; }
  .bu-card-a { border-left: 4px solid #2d9cdb; }
  .bu-card-b { border-left: 4px solid #e08a3c; }
  .bu-card-main .bu-card-title { color: #4b3fbf; }

  .bu-hyp { color: #6d6d8c; font-size: 0.8rem; font-style: italic; }
  .bu-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: #8a8aa8; font-weight: 600; }
  .bu-quote { color: #4a4a66; font-style: italic; }
  .bu-phrase { font-size: 1.05rem; font-weight: 600; color: #22223a; }
  .bu-pill { display:inline-block; font-size:0.7rem; padding:1px 8px; border-radius:999px; background:#eef; color:#4b3fbf; }
  .bu-list { margin: 0.2rem 0 0 0; padding-left: 1.1rem; color:#33334d; }
  .bu-list li { margin-bottom: 0.28rem; }
  .bu-muted { color:#8a8aa8; font-size:0.85rem; }
  .bu-pass {
    text-align:center; padding: 2.2rem 1rem; background:#faf9ff; border:1px dashed #c9c2f5;
    border-radius:16px; margin: 1rem 0;
  }
  .bu-pass h2 { margin: 0 0 0.3rem 0; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(value) -> str:
    return _html.escape(str(value))


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state() -> None:
    defaults = {
        "screen": "home",
        "lang_a": "English",
        "lang_b": "English",
        "text_a": "",
        "text_b": "",
        "consent_a": False,
        "consent_b": False,
        "result": None,
        "analysis_error": None,
        "corrections": {"person_a": "", "person_b": ""},
        "demo_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def goto(screen: str) -> None:
    st.session_state["screen"] = screen
    st.rerun()


LANG_LABELS = [label for label, _ in sarvam.LANGUAGE_CHOICES]
LANG_CODE = {label: code for label, code in sarvam.LANGUAGE_CHOICES}


# ---------------------------------------------------------------------------
# Small render helpers
# ---------------------------------------------------------------------------
def card(title: str, inner_html: str, cls: str = "") -> None:
    st.markdown(
        f'<div class="bu-card {cls}"><div class="bu-card-title">{esc(title)}</div>'
        f"{inner_html}</div>",
        unsafe_allow_html=True,
    )


def html_list(items: list, empty_text: str = "Not enough information.") -> str:
    clean = [str(i).strip() for i in (items or []) if str(i).strip()]
    if not clean:
        return f'<div class="bu-muted">{esc(empty_text)}</div>'
    lis = "".join(f"<li>{esc(i)}</li>" for i in clean)
    return f'<ul class="bu-list">{lis}</ul>'


def read_upload(uploaded) -> bytes:
    if uploaded is None:
        return b""
    if hasattr(uploaded, "getvalue"):
        return uploaded.getvalue()
    data = uploaded.read()
    return data if isinstance(data, bytes) else bytes(data)


# ---------------------------------------------------------------------------
# Screen 1 — Home
# ---------------------------------------------------------------------------
def screen_home() -> None:
    st.markdown(
        '<div class="bu-hero"><h1>BETWEEN US 🪞</h1>'
        '<div class="bu-tagline">Two perspectives. One conversation. Find the meaning gap.</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "Two people describe the **same** misunderstanding, each in their own words — by "
        "voice or typing, in English, Hindi, Telugu, Tamil, Kannada, or a mix like Hinglish "
        "or Tenglish. BETWEEN US lays the two accounts side by side and shows you where they "
        "meet and where they quietly split: the facts you both agree on, the first moment your "
        "understanding diverged, the two readings of that moment, the phrases that may have "
        "meant different things to each of you, questions to ask each other, and a kinder "
        "reword of each person's main concern."
    )

    st.markdown(
        '<div class="bu-notice">'
        "<b>How to use it:</b> this runs on <b>one device that you pass between you</b>. "
        "Person A records or types first; the screen is then hidden behind a “pass the device” "
        "step; Person B does the same. The analysis only appears once <b>both</b> of you tick the "
        "consent box. Neither person's raw account is shown to the other before consent."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bu-notice">'
        "<b>What this is not:</b> it never reads minds, never judges who is right, and never "
        "claims to detect feelings from your voice. Every inference is shown as a "
        "<i>hypothesis you can correct</i>. It only uses the feelings and needs you actually "
        "stated. This tool supports communication and <b>does not replace professional "
        "counselling</b> — if things feel heavy, please reach out to a qualified counsellor."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bu-notice">'
        "<b>Privacy:</b> your audio and text are kept only in this browser session's memory "
        "(Streamlit session state) and are discarded when the session ends. Audio is sent to "
        "Sarvam AI only to be transcribed, then it is gone. Nothing is saved to a database or "
        "to disk by this app."
        "</div>",
        unsafe_allow_html=True,
    )

    if not sarvam.api_key_present():
        st.warning(
            "No SARVAM_API_KEY detected. Copy `.env.example` to `.env` and add your key "
            "from https://dashboard.sarvam.ai — or press **Load demo** to see the flow "
            "(the demo still needs a key for the analysis step)."
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Start", type="primary", use_container_width=True, key="btn_start"):
            goto("input_a")
    with col2:
        if st.button("Load demo", use_container_width=True, key="btn_demo"):
            st.session_state["text_a"] = DEMO_ACCOUNT_A
            st.session_state["text_b"] = DEMO_ACCOUNT_B
            st.session_state["lang_a"] = "Hinglish / mixed (auto-detect)"
            st.session_state["lang_b"] = "Hinglish / mixed (auto-detect)"
            st.session_state["demo_loaded"] = True
            st.session_state["result"] = None
            st.session_state["analysis_error"] = None
            goto("consent")

    st.markdown(
        '<div class="bu-muted" style="margin-top:1rem">Tip: the demo loads two ready-made '
        "Hinglish accounts (a “fine, do whatever you want” message and a “dekhte hain” reply), "
        "so you can show the whole flow in under two minutes with no microphone.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Screen 2 — Input (rendered once per person)
# ---------------------------------------------------------------------------
def screen_input(person: str) -> None:
    label = "Person A" if person == "a" else "Person B"
    other = "Person B" if person == "a" else "Person A"

    st.subheader(f"{label} — your side of the story")
    st.caption(
        "Describe the same situation in your own words. You can speak or type. "
        "Whatever you enter stays on this device until you both consent."
    )

    st.selectbox(
        "Language you'll use",
        options=LANG_LABELS,
        key=f"lang_{person}",
        help="Pick a single language, or a mixed option (auto-detect) for Hinglish/Tenglish.",
    )

    st.markdown(
        "Try to cover these four things:\n"
        "- **What happened**, in your words\n"
        "- **What you felt** — only what you actually felt\n"
        "- **What you understood** from it\n"
        "- **What you want the other person to understand**"
    )

    method = st.radio(
        "How would you like to add it?",
        options=["🎙️ Record", "📎 Upload audio", "⌨️ Type"],
        key=f"method_{person}",
        horizontal=True,
    )

    audio_bytes, audio_name = b"", ""

    if method == "🎙️ Record":
        if hasattr(st, "audio_input"):
            clip = st.audio_input("Record your account (keep it under 30 seconds)", key=f"rec_{person}")
            if clip is not None:
                audio_bytes, audio_name = read_upload(clip), "recording.webm"
        else:
            st.info("In-browser recording isn't available in this Streamlit version. Please upload a file or type below.")
    elif method == "📎 Upload audio":
        up = st.file_uploader(
            "Upload an audio file (WAV, MP3, M4A, OGG, FLAC — under 30 seconds)",
            type=["wav", "mp3", "m4a", "mp4", "ogg", "opus", "flac", "aac", "webm"],
            key=f"up_{person}",
        )
        if up is not None:
            audio_bytes, audio_name = read_upload(up), up.name

    if method != "⌨️ Type" and audio_bytes:
        if st.button("Transcribe audio", key=f"transcribe_{person}"):
            code = LANG_CODE.get(st.session_state[f"lang_{person}"], "unknown")
            with st.spinner("Transcribing…"):
                try:
                    result = sarvam.transcribe_audio(audio_bytes, audio_name, code)
                    st.session_state[f"text_{person}"] = result["transcript"]
                    st.session_state[f"detected_{person}"] = result.get("language_code")
                    st.rerun()
                except sarvam.MissingApiKeyError as exc:
                    st.error(str(exc))
                except sarvam.TranscriptionError as exc:
                    st.error(str(exc))

    if st.session_state.get(f"detected_{person}"):
        st.caption(f"Detected language: {st.session_state[f'detected_{person}']}")

    st.text_area(
        "Your account (edit freely — fix any transcription errors before submitting)",
        key=f"text_{person}",
        height=220,
        placeholder="Type here, or record/upload above and press Transcribe…",
    )

    st.markdown(
        f'<div class="bu-muted">Nothing is stored on a server. {other} will not see this '
        "until you both consent.</div>",
        unsafe_allow_html=True,
    )

    text = (st.session_state.get(f"text_{person}") or "").strip()
    col_back, col_next = st.columns([1, 2])
    with col_back:
        if st.button("← Back", key=f"back_{person}", use_container_width=True):
            goto("home" if person == "a" else "input_b")
    with col_next:
        if st.button(
            "Submit my account →",
            type="primary",
            use_container_width=True,
            key=f"submit_{person}",
            disabled=not text,
        ):
            if person == "a":
                goto("pass")
            else:
                goto("consent")
    if not text:
        st.caption("Add something above to continue.")


# ---------------------------------------------------------------------------
# Screen 2b — Pass the device (interstitial, hides A's account)
# ---------------------------------------------------------------------------
def screen_pass() -> None:
    st.markdown(
        '<div class="bu-pass"><h2>Pass the device to Person B</h2>'
        '<div class="bu-muted">Person A\'s account is now hidden. Hand the phone or laptop '
        "to the other person.</div></div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Back", key="pass_back", use_container_width=True):
            goto("input_a")
    with col2:
        if st.button("I'm Person B — continue →", type="primary", use_container_width=True, key="pass_go"):
            goto("input_b")


# ---------------------------------------------------------------------------
# Screen 3 — Consent + analysis
# ---------------------------------------------------------------------------
def screen_consent() -> None:
    st.subheader("Consent, then analysis")

    if st.session_state.get("demo_loaded"):
        st.info("Demo loaded: two ready-made Hinglish accounts. Tick both consent boxes, then press Analyze.")

    st.markdown("Both people must agree before anything is analyzed.")
    st.checkbox(
        "Person A: I agree my account can be analyzed alongside the other person's.",
        key="consent_a",
    )
    st.checkbox(
        "Person B: I agree my account can be analyzed alongside the other person's.",
        key="consent_b",
    )

    both_ready = (
        bool(st.session_state.get("consent_a"))
        and bool(st.session_state.get("consent_b"))
        and (st.session_state.get("text_a") or "").strip()
        and (st.session_state.get("text_b") or "").strip()
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("← Back", key="consent_back", use_container_width=True):
            goto("input_b")
    with col2:
        analyze = st.button(
            "Analyze 🔍",
            type="primary",
            use_container_width=True,
            key="btn_analyze",
            disabled=not both_ready,
        )

    if not both_ready:
        st.caption("Both accounts and both consent boxes are needed to analyze.")

    if analyze:
        code_a = LANG_CODE.get(st.session_state.get("lang_a", "English"), "unknown")
        code_b = LANG_CODE.get(st.session_state.get("lang_b", "English"), "unknown")
        with st.spinner("Finding the meaning gap… (this can take a few seconds)"):
            try:
                st.session_state["result"] = analysis_engine.analyze_accounts(
                    st.session_state["text_a"],
                    st.session_state["text_b"],
                    language_a=code_a,
                    language_b=code_b,
                    corrections=st.session_state.get("corrections"),
                )
                st.session_state["analysis_error"] = None
            except sarvam.MissingApiKeyError as exc:
                st.session_state["analysis_error"] = str(exc)
            except sarvam.AnalysisAPIError as exc:
                st.session_state["analysis_error"] = str(exc)
            except analysis_engine.AnalysisValidationError as exc:
                st.session_state["analysis_error"] = str(exc)
            except Exception:  # noqa: BLE001 - last-resort friendly message
                st.session_state["analysis_error"] = (
                    "Something went wrong while analyzing. Please try again."
                )
        if st.session_state.get("analysis_error"):
            st.error(st.session_state["analysis_error"])
        else:
            goto("results")


# ---------------------------------------------------------------------------
# Screen 4 — Results (the Meaning Gap view)
# ---------------------------------------------------------------------------
def screen_results() -> None:
    result = st.session_state.get("result")
    if not result:
        st.info("No analysis yet.")
        if st.button("← Back to consent", key="res_noback"):
            goto("consent")
        return

    st.subheader("The meaning gap")
    st.caption("Everything below is offered as a hypothesis you can correct — not a verdict.")

    # --- Divergence point: the main card, shown first ---
    div = result["divergence_point"]
    inner = (
        f'<div class="bu-label">Where your understandings split</div>'
        f'<div class="bu-phrase" style="margin:0.2rem 0 0.5rem">{esc(div["moment"])}</div>'
        f'<div class="bu-label">Person A\'s reading</div><div>{esc(div["person_a_reading"])}</div>'
        f'<div class="bu-label" style="margin-top:0.6rem">Person B\'s reading</div><div>{esc(div["person_b_reading"])}</div>'
        f'<div class="bu-label" style="margin-top:0.6rem">Why it may have diverged</div>'
        f'<div class="bu-hyp">{esc(div["why_it_may_have_diverged"])}</div>'
    )
    card("The moment you read differently", inner, cls="bu-card-main")

    # --- Side-by-side readings ---
    st.markdown("#### Each person's reading, side by side")
    col_a, col_b = st.columns(2)
    for col, who, key in ((col_a, "Person A", "person_a"), (col_b, "Person B", "person_b")):
        person = result[key]
        with col:
            inner = (
                f'<div class="bu-label">Feelings they stated</div>'
                f'{html_list(person["explicitly_stated_feelings"], "None stated explicitly.")}'
                f'<div class="bu-label" style="margin-top:0.5rem">Needs they stated</div>'
                f'{html_list(person["stated_needs"], "None stated explicitly.")}'
                f'<div class="bu-label" style="margin-top:0.5rem">Readings to confirm</div>'
                f'{html_list(person["interpretations_to_confirm"], "Nothing to confirm.")}'
            )
            card(who, inner, cls="bu-card-a" if key == "person_a" else "bu-card-b")

    # --- Ambiguous phrases ---
    st.markdown("#### Phrases that may have meant different things")
    phrases = result["ambiguous_phrases"]
    if not phrases:
        st.markdown('<div class="bu-muted">No ambiguous phrases were identified.</div>', unsafe_allow_html=True)
    for p in phrases:
        inner = (
            f'<div class="bu-phrase">“{esc(p["phrase"])}” '
            f'<span class="bu-pill">{esc(p["language"])}</span></div>'
            f'<div class="bu-label" style="margin-top:0.5rem">May have meant to Person A</div>'
            f'<div>{esc(p["possible_meaning_a"])}</div>'
            f'<div class="bu-label" style="margin-top:0.4rem">May have meant to Person B</div>'
            f'<div>{esc(p["possible_meaning_b"])}</div>'
            f'<div class="bu-hyp" style="margin-top:0.4rem">{esc(p["note"])}</div>'
        )
        card("Ambiguous phrase", inner)

    # --- Shared facts ---
    st.markdown("#### Facts you both agree on")
    facts = result["shared_facts"]
    if not facts:
        st.markdown('<div class="bu-muted">Not enough shared ground was found.</div>', unsafe_allow_html=True)
    for f in facts:
        inner = (
            f'<div>{esc(f["statement"])} <span class="bu-pill">{esc(f["confidence"])} confidence</span></div>'
            f'<div class="bu-label" style="margin-top:0.4rem">Person A</div><div class="bu-quote">“{esc(f["evidence_a"])}”</div>'
            f'<div class="bu-label" style="margin-top:0.3rem">Person B</div><div class="bu-quote">“{esc(f["evidence_b"])}”</div>'
        )
        card("Shared fact", inner)

    # --- Questions each can ask the other ---
    st.markdown("#### Questions to ask each other")
    col_qa, col_qb = st.columns(2)
    with col_qa:
        card("For Person A to ask Person B", html_list(result["questions_for_a_to_ask_b"]), cls="bu-card-a")
    with col_qb:
        card("For Person B to ask Person A", html_list(result["questions_for_b_to_ask_a"]), cls="bu-card-b")

    # --- Reworded concerns ---
    st.markdown("#### A kinder way to say each concern")
    col_ra, col_rb = st.columns(2)
    with col_ra:
        card("Person A, reworded", f'<div>{esc(result["reworded_concerns"]["person_a"])}</div>', cls="bu-card-a")
    with col_rb:
        card("Person B, reworded", f'<div>{esc(result["reworded_concerns"]["person_b"])}</div>', cls="bu-card-b")

    # --- Open points ---
    st.markdown("#### Still open")
    st.markdown(html_list(result["remaining_open_points"], "Nothing flagged as open."), unsafe_allow_html=True)

    # --- Edit / This isn't what I meant ---
    st.markdown("---")
    st.markdown("#### “This isn't what I meant”")
    st.caption(
        "Correct any hypothesis above, in your own words, and re-run the analysis. "
        "Your correction is treated as authoritative."
    )
    col_ea, col_eb = st.columns(2)
    for col, who, key in ((col_ea, "Person A", "person_a"), (col_eb, "Person B", "person_b")):
        with col:
            with st.expander(f"{who}: correct a reading"):
                st.text_area(
                    "What did I actually mean?",
                    key=f"corr_{key}",
                    height=120,
                    placeholder="e.g. When I said 'dekhte hain' I meant 'I need a day to think', not 'no'.",
                )
                if st.button(f"Re-analyze with {who}'s correction", key=f"reanalyze_{key}", use_container_width=True):
                    corrections = dict(st.session_state.get("corrections") or {})
                    corrections[key] = st.session_state.get(f"corr_{key}", "")
                    st.session_state["corrections"] = corrections
                    _rerun_analysis()

    # --- Notices ---
    st.markdown(
        '<div class="bu-notice">'
        "<b>Reminder:</b> this supports communication and does not replace professional "
        "counselling. Nothing here is a diagnosis or a verdict, and no one is being scored. "
        "Your audio and text lived only in this session's memory and are gone when you close it."
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("Start over", key="res_restart"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        goto("home")


def _rerun_analysis() -> None:
    code_a = LANG_CODE.get(st.session_state.get("lang_a", "English"), "unknown")
    code_b = LANG_CODE.get(st.session_state.get("lang_b", "English"), "unknown")
    with st.spinner("Re-analyzing with your correction…"):
        try:
            st.session_state["result"] = analysis_engine.analyze_accounts(
                st.session_state["text_a"],
                st.session_state["text_b"],
                language_a=code_a,
                language_b=code_b,
                corrections=st.session_state.get("corrections"),
            )
            st.session_state["analysis_error"] = None
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't re-run the analysis: {exc}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
SCREENS = {
    "home": screen_home,
    "input_a": lambda: screen_input("a"),
    "pass": screen_pass,
    "input_b": lambda: screen_input("b"),
    "consent": screen_consent,
    "results": screen_results,
}


def main() -> None:
    init_state()
    screen = st.session_state.get("screen", "home")
    SCREENS.get(screen, screen_home)()


if __name__ == "__main__":
    main()
