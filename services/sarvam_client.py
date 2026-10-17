"""Sarvam AI service wrapper for Speech-to-Text and Meaning Mirror Analysis.

All calls to Sarvam AI APIs are centralized here.
API keys are loaded securely from environment variables and never logged or exposed.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv

# Configure basic module logger (never log credentials)
logger = logging.getLogger("MeaningMirror.SarvamClient")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Language code mappings for Sarvam Speech-to-Text API
# VERIFY AGAINST DOCS: Sarvam STT supported language codes:
# 'en-IN', 'hi-IN', 'te-IN', 'ta-IN', 'kn-IN', 'unknown'
LANGUAGE_CODE_MAP = {
    "Auto-detect / Mixed (Hinglish, Tenglish, etc.)": "unknown",
    "English": "en-IN",
    "Hindi (हिन्दी)": "hi-IN",
    "Telugu (తెలుగు)": "te-IN",
    "Tamil (தமிழ்)": "ta-IN",
    "Kannada (ಕನ್ನಡ)": "kn-IN",
}

# VERIFY AGAINST DOCS: Speech model name 'saaras:v3' is standard; 'saaras:v4' also available in latest SDK
DEFAULT_STT_MODEL = "saaras:v3"

# VERIFY AGAINST DOCS: Chat completion model: 'sarvam-105b-conversations' is the recommended conversational model without reasoning token truncation
DEFAULT_CHAT_MODEL = "sarvam-105b-conversations"

# VERIFY AGAINST DOCS: Sarvam audio file size limit is typically 25MB, max duration ~10 minutes
MAX_AUDIO_BYTES = 25 * 1024 * 1024


class SarvamServiceError(Exception):
    """Custom exception for user-friendly error messages."""
    pass


def get_sarvam_client():
    """Initializes and returns the SarvamAI client using SARVAM_API_KEY from environment."""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key or not api_key.strip():
        raise SarvamServiceError(
            "SARVAM_API_KEY is not set. Please create a .env file with your Sarvam API key or enter it in the settings."
        )

    try:
        from sarvamai import SarvamAI
        # VERIFY AGAINST DOCS: client initialization accepts api_subscription_key
        return SarvamAI(api_subscription_key=api_key.strip())
    except ImportError as e:
        raise SarvamServiceError(
            "The 'sarvamai' package is not installed. Please install it using 'pip install sarvamai'."
        ) from e
    except Exception as e:
        raise SarvamServiceError(f"Failed to initialize Sarvam AI client: {str(e)}")


def transcribe_audio_file(
    file_bytes: bytes,
    filename: str = "audio.wav",
    language_choice: str = "Auto-detect / Mixed (Hinglish, Tenglish, etc.)"
) -> Tuple[str, Optional[str]]:
    """Transcribes an audio file using Sarvam Speech-to-Text API.
    
    Returns:
        Tuple of (transcript_text, detected_language_code)
    """
    if not file_bytes or len(file_bytes) == 0:
        raise SarvamServiceError("Empty audio data received. Please record or upload a valid audio file.")

    if len(file_bytes) > MAX_AUDIO_BYTES:
        raise SarvamServiceError(
            f"Audio file is too large ({len(file_bytes) / (1024 * 1024):.1f}MB). Sarvam limit is 25MB."
        )

    client = get_sarvam_client()
    lang_code = LANGUAGE_CODE_MAP.get(language_choice, "unknown")

    # VERIFY AGAINST DOCS: mode parameter can be 'codemix' for mixed speech or 'transcribe'
    mode = "codemix" if lang_code == "unknown" else "transcribe"

    logger.info(f"Initiating STT transcription with model={DEFAULT_STT_MODEL}, mode={mode}, lang={lang_code}")

    try:
        # Pass file as tuple: (filename, bytes)
        # VERIFY AGAINST DOCS: client.speech_to_text.transcribe accepts file=(filename, bytes) or IO[bytes]
        response = client.speech_to_text.transcribe(
            file=(filename, file_bytes),
            model=DEFAULT_STT_MODEL,
            mode=mode,
            language_code=lang_code,
            with_timestamps=False
        )

        # VERIFY AGAINST DOCS: SpeechToTextResponse has attribute 'transcript' and optional 'language_code'
        transcript = getattr(response, "transcript", None)
        if transcript is None and hasattr(response, "get"):
            transcript = response.get("transcript", "")
            
        detected_lang = getattr(response, "language_code", None)

        if not transcript or not str(transcript).strip():
            return "", detected_lang

        return str(transcript).strip(), detected_lang

    except Exception as error:
        error_name = type(error).__name__
        logger.error(f"STT transcription failed: {error_name} - {str(error)}")
        
        err_msg = str(error).lower()
        if "401" in err_msg or "unauthorized" in err_msg:
            raise SarvamServiceError("Sarvam API authentication failed (401). Please verify your SARVAM_API_KEY.")
        elif "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
            raise SarvamServiceError("Sarvam API rate limit exceeded. Please wait a moment before retrying.")
        elif "timeout" in err_msg or "timed out" in err_msg:
            raise SarvamServiceError("Transcription request timed out. Please check your internet connection and try again.")
        else:
            raise SarvamServiceError(f"Transcription failed: {str(error)}. You can still type your account directly.")


def _clean_json_string(raw: str) -> str:
    """Removes markdown code fences and extraneous text surrounding a JSON response."""
    text = raw.strip()
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    else:
        # Find first '{' and last '}'
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
    return text


def _validate_analysis_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures all mandatory keys from the Meaning Mirror schema exist."""
    required_keys = [
        "shared_facts",
        "person_a",
        "person_b",
        "divergence_point",
        "ambiguous_phrases",
        "questions_for_a_to_ask_b",
        "questions_for_b_to_ask_a",
        "reworded_concerns",
        "remaining_open_points"
    ]
    
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Missing required schema keys: {', '.join(missing)}")

    # Ensure structure defaults
    data.setdefault("shared_facts", [])
    data.setdefault("ambiguous_phrases", [])
    data.setdefault("questions_for_a_to_ask_b", [])
    data.setdefault("questions_for_b_to_ask_a", [])
    data.setdefault("remaining_open_points", [])

    if not isinstance(data.get("person_a"), dict):
        data["person_a"] = {"explicitly_stated_feelings": [], "stated_needs": [], "interpretations_to_confirm": []}
    else:
        data["person_a"].setdefault("explicitly_stated_feelings", [])
        data["person_a"].setdefault("stated_needs", [])
        data["person_a"].setdefault("interpretations_to_confirm", [])

    if not isinstance(data.get("person_b"), dict):
        data["person_b"] = {"explicitly_stated_feelings": [], "stated_needs": [], "interpretations_to_confirm": []}
    else:
        data["person_b"].setdefault("explicitly_stated_feelings", [])
        data["person_b"].setdefault("stated_needs", [])
        data["person_b"].setdefault("interpretations_to_confirm", [])

    if not isinstance(data.get("divergence_point"), dict):
        data["divergence_point"] = {
            "moment": "Point of divergence not clearly identifiable from provided text",
            "person_a_reading": "",
            "person_b_reading": "",
            "why_it_may_have_diverged": ""
        }

    if not isinstance(data.get("reworded_concerns"), dict):
        data["reworded_concerns"] = {"person_a": "", "person_b": ""}

    return data


