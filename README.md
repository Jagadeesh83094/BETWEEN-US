# BETWEEN US — The Meaning Mirror 🪞

**Two perspectives. One conversation. Find the meaning gap.**

Two people describe the *same* misunderstanding in their own words — by voice or by
typing, in English, Hindi, Telugu, Tamil, Kannada, or a mix like Hinglish / Tenglish.
BETWEEN US shows them:

1. the facts both accounts agree on,
2. the first moment their understanding diverged,
3. the two different readings of that moment,
4. phrases that likely meant different things to each person,
5. questions each person can ask the other, and
6. a kinder rewording of each person's main concern.

It is a **communication mirror**, not a judge. It never reads minds, never decides who
is right, and never claims to detect feelings from your voice. Every inference is shown
as a hypothesis you can correct.

> **This supports communication and does not replace professional counselling.**
> If things feel heavy, please talk to a qualified counsellor.

---

## What it is (and isn't)

- **Is:** a single-device, "pass the phone" flow built for two people in the same room.
- **Is:** transparent — it only uses the feelings and needs each person *explicitly stated*.
- **Isn't:** a therapist, a verdict, or a mind reader.
- **Privacy:** audio and text are held **only** in Streamlit session state (per-browser,
  in-memory) and are gone when the session ends. Audio is sent to Sarvam AI only to be
  transcribed. Nothing is written to a database or to disk by this app.

---

## Tech stack

- **Python 3.11+** (tested on 3.12), **Streamlit**, **python-dotenv**.
- **Sarvam AI** via the official `sarvamai` Python SDK:
  - **Speech-to-Text** — `saaras:v4`, mode `transcribe` (short audio, ≤ 30 s).
  - **Chat Completion** — `sarvam-105b` for the analysis, in JSON mode.

Every API call is isolated in `services/sarvam_client.py`. All prompt text is in
`prompts/analysis_prompt.py`. All UI lives in `app.py`.

---

## Setup

```bash
# 1. (optional but recommended) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. add your API key
cp .env.example .env               # then edit .env and paste your key
#    Get a key at https://dashboard.sarvam.ai
```

`.env` should contain:

```
SARVAM_API_KEY=your_sarvam_api_key_here
```

The key is loaded with `python-dotenv`. It is **never** hardcoded, printed, or shown in
the UI. Do not commit `.env`.

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

---

## The flow (four screens)

1. **Home** — tagline, what the app does, privacy + counselling notices, **Start** and
   **Load demo**.
2. **Input** (once per person) — choose language, then **record** (`st.audio_input`),
   **upload** an audio file, or **type**. After transcription you get an editable text box
   to fix errors before submitting. Prompts cover: what happened, what you felt, what you
   understood, what you want the other person to understand.
3. **Consent + analysis** — both people tick a consent box, then press **Analyze**.
4. **Results** — the Meaning Gap view: divergence point first (main card), then the two
   readings side by side, ambiguous phrases, shared facts, questions, rewordings, open
   points — plus an **"Edit / This isn't what I meant"** control for each person that
   re-runs the analysis with their correction.

Between Person A and Person B the screen is replaced by a **"Pass the device to Person B"**
step, so neither person's raw account is shown to the other before consent.

---

## Demo mode (no microphone needed)

Press **Load demo** on the home screen. It loads two ready-made **Hinglish** accounts
about a *"fine, do whatever you want"* message and a *"dekhte hain"* reply to a weekend
plan, jumps to the consent screen, and you can run the full analysis in under two minutes
with no audio at all. (The analysis step still needs a valid `SARVAM_API_KEY`.)

---

## Project tree

```
between-us/
├── app.py                      # All UI: 4 screens, pass-the-phone flow, styling
├── requirements.txt
├── .env.example
├── README.md
├── services/
│   ├── __init__.py
│   ├── sarvam_client.py        # EVERY Sarvam API call (STT + chat), verified against docs
│   └── analysis.py             # Analysis engine: build → call → validate JSON → retry once
├── prompts/
│   ├── __init__.py
│   └── analysis_prompt.py      # System prompt, JSON schema template, message builders
├── data/
│   ├── __init__.py
│   └── demo_accounts.py        # The two Hinglish demo accounts
├── test_engine.py              # Unit tests: JSON parse / retry / validation (no network)
└── test_app.py                 # End-to-end UI test via Streamlit AppTest (no network)
```

## Tests

Both suites run offline (the API calls are stubbed), so they verify the logic and the
whole UI flow without spending credits:

```bash
python3 test_engine.py   # valid JSON, fenced JSON, malformed->retry->valid, hard-fail, coercion
python3 test_app.py      # home -> demo -> consent gating -> results; full typed pass-the-phone flow
```

---

## Reliability

- **Transcription fails / no mic?** You keep your place — switch to **Upload audio** or
  **Type**; nothing already entered is lost. Empty or silent recordings get a clear message.
- **Long audio (>30 s):** the REST API rejects it; the app explains the 30-second limit and
  suggests a shorter clip, an upload, or typing.
- **API problems:** timeouts, rate limits (429), invalid keys (403) and busy services (503)
  are mapped to plain-language messages.
- **Malformed model JSON:** the analysis is validated; on failure it retries **once** with a
  repair message, and if it still fails shows a friendly error with a retry button.
- **Empty input:** the Submit and Analyze buttons stay disabled until there's something to work with.
- **Unsupported language:** any code the STT model doesn't accept falls back to auto-detect.

---

## Verify before demo (things I could not fully confirm from the docs)

I checked the Sarvam docs and introspected the installed SDK (`sarvamai 0.1.37`) on
2026-10-16. The following are the only items that could not be confirmed *exhaustively*
from the public docs; each is marked `# VERIFY AGAINST DOCS` in `services/sarvam_client.py`.

1. **No client-side duration check.** The SDK exposes no audio-length helper, so the 30-second
   REST limit is enforced by the API (which returns `422`), and the app translates that into a
   message. *Confirm:* record >30 s and check the message.
2. **`reasoning_effort` left at its default.** We deliberately don't set it (V1 default is
   `medium` per docs) to keep latency/cost predictable. *Confirm:* whether `low` gives faster,
   good-enough JSON for the demo.
3. **`max_tokens=4000` and `temperature=0.2`.** Both are documented parameters and are accepted
   by the SDK, but the exact truncation behaviour of the long JSON schema at a given
   `max_tokens` isn't documented. *Confirm:* a full run doesn't hit `finish_reason: "length"`.
4. **Exact JSON-schema (structured output) support for `sarvam-105b`.** The SDK accepts
   `response_format={"type": "json_schema", ...}` and `{"type": "json_object"}`; we use the
   simpler `json_object` mode plus the schema in the prompt, and still validate + retry. *Confirm:*
   whether strict `json_schema` mode is available on your key for `sarvam-105b`.
5. **Which STT model your key can use.** Docs list `saaras:v4` as the default/recommended model;
   we default to it (`SARVAM_STT_MODEL` in `.env` overrides). *Confirm:* your key's access to
   `saaras:v4` (fall back to `saaras:v3` if needed).
6. **`st.audio_input` browser codec.** It produces a WebM/Opus blob in most browsers, which the
   API accepts; if a browser returns an empty blob the app shows a clear error. *Confirm:* in the
   actual demo browser.

Everything else — the SDK client constructor, the `chat.completions` / `speech_to_text.transcribe`
call shapes, the `sarvam-105b` and `saaras:v4` model IDs, the 23 BCP-47 language codes, the
`transcript` / `language_code` / `choices[0].message.content` response fields, and the `ApiError`
status codes — was verified directly and is not guessed.
