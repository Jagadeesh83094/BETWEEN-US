"""Session state manager for BETWEEN US — The Meaning Mirror.

Controls single-device flow:
Screen 1: Home
Screen 2A: Input Person A
Interstitial: Pass the device to Person B
Screen 2B: Input Person B
Screen 3: Consent & Analysis
Screen 4: Meaning Gap Results (with Corrections & Re-analysis)
"""

import streamlit as st
from data.demo_data import DEMO_SCENARIO_HINGLISH


def init_session_state():
    """Initializes default keys in streamlit session state if not already set."""
    defaults = {
        # Screen state: 'home', 'input_a', 'pass_to_b', 'input_b', 'consent', 'results'
        "screen": "home",
        
        # Participant names or designations
        "name_a": "Person A",
        "name_b": "Person B",
        
        # Selected input language
        "lang_a": "Auto-detect / Mixed (Hinglish, Tenglish, etc.)",
        "lang_b": "Auto-detect / Mixed (Hinglish, Tenglish, etc.)",
        
        # Input accounts
        "account_a": "",
        "account_b": "",
        
        # Editable draft buffers before submission
        "draft_a": "",
        "draft_b": "",
        
        # Transcription status or notices
        "stt_status_a": None,
        "stt_status_b": None,
        
        # Consent status
        "consent_a": False,
        "consent_b": False,
        
        # Analysis result
        "analysis_result": None,
        "is_analyzing": False,
        "analysis_error": None,
        
        # User corrections for re-analysis ("Edit / This isn't what I meant")
        "corrections_a": "",
        "corrections_b": "",
        "show_edit_a": False,
        "show_edit_b": False,
        
        # Demo flag
        "is_demo": False,
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_all_data():
    """Wipes all entered accounts, consent, and results from session state."""
    st.session_state["screen"] = "home"
    st.session_state["account_a"] = ""
    st.session_state["account_b"] = ""
    st.session_state["draft_a"] = ""
    st.session_state["draft_b"] = ""
    st.session_state["stt_status_a"] = None
    st.session_state["stt_status_b"] = None
    st.session_state["consent_a"] = False
    st.session_state["consent_b"] = False
    st.session_state["analysis_result"] = None
    st.session_state["is_analyzing"] = False
    st.session_state["analysis_error"] = None
    st.session_state["corrections_a"] = ""
    st.session_state["corrections_b"] = ""
    st.session_state["show_edit_a"] = False
    st.session_state["show_edit_b"] = False
    st.session_state["is_demo"] = False


def load_demo_scenario():
    """Pre-fills session state with Hinglish demo scenario and moves to consent screen."""
    demo = DEMO_SCENARIO_HINGLISH
    st.session_state["name_a"] = demo["person_a"]["name"]
    st.session_state["name_b"] = demo["person_b"]["name"]
    st.session_state["account_a"] = demo["person_a"]["text"]
    st.session_state["account_b"] = demo["person_b"]["text"]
    st.session_state["draft_a"] = demo["person_a"]["text"]
    st.session_state["draft_b"] = demo["person_b"]["text"]
    st.session_state["consent_a"] = True
    st.session_state["consent_b"] = True
    st.session_state["is_demo"] = True
    st.session_state["screen"] = "consent"
    st.session_state["analysis_result"] = None
    st.session_state["analysis_error"] = None
