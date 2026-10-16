"""Every Sarvam AI API call in the app lives in this one file.

VERIFIED 2026-10-16 against:
  * the official docs at https://docs.sarvam.ai (quickstart, SDKs, chat
    completion overview, chat V1 reference, speech-to-text REST reference,
    "how to specify language codes", FAQs)
  * the installed SDK itself, ``sarvamai 0.1.37`` (method signatures and
    response models were introspected directly).

Verified facts baked in below:
  * Client:            ``SarvamAI(api_subscription_key=...)`` (also reads the
                       ``SARVAM_API_KEY`` env var).
  * Chat:              ``client.chat.completions(messages=[...], model=...)``
                       -> ``response.choices[0].message.content``.
                       Models: ``sarvam-105b`` (128K), ``sarvam-105b-conversations``.
                       ``response_format={"type": "json_object"}`` is accepted.
  * Speech-to-text:    ``client.speech_to_text.transcribe(file=..., model=...,
                       mode=..., language_code=...)`` -> ``.transcript`` /
                       ``.language_code``. Models ``saaras:v4`` (default) /
                       ``saaras:v3``. REST limit: 30 seconds per request.
  * Language codes:    the 23 BCP-47 codes below, plus ``"unknown"`` to
                       auto-detect.
  * Errors:            ``from sarvamai.core.api_error import ApiError`` with
                       ``.status_code`` / ``.body``.

Items I could NOT fully confirm from the docs are marked ``# VERIFY AGAINST DOCS``
and listed in the README's "Verify before demo" section.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration (all overridable via .env)
# ---------------------------------------------------------------------------
STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4")
STT_MODE = os.getenv("SARVAM_STT_MODE", "transcribe")
CHAT_MODEL = os.getenv("SARVAM_CHAT_MODEL", "sarvam-105b")

# 30 seconds is the documented hard limit for the synchronous REST endpoint.
# VERIFY AGAINST DOCS: the SDK does not expose a duration check; we rely on the
# API returning 422 for over-length audio and translate that into a message.
REST_STT_MAX_SECONDS = 30

# BCP-47 codes accepted by saaras:v3 / saaras:v4 (from "How to specify language codes").
SUPPORTED_STT_LANGUAGES = {
    "hi-IN", "bn-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN",
    "te-IN", "en-IN", "gu-IN", "as-IN", "ur-IN", "ne-IN", "kok-IN", "ks-IN",
    "sd-IN", "sa-IN", "sat-IN", "mni-IN", "brx-IN", "mai-IN", "doi-IN",
}

# What the UI offers. Labels are what the user picks; the value is the code we
# send to the STT API. "unknown" = let Sarvam auto-detect (used for Hinglish,
# Tenglish and any code-mixed input, which has no single BCP-47 code).
LANGUAGE_CHOICES = [
    ("English", "en-IN"),
    ("Hindi", "hi-IN"),
    ("Telugu", "te-IN"),
    ("Tamil", "ta-IN"),
    ("Kannada", "kn-IN"),
    ("Hinglish / mixed (auto-detect)", "unknown"),
    ("Tenglish / Tanglish / mixed (auto-detect)", "unknown"),
    ("Not sure — auto-detect", "unknown"),
]

MIME_BY_EXT = {
    "webm": "audio/webm",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "aiff": "audio/aiff",
    "amr": "audio/amr",
}


# ---------------------------------------------------------------------------
# Errors — friendly, typed, so the UI never has to know SDK internals
# ---------------------------------------------------------------------------
class SarvamServiceError(RuntimeError):
    """Base class for every recoverable problem surfaced to the user."""


class MissingApiKeyError(SarvamServiceError):
    pass


class TranscriptionError(SarvamServiceError):
    pass


class AnalysisAPIError(SarvamServiceError):
    pass


# ---------------------------------------------------------------------------
# Client / key handling
# ---------------------------------------------------------------------------
def api_key_present() -> bool:
    """True when a non-empty SARVAM_API_KEY is configured."""
    return bool(os.getenv("SARVAM_API_KEY", "").strip())


def _require_key() -> str:
    key = os.getenv("SARVAM_API_KEY", "").strip()
    if not key:
        raise MissingApiKeyError(
            "No SARVAM_API_KEY found. Copy .env.example to .env and paste your key "
            "from https://dashboard.sarvam.ai, then restart the app."
        )
    return key


def _client():
    """Build a Sarvam SDK client. Imported lazily so a missing SDK gives a clear message."""
    try:
        from sarvamai import SarvamAI
    except ImportError as exc:  # pragma: no cover - dependency is in requirements.txt
        raise SarvamServiceError(
            "The 'sarvamai' SDK is not installed. Run: pip install -r requirements.txt"
        ) from exc
    # NOTE: the key is passed straight from the environment and is never logged
    # or rendered anywhere in the UI.
    return SarvamAI(api_subscription_key=_require_key(), timeout=60.0)


def _ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"


def _mime_of(filename: str) -> str:
    return MIME_BY_EXT.get(_ext_of(filename), "application/octet-stream")


# ---------------------------------------------------------------------------
# Speech to text
# ---------------------------------------------------------------------------
def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.webm",
    language_code: str = "unknown",
) -> dict:
    """Transcribe a short (<=30s) audio clip.

    Returns {"transcript": str, "language_code": str|None}. Raises
    TranscriptionError with a human-readable message on any failure, so the UI
    can fall back to typing or file upload without losing entered data.
    """
    if not audio_bytes or len(audio_bytes) == 0:
        raise TranscriptionError(
            "That recording looks empty — no audio was captured. Please try again, "
            "upload a file, or type your account instead."
        )

    if language_code not in SUPPORTED_STT_LANGUAGES and language_code != "unknown":
        # Never send an unsupported code; fall back to auto-detect.
        language_code = "unknown"

    # The SDK accepts (filename, bytes, content_type) directly — no temp file needed.
    file_tuple = (filename, audio_bytes, _mime_of(filename))

    try:
        client = _client()
        response = client.speech_to_text.transcribe(
            file=file_tuple,
            model=STT_MODEL,
            mode=STT_MODE,
            language_code=language_code,
        )
    except MissingApiKeyError:
        raise
    except Exception as exc:  # noqa: BLE001 - we translate every failure for the user
        raise TranscriptionError(_friendly_stt_error(exc)) from exc

    transcript = (getattr(response, "transcript", "") or "").strip()
    detected = getattr(response, "language_code", None)
    if not transcript:
        raise TranscriptionError(
            "We couldn't hear any words in that clip. Please try again closer to the mic, "
            "or type your account instead."
        )
    return {"transcript": transcript, "language_code": detected}


def _friendly_stt_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    if status == 422:
        return (
            "The audio couldn't be processed — it may be longer than 30 seconds, in an "
            "unsupported format, or empty. Try a shorter clip (under 30s), upload a "
            "WAV/MP3/M4A file, or type your account instead."
        )
    if status == 403:
        return "Your Sarvam API key was rejected. Check SARVAM_API_KEY in your .env file."
    if status == 429:
        return "Too many requests right now (rate limit). Please wait a few seconds and try again."
    if status in (500, 503):
        return "Sarvam's speech service is temporarily busy. Please try again in a moment."
    if status == 400:
        return "Sarvam couldn't read that audio file. Try a different format or type your account."
    return (
        "Transcription didn't go through. You can try again, upload an audio file, "
        "or just type your account — nothing you've entered is lost."
    )


# ---------------------------------------------------------------------------
# Chat / analysis
# ---------------------------------------------------------------------------
def chat_json(
    messages: list,
    temperature: float = 0.2,
    max_tokens: int = 4000,
) -> str:
    """Call the Sarvam chat model in JSON mode and return the raw text content.

    We ask for a JSON object via ``response_format`` AND spell the schema out in
    the prompt; the analysis layer still validates and retries once, because
    "JSON mode" guarantees valid JSON but not our exact shape.
    """
    try:
        client = _client()
        response = client.chat.completions(
            messages=messages,
            model=CHAT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            # VERIFY AGAINST DOCS: we do not set `reasoning_effort`; the API
            # default ("medium" on V1) is used, to keep latency/cost predictable.
        )
    except MissingApiKeyError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AnalysisAPIError(_friendly_chat_error(exc)) from exc

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise AnalysisAPIError(
            "The analysis model returned an unexpected response shape. Please try again."
        ) from exc

    if not content or not content.strip():
        raise AnalysisAPIError(
            "The analysis model returned an empty response. Please try again."
        )
    return content


def _friendly_chat_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    if status == 403:
        return "Your Sarvam API key was rejected. Check SARVAM_API_KEY in your .env file."
    if status == 429:
        return "Too many requests right now (rate limit). Please wait a few seconds and try again."
    if status in (500, 503):
        return "Sarvam's analysis service is temporarily busy. Please try again in a moment."
    if status == 400:
        return "The analysis request was rejected. Please try again."
    return "The analysis call failed (timeout or network issue). Please try again."