def analyze_perspectives(
    account_a: str,
    account_b: str,
    corrections_a: str = "",
    corrections_b: str = ""
) -> Dict[str, Any]:
    """Calls the Sarvam chat model to generate the Meaning Mirror analysis.
    
    Enforces strict JSON schema, retries once on malformed JSON, and validates structure.
    """
    from prompts.analysis_prompt import SYSTEM_PROMPT, build_analysis_user_prompt

    if not account_a.strip() or not account_b.strip():
        raise SarvamServiceError("Both Person A and Person B must provide their accounts before analysis.")

    client = get_sarvam_client()
    user_prompt = build_analysis_user_prompt(account_a, account_b, corrections_a, corrections_b)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    logger.info(f"Submitting analysis to Sarvam chat model={DEFAULT_CHAT_MODEL}")

    # VERIFY AGAINST DOCS: client.chat.completions parameters
    # model: 'sarvam-105b'
    # response_format: {'type': 'json_object'}
    # temperature: 0.2
    # max_tokens: 3000
    
    last_error: Optional[Exception] = None
    
    for attempt in range(2):  # Try initial call, retry once if malformed JSON
        try:
            if attempt == 1:
                logger.warning("Retrying analysis call with explicit JSON formatting request...")
                messages.append({
                    "role": "user",
                    "content": "CRITICAL: The previous output could not be parsed as valid JSON. Return ONLY the strict JSON object with all required keys."
                })

            response = client.chat.completions(
                model=DEFAULT_CHAT_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=3000
            )

            raw_text = response.choices[0].message.content
            if not raw_text or not raw_text.strip():
                raise ValueError("Model returned an empty completion response.")

            cleaned = _clean_json_string(raw_text)
            parsed_json = json.loads(cleaned)
            validated_data = _validate_analysis_schema(parsed_json)
            
            logger.info("Meaning Mirror analysis successfully completed and validated.")
            return validated_data

        except (json.JSONDecodeError, ValueError) as json_err:
            last_error = json_err
            logger.warning(f"JSON validation attempt {attempt+1} failed: {str(json_err)}")
            if attempt == 0:
                continue
        except Exception as api_err:
            error_name = type(api_err).__name__
            err_msg = str(api_err).lower()
            logger.error(f"Sarvam API call failed: {error_name} - {str(api_err)}")
            
            if "401" in err_msg or "unauthorized" in err_msg:
                raise SarvamServiceError("Sarvam API authentication failed. Please verify your SARVAM_API_KEY.")
            elif "429" in err_msg or "rate limit" in err_msg:
                raise SarvamServiceError("Sarvam API rate limit reached. Please wait 10 seconds and try again.")
            elif "timeout" in err_msg:
                raise SarvamServiceError("Analysis request timed out. Please retry.")
            else:
                raise SarvamServiceError(f"Analysis engine error ({error_name}): {str(api_err)}")

    raise SarvamServiceError(
        f"Unable to produce a valid analysis schema after retry ({str(last_error)}). Please try submitting again."
    )
