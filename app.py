"""BETWEEN US — The Meaning Mirror
Hackathon Prototype for Interpersonal Understanding and Nuance Resolution.
"""

import os
import streamlit as st
from dotenv import load_dotenv

from utils.state_manager import init_session_state, reset_all_data, load_demo_scenario
from services.sarvam_client import (
    transcribe_audio_file,
    analyze_perspectives,
    SarvamServiceError,
    LANGUAGE_CODE_MAP,
)

# Page configuration
st.set_page_config(
    page_title="BETWEEN US — The Meaning Mirror",
    page_icon="🪞",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load environment variables
load_dotenv()

# Initialize session state variables
init_session_state()

# Inject custom stylesheet
def inject_custom_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles", "theme.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

inject_custom_css()


def render_header():
    """Renders the top branding and hero tagline."""
    st.markdown(
        """
        <div class="hero-header">
            <div class="hero-title">BETWEEN US</div>
            <div class="hero-subtitle">The Meaning Mirror</div>
            <div class="hero-description">
                Two perspectives. One conversation. Find the meaning gap.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def check_api_key_banner():
    """Shows API key status or provides setup option if missing from .env."""
    current_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not current_key:
        with st.expander("⚠️ Sarvam API Key Required to Run Analysis", expanded=True):
            st.warning(
                "No `SARVAM_API_KEY` was detected in your `.env` file. "
                "You can still explore the preloaded Hinglish Demo, or enter your key below for live analysis."
            )
            col_k1, col_k2 = st.columns([3, 1])
            temp_key = col_k1.text_input(
                "Enter Sarvam API Key (held in memory only)",
                type="password",
                help="Never stored on disk or logged.",
            )
            if col_k2.button("Apply Key", use_container_width=True) and temp_key.strip():
                os.environ["SARVAM_API_KEY"] = temp_key.strip()
                st.success("API key set for this session!")
                st.rerun()


# ==============================================================================
# SCREEN 1: HOME
# ==============================================================================
def render_screen_home():
    """Renders Screen 1: Overview, Disclaimers, and Launch Options."""
    col_main, _ = st.columns([1, 0.01])
    with col_main:
        st.markdown(
            """
            <div class="mirror-card">
                <h3 style="margin-top:0; color:#f8fafc; font-weight:700;">Why Conversations Diverge</h3>
                <p style="color:#cbd5e1; font-size:1.05rem; line-height:1.7;">
                    Misunderstandings rarely happen because of ill intent. More often, the exact same moment, 
                    hesitant pause, or everyday phrase carries two completely different realities to each person. 
                    A polite <em>"dekhte hain"</em> or <em>"chuddam"</em> might mean <em>"I need time"</em> to one, 
                    yet sound like a green light to another.
                </p>
                <p style="color:#cbd5e1; font-size:1.05rem; line-height:1.7;">
                    <strong>BETWEEN US</strong> acts as a neutral mirror for single-device shared dialogue. 
                    Each person describes what happened in their own words. The mirror reflects back the 
                    unspoken assumptions, pinpoints the exact fork in understanding, and suggests kinder ways forward.
                </p>
                <div class="counselling-alert">
                    <strong>Notice:</strong> This tool is created to foster empathetic communication and self-reflection. 
                    It is an AI communication aid and does not replace professional therapy, counselling, or mediation.
                </div>
                <div class="privacy-notice">
                    🔒 <strong>Privacy Guarantee:</strong> Designed for one phone or laptop passed between two people. 
                    Neither participant's account is revealed to the other until both give explicit mutual consent. 
                    No audio, transcripts, or personal data are stored in any database; everything lives solely in 
                    temporary session memory.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("🚀 Start New Conversation", type="primary", use_container_width=True):
                st.session_state["screen"] = "input_a"
                st.rerun()

        with col_btn2:
            if st.button("⚡ Load Demo Scenario (Hinglish)", use_container_width=True):
                load_demo_scenario()
                st.rerun()


# ==============================================================================
# SCREEN 2: INPUT (PERSON A & PERSON B)
# ==============================================================================
def render_screen_input(person_id: str):
    """Renders Screen 2: Audio Recording, File Upload, or Text Input with Guided Prompts."""
    is_a = person_id == "a"
    name_key = "name_a" if is_a else "name_b"
    lang_key = "lang_a" if is_a else "lang_b"
    draft_key = "draft_a" if is_a else "draft_b"
    account_key = "account_a" if is_a else "account_b"
    badge_class = "badge-a" if is_a else "badge-b"
    person_label = "Person A" if is_a else "Person B"
    step_str = "Step 1 of 3: Person A's Perspective" if is_a else "Step 2 of 3: Person B's Perspective"

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <div>
                <span class="{badge_class}">{person_label}</span>
                <span style="color:#94a3b8; font-size:0.9rem; margin-left:0.5rem;">{step_str}</span>
            </div>
            <div style="color:#64748b; font-size:0.85rem;">Confidential until consent</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_meta1, col_meta2 = st.columns([1, 1.5])
    with col_meta1:
        st.session_state[name_key] = st.text_input(
            "Your Name / Alias:",
            value=st.session_state[name_key],
            key=f"input_name_{person_id}",
        )
    with col_meta2:
        lang_options = list(LANGUAGE_CODE_MAP.keys())
        default_index = (
            lang_options.index(st.session_state[lang_key])
            if st.session_state[lang_key] in lang_options
            else 0
        )
        st.session_state[lang_key] = st.selectbox(
            "Language you will speak or type in:",
            options=lang_options,
            index=default_index,
            key=f"input_lang_{person_id}",
            help="Sarvam AI speech recognition supports English, Hindi, Telugu, Tamil, Kannada, and code-mixed speech.",
        )

    st.markdown(
        """
        <div style="background:rgba(30,41,59,0.3); border-radius:10px; padding:0.9rem 1.1rem; margin:1rem 0; border:1px solid rgba(255,255,255,0.06);">
            <div style="font-weight:600; color:#e2e8f0; font-size:0.92rem; margin-bottom:0.4rem;">💡 Guide your account using these 4 prompts:</div>
            <ul style="margin:0; padding-left:1.2rem; color:#94a3b8; font-size:0.88rem; line-height:1.5;">
                <li><strong>What happened:</strong> The observable facts and events as you experienced them</li>
                <li><strong>What you felt:</strong> Feelings you explicitly experienced (e.g., confused, hurt, overwhelmed)</li>
                <li><strong>What you understood:</strong> What you thought the other person meant or intended</li>
                <li><strong>What you want them to understand:</strong> What was really important to you</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Input Mode Tabs
    tab_voice, tab_upload, tab_type = st.tabs(
        ["🎙️ Record Audio", "📁 Upload Audio File", "✍️ Type / Paste Directly"]
    )

    # Tab 1: Audio Recording
    with tab_voice:
        st.markdown(
            "<p style='color:#94a3b8; font-size:0.88rem;'>Record your voice describing what happened in your chosen language.</p>",
            unsafe_allow_html=True,
        )
        # Check if st.audio_input is available in this Streamlit version
        audio_recorded = None
        if hasattr(st, "audio_input"):
            audio_recorded = st.audio_input(
                "Click microphone to record", key=f"audio_mic_{person_id}"
            )
        else:
            st.info("Browser microphone input is not natively supported in this environment. Please use the file upload or direct text tab.")

        if audio_recorded is not None:
            st.audio(audio_recorded)
            if st.button(f"⚡ Transcribe Audio with Sarvam STT", key=f"btn_transcribe_mic_{person_id}"):
                with st.spinner("Transcribing audio using Sarvam AI Speech-to-Text..."):
                    try:
                        audio_bytes = audio_recorded.getvalue()
                        transcript, detected = transcribe_audio_file(
                            audio_bytes,
                            filename="recording.wav",
                            language_choice=st.session_state[lang_key],
                        )
                        if transcript:
                            st.session_state[draft_key] = transcript
                            st.success(f"Transcription complete! (Detected: {detected or 'Auto'})")
                            st.rerun()
                        else:
                            st.warning("No speech detected in the recording. Please try speaking closer to the mic.")
                    except SarvamServiceError as se:
                        st.error(str(se))

    # Tab 2: Audio File Upload
    with tab_upload:
        st.markdown(
            "<p style='color:#94a3b8; font-size:0.88rem;'>Upload an audio recording (.wav, .mp3, .m4a, .ogg) up to 25MB.</p>",
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "mp3", "m4a", "ogg", "aac", "webm"],
            key=f"audio_file_{person_id}",
        )
        if uploaded_file is not None:
            st.audio(uploaded_file)
            if st.button(f"⚡ Transcribe Uploaded File", key=f"btn_transcribe_file_{person_id}"):
                with st.spinner("Transcribing audio using Sarvam AI Speech-to-Text..."):
                    try:
                        audio_bytes = uploaded_file.getvalue()
                        transcript, detected = transcribe_audio_file(
                            audio_bytes,
                            filename=uploaded_file.name,
                            language_choice=st.session_state[lang_key],
                        )
                        if transcript:
                            st.session_state[draft_key] = transcript
                            st.success(f"Transcription complete! (Detected: {detected or 'Auto'})")
                            st.rerun()
                        else:
                            st.warning("No speech detected in the audio file.")
                    except SarvamServiceError as se:
                        st.error(str(se))

    # Tab 3: Type Directly
    with tab_type:
        st.markdown(
            "<p style='color:#94a3b8; font-size:0.88rem;'>Type or paste your account directly in English, Hindi, Telugu, Tamil, Kannada, or code-mixed text.</p>",
            unsafe_allow_html=True,
        )

    # Editable Draft Area (Always visible so transcribed or typed text can be reviewed & edited)
    st.markdown("---")
    st.markdown(
        "<div style='font-weight:600; color:#e2e8f0; font-size:0.95rem; margin-bottom:0.25rem;'>Your Account (Review & Edit):</div>",
        unsafe_allow_html=True,
    )
    
    current_draft = st.text_area(
        label="Account text",
        label_visibility="collapsed",
        value=st.session_state[draft_key],
        height=220,
        placeholder="What happened:\n...\n\nWhat I felt:\n...\n\nWhat I understood:\n...\n\nWhat I want the other person to understand:\n...",
        key=f"textarea_draft_{person_id}",
    )
    st.session_state[draft_key] = current_draft

    col_sub1, col_sub2 = st.columns([1, 1])
    with col_sub1:
        if st.button("⬅️ Back to Home", key=f"btn_back_{person_id}"):
            st.session_state["screen"] = "home"
            st.rerun()

    with col_sub2:
        btn_label = "Lock Account & Pass Device ➔" if is_a else "Lock Account & Proceed to Consent ➔"
        if st.button(btn_label, type="primary", use_container_width=True, key=f"btn_next_{person_id}"):
            if not current_draft.strip():
                st.error("Please record, upload, or type your account before proceeding.")
            else:
                st.session_state[account_key] = current_draft.strip()
                if is_a:
                    st.session_state["screen"] = "pass_to_b"
                else:
                    st.session_state["screen"] = "consent"
                st.rerun()


# ==============================================================================
# INTERSTITIAL SCREEN: PASS THE DEVICE
# ==============================================================================
def render_screen_pass_to_b():
    """Renders the interstitial privacy screen between Person A and Person B."""
    st.markdown(
        """
        <div class="pass-device-screen">
            <div class="pass-device-icon">📱 ➔ 👤</div>
            <h2 style="color:#ffffff; font-weight:700; margin-bottom:0.5rem;">Pass the Device to Person B</h2>
            <p style="color:#94a3b8; font-size:1.1rem; max-width:550px; margin:0 auto 1.5rem auto;">
                Person A's account has been securely sealed and hidden. Please hand this device to Person B 
                so they can describe the misunderstanding from their perspective without influence.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p2:
        if st.button("I am Person B — Ready to Share My Perspective ➔", type="primary", use_container_width=True):
            st.session_state["screen"] = "input_b"
            st.rerun()


# ==============================================================================
# SCREEN 3: CONSENT & ANALYSIS
# ==============================================================================
def render_screen_consent():
    """Renders Screen 3: Mutual Consent and Trigger for Sarvam Chat Analysis."""
    name_a = st.session_state["name_a"]
    name_b = st.session_state["name_b"]

    st.markdown(
        """
        <div class="hero-header" style="padding-bottom:1rem; margin-bottom:1.5rem;">
            <div style="font-size:1.75rem; font-weight:700; color:#f8fafc;">Mutual Consent & Mirror Reveal</div>
            <div style="color:#94a3b8; font-size:0.95rem;">
                Step 3 of 3: Both participants must agree before any comparison is generated.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mirror-card">
            <div style="font-weight:600; color:#e2e8f0; font-size:1.1rem; margin-bottom:0.75rem;">
                Status of Recorded Perspectives
            </div>
            <div style="display:flex; flex-direction:column; gap:0.5rem; margin-bottom:1rem;">
                <div style="display:flex; align-items:center; gap:0.5rem; color:#cbd5e1;">
                    <span style="color:#22c55e;">✔</span> <strong>{name_a}:</strong> Perspective recorded and sealed ({len(st.session_state['account_a'])} characters)
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem; color:#cbd5e1;">
                    <span style="color:#22c55e;">✔</span> <strong>{name_b}:</strong> Perspective recorded and sealed ({len(st.session_state['account_b'])} characters)
                </div>
            </div>
            <p style="color:#94a3b8; font-size:0.9rem; line-height:1.5;">
                In accordance with our strict confidentiality rules, neither person's raw submission will be displayed 
                unless mutual consent is given. The Meaning Mirror will analyze the accounts side-by-side to find the 
                divergence point, clarify ambiguous phrasing, and suggest kinder rewordings.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state["consent_a"] = st.checkbox(
            f"**{name_a}:** I agree my account can be analyzed alongside {name_b}'s.",
            value=st.session_state["consent_a"],
            key="chk_consent_a",
        )
    with col_c2:
        st.session_state["consent_b"] = st.checkbox(
            f"**{name_b}:** I agree my account can be analyzed alongside {name_a}'s.",
            value=st.session_state["consent_b"],
            key="chk_consent_b",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    both_consented = st.session_state["consent_a"] and st.session_state["consent_b"]

    col_act1, col_act2, col_act3 = st.columns([1, 2, 1])
    with col_act2:
        if st.button(
            "✨ Reveal the Meaning Mirror",
            type="primary",
            disabled=not both_consented,
            use_container_width=True,
            key="btn_trigger_analysis",
        ):
            with st.spinner("Reflecting perspectives through Sarvam AI... Pinpointing the divergence moment..."):
                try:
                    result = analyze_perspectives(
                        account_a=st.session_state["account_a"],
                        account_b=st.session_state["account_b"],
                        corrections_a=st.session_state.get("corrections_a", ""),
                        corrections_b=st.session_state.get("corrections_b", ""),
                    )
                    st.session_state["analysis_result"] = result
                    st.session_state["analysis_error"] = None
                    st.session_state["screen"] = "results"
                    st.rerun()
                except SarvamServiceError as e:
                    st.session_state["analysis_error"] = str(e)
                    st.error(str(e))

    if not both_consented:
        st.info("Both participants must tick their consent box above to unlock the analysis.")


# ==============================================================================
# SCREEN 4: RESULTS (THE MEANING GAP VIEW)
# ==============================================================================
def render_screen_results():
    """Renders Screen 4: Divergence Point, Side-by-Side Readings, Ambiguous Phrases, and Feedback."""
    data = st.session_state.get("analysis_result")
    if not data:
        st.error("No analysis results found. Please run the analysis first.")
        if st.button("Back to Consent"):
            st.session_state["screen"] = "consent"
            st.rerun()
        return

    name_a = st.session_state.get("name_a", "Person A")
    name_b = st.session_state.get("name_b", "Person B")

    st.markdown(
        """
        <div style="text-align:center; margin-bottom:2rem;">
            <div style="font-size:2rem; font-weight:800; color:#ffffff;">The Meaning Mirror</div>
            <div style="color:#38bdf8; font-style:italic; font-family:'Lora',serif; font-size:1.15rem;">
                Where two understandings met and branched
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # 1. THE DIVERGENCE POINT (HERO CARD)
    # -------------------------------------------------------------------------
    div_point = data.get("divergence_point", {})
    moment_text = div_point.get("moment", "Exact turning point")
    why_text = div_point.get("why_it_may_have_diverged", "")

    st.markdown(
        f"""
        <div class="divergence-card">
            <div class="divergence-title">
                <span>📍</span> The First Point of Divergence
            </div>
            <div class="moment-quote">
                "{moment_text}"
            </div>
            <div style="color:#cbd5e1; font-size:0.95rem; line-height:1.6;">
                <strong style="color:#e9d5ff;">Why interpretations may have diverged:</strong><br>
                {why_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # 2. TWO DIFFERENT READINGS OF THAT EXACT MOMENT
    # -------------------------------------------------------------------------
    st.markdown(
        "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.75rem;'>The Two Readings of That Moment</div>",
        unsafe_allow_html=True,
    )

    col_read_a, col_read_b = st.columns(2)
    with col_read_a:
        st.markdown(
            f"""
            <div class="perspective-card-a">
                <span class="badge-a">{name_a}'s Reading</span>
                <div class="badge-hypothesis">Hypothesis to confirm</div>
                <div style="color:#fef3c7; font-size:1rem; line-height:1.6; margin-top:0.5rem;">
                    {div_point.get("person_a_reading", "No reading recorded")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_read_b:
        st.markdown(
            f"""
            <div class="perspective-card-b">
                <span class="badge-b">{name_b}'s Reading</span>
                <div class="badge-hypothesis">Hypothesis to confirm</div>
                <div style="color:#e0f2fe; font-size:1rem; line-height:1.6; margin-top:0.5rem;">
                    {div_point.get("person_b_reading", "No reading recorded")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 3. AMBIGUOUS PHRASES & CULTURAL NUANCE
    # -------------------------------------------------------------------------
    ambiguous = data.get("ambiguous_phrases", [])
    if ambiguous:
        st.markdown(
            "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.75rem;'>🗣️ Phrases That Likely Meant Different Things</div>",
            unsafe_allow_html=True,
        )
        for p in ambiguous:
            phrase = p.get("phrase", "")
            lang = p.get("language", "Mixed/Vernacular")
            mean_a = p.get("possible_meaning_a", "")
            mean_b = p.get("possible_meaning_b", "")
            note = p.get("note", "")

            st.markdown(
                f"""
                <div class="phrase-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                        <span class="phrase-term">"{phrase}"</span>
                        <span style="font-size:0.75rem; background:rgba(255,255,255,0.1); color:#cbd5e1; padding:0.2rem 0.5rem; border-radius:10px;">
                            {lang}
                        </span>
                    </div>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:1rem; margin-bottom:0.6rem;">
                        <div style="background:rgba(245,158,11,0.06); padding:0.6rem 0.8rem; border-radius:8px; border-left:3px solid #f59e0b;">
                            <span style="font-size:0.75rem; color:#fbbf24; font-weight:700; text-transform:uppercase;">Could be heard by {name_a} as:</span><br>
                            <span style="color:#f8fafc; font-size:0.92rem;">{mean_a}</span>
                        </div>
                        <div style="background:rgba(56,189,248,0.06); padding:0.6rem 0.8rem; border-radius:8px; border-left:3px solid #38bdf8;">
                            <span style="font-size:0.75rem; color:#7dd3fc; font-weight:700; text-transform:uppercase;">Could be intended by {name_b} as:</span><br>
                            <span style="color:#f8fafc; font-size:0.92rem;">{mean_b}</span>
                        </div>
                    </div>
                    <div style="color:#94a3b8; font-size:0.85rem; font-style:italic;">
                        💡 <strong>Linguistic / Cultural note:</strong> {note}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 4. SHARED FACTS (COMMON GROUND)
    # -------------------------------------------------------------------------
    shared_facts = data.get("shared_facts", [])
    if shared_facts:
        st.markdown(
            "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.75rem;'>🤝 Facts Both Accounts Agree On</div>",
            unsafe_allow_html=True,
        )
        for fact in shared_facts:
            stmt = fact.get("statement", "")
            ev_a = fact.get("evidence_a", "")
            ev_b = fact.get("evidence_b", "")
            conf = fact.get("confidence", "high").capitalize()
            
            conf_color = "#22c55e" if conf.lower() == "high" else "#eab308"

            st.markdown(
                f"""
                <div style="background:rgba(30,41,59,0.4); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:0.9rem 1.1rem; margin-bottom:0.75rem;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <span style="color:#f8fafc; font-weight:600; font-size:0.96rem;">✔ {stmt}</span>
                        <span style="font-size:0.72rem; color:{conf_color}; border:1px solid {conf_color}; padding:0.15rem 0.45rem; border-radius:8px;">
                            {conf} Confidence
                        </span>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-top:0.5rem; font-size:0.83rem; color:#94a3b8;">
                        <div><strong style="color:#f59e0b;">{name_a}:</strong> "{ev_a}"</div>
                        <div><strong style="color:#38bdf8;">{name_b}:</strong> "{ev_b}"</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 5. EXPLICITLY STATED FEELINGS & NEEDS (STRICT RULE ENFORCEMENT)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div style="font-size:1.15rem; font-weight:700; color:#f8fafc;">💭 Explicitly Stated Feelings & Needs</div>
            <div style="font-size:0.78rem; color:#94a3b8; font-style:italic;">Only directly articulated words; never inferred</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_feel_a, col_feel_b = st.columns(2)
    person_a_info = data.get("person_a", {})
    person_b_info = data.get("person_b", {})

    with col_feel_a:
        feelings_a = person_a_info.get("explicitly_stated_feelings", [])
        needs_a = person_a_info.get("stated_needs", [])
        st.markdown(
            f"""
            <div class="perspective-card-a">
                <strong style="color:#fbbf24;">{name_a}'s Explicit Words:</strong>
                <p style="margin:0.5rem 0 0.25rem 0; font-size:0.88rem; color:#cbd5e1;">
                    <strong>Feelings Stated:</strong> {", ".join(feelings_a) if feelings_a else "None explicitly stated"}
                </p>
                <p style="margin:0; font-size:0.88rem; color:#cbd5e1;">
                    <strong>Needs Stated:</strong> {", ".join(needs_a) if needs_a else "None explicitly stated"}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_feel_b:
        feelings_b = person_b_info.get("explicitly_stated_feelings", [])
        needs_b = person_b_info.get("stated_needs", [])
        st.markdown(
            f"""
            <div class="perspective-card-b">
                <strong style="color:#7dd3fc;">{name_b}'s Explicit Words:</strong>
                <p style="margin:0.5rem 0 0.25rem 0; font-size:0.88rem; color:#cbd5e1;">
                    <strong>Feelings Stated:</strong> {", ".join(feelings_b) if feelings_b else "None explicitly stated"}
                </p>
                <p style="margin:0; font-size:0.88rem; color:#cbd5e1;">
                    <strong>Needs Stated:</strong> {", ".join(needs_b) if needs_b else "None explicitly stated"}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 6. QUESTIONS EACH PERSON CAN ASK THE OTHER
    # -------------------------------------------------------------------------
    st.markdown(
        "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.75rem;'>❓ Questions to Bridge Understanding</div>",
        unsafe_allow_html=True,
    )

    q_a_to_b = data.get("questions_for_a_to_ask_b", [])
    q_b_to_a = data.get("questions_for_b_to_ask_a", [])

    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.markdown(f"<div style='font-weight:600; color:#fbbf24; margin-bottom:0.5rem;'>For {name_a} to Ask {name_b}:</div>", unsafe_allow_html=True)
        if q_a_to_b:
            for q in q_a_to_b:
                st.markdown(f"- *\"{q}\"*")
        else:
            st.markdown("- *No specific question suggested.*")

    with col_q2:
        st.markdown(f"<div style='font-weight:600; color:#7dd3fc; margin-bottom:0.5rem;'>For {name_b} to Ask {name_a}:</div>", unsafe_allow_html=True)
        if q_b_to_a:
            for q in q_b_to_a:
                st.markdown(f"- *\"{q}\"*")
        else:
            st.markdown("- *No specific question suggested.*")

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 7. KINDER REWORDING OF MAIN CONCERNS
    # -------------------------------------------------------------------------
    reworded = data.get("reworded_concerns", {})
    st.markdown(
        "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.75rem;'>🕊️ Kinder Rewording of Core Concerns</div>",
        unsafe_allow_html=True,
    )

    col_rew1, col_rew2 = st.columns(2)
    with col_rew1:
        st.markdown(
            f"""
            <div style="background:rgba(245,158,11,0.06); border:1px solid rgba(245,158,11,0.25); border-radius:10px; padding:1rem;">
                <span style="font-size:0.75rem; color:#fbbf24; font-weight:700; text-transform:uppercase;">{name_a}'s concern, reframed for connection:</span>
                <p style="margin:0.5rem 0 0 0; color:#f8fafc; font-size:0.95rem; font-family:'Lora',serif; font-style:italic;">
                    "{reworded.get('person_a', 'Not enough information to reword')}"
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_rew2:
        st.markdown(
            f"""
            <div style="background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.25); border-radius:10px; padding:1rem;">
                <span style="font-size:0.75rem; color:#7dd3fc; font-weight:700; text-transform:uppercase;">{name_b}'s concern, reframed for connection:</span>
                <p style="margin:0.5rem 0 0 0; color:#f8fafc; font-size:0.95rem; font-family:'Lora',serif; font-style:italic;">
                    "{reworded.get('person_b', 'Not enough information to reword')}"
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 8. REMAINING OPEN POINTS
    # -------------------------------------------------------------------------
    open_points = data.get("remaining_open_points", [])
    if open_points:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:1.15rem; font-weight:700; color:#f8fafc; margin-bottom:0.5rem;'>🧭 Open Points for Future Dialogue</div>",
            unsafe_allow_html=True,
        )
        for op in open_points:
            st.markdown(f"- ⏳ {op}")

    st.markdown("<br><hr style='border-color:rgba(255,255,255,0.08);'><br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 9. INTERACTIVE CORRECTION & RE-ANALYSIS ("This isn't what I meant")
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.15rem; font-weight:700; color:#f8fafc;">✏️ Clarify or Correct Any Inferences</div>
            <div style="color:#94a3b8; font-size:0.88rem;">
                Every inference above is a hypothesis. If something doesn't match your true intent, add a clarification below and re-run.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_cor1, col_cor2 = st.columns(2)
    with col_cor1:
        with st.expander(f"📝 {name_a}: 'This isn't what I meant'"):
            cor_a = st.text_area(
                f"Clarification from {name_a}:",
                value=st.session_state.get("corrections_a", ""),
                placeholder="e.g., I wasn't assuming he didn't care; I was trying to save money on cab surge...",
                key="input_correction_a",
            )
            st.session_state["corrections_a"] = cor_a

    with col_cor2:
        with st.expander(f"📝 {name_b}: 'This isn't what I meant'"):
            cor_b = st.text_area(
                f"Clarification from {name_b}:",
                value=st.session_state.get("corrections_b", ""),
                placeholder="e.g., When I said 'fine do whatever', I was exhausted from work, not giving permission...",
                key="input_correction_b",
            )
            st.session_state["corrections_b"] = cor_b

    if st.session_state.get("corrections_a") or st.session_state.get("corrections_b"):
        if st.button("🔄 Re-Run Analysis with Clarifications", type="primary"):
            with st.spinner("Re-evaluating with your clarifications..."):
                try:
                    updated_result = analyze_perspectives(
                        account_a=st.session_state["account_a"],
                        account_b=st.session_state["account_b"],
                        corrections_a=st.session_state.get("corrections_a", ""),
                        corrections_b=st.session_state.get("corrections_b", ""),
                    )
                    st.session_state["analysis_result"] = updated_result
                    st.success("Meaning Mirror refreshed with your clarifications!")
                    st.rerun()
                except SarvamServiceError as se:
                    st.error(str(se))

    # -------------------------------------------------------------------------
    # 10. RAW ACCOUNTS & NEW SESSION
    # -------------------------------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📄 View Submitted Accounts Side-by-Side (Consent Granted)"):
        col_raw1, col_raw2 = st.columns(2)
        with col_raw1:
            st.markdown(f"**{name_a}'s Words:**")
            st.text(st.session_state["account_a"])
        with col_raw2:
            st.markdown(f"**{name_b}'s Words:**")
            st.text(st.session_state["account_b"])

    st.markdown("<br>", unsafe_allow_html=True)
    col_end1, col_end2, col_end3 = st.columns([1, 1, 1])
    with col_end2:
        if st.button("🔄 Start New Conversation", use_container_width=True):
            reset_all_data()
            st.rerun()


# ==============================================================================
# MAIN ROUTER
# ==============================================================================
def main():
    render_header()
    check_api_key_banner()

    screen = st.session_state.get("screen", "home")

    if screen == "home":
        render_screen_home()
    elif screen == "input_a":
        render_screen_input("a")
    elif screen == "pass_to_b":
        render_screen_pass_to_b()
    elif screen == "input_b":
        render_screen_input("b")
    elif screen == "consent":
        render_screen_consent()
    elif screen == "results":
        render_screen_results()
    else:
        render_screen_home()


if __name__ == "__main__":
    main()
