# BETWEEN US — The Meaning Mirror 🪞

> *"Two perspectives. One conversation. Find the meaning gap."*

A prototype for interpersonal understanding built for hackathons. When two people experience a communication breakdown, they each describe what happened in their own words (voice or text, in English, Hindi, Telugu, Tamil, Kannada, or mixed codes like Hinglish/Tenglish).

**BETWEEN US** acts as a neutral mirror that uncovers the exact point where interpretations diverged, translates ambiguous phrasing (such as a polite *"dekhte hain"* or *"chuddam"* heard as yes by one and no by the other), surfaces shared ground, and offers kinder ways forward.

---

## 🌟 Core Features

1. **The Divergence Point (Hero Card):** Identifies the exact turning point where interpretations split, explaining why each reading formed without taking sides.
2. **Side-by-Side Readings:** Visualizes both interpretations of that critical moment as tentative hypotheses ("may have meant", "could be read as").
3. **Ambiguous Phrases & Cultural Nuance:** Highlights idiomatic vernacular phrases (e.g., *"dekhte hain"*, *"chuddam"*, *"sare le"*, *"fine, do whatever you want"*) and details their dual interpretations.
4. **Shared Facts (Common Ground):** Highlights facts both accounts agree on, complete with evidence quotes from each person and confidence ratings.
5. **Strict Emotion Discipline:** Displays **only** feelings and needs explicitly articulated by each speaker. No emotions or states of mind are invented or extrapolated.
6. **Curious Questions:** Suggests non-accusatory questions for Person A to ask Person B, and for Person B to ask Person A.
7. **Kinder Rewordings:** De-escalates primary concerns into warm, connection-focused language.
8. **Interactive Correction Flow ("This isn't what I meant"):** Allows participants to clarify or dispute any inference and re-run the analysis.
9. **Single-Device "Pass the Phone" Design:** Designed specifically for one smartphone or laptop passed between two people. Person A's account is sealed before Person B takes the device. Mutual consent is required before any analysis is revealed.
10. **Zero-Audio Demo Mode:** Includes a preloaded Hinglish scenario ("dekhte hain" vs "fine, do whatever you want") that evaluates in under two minutes with zero microphone needed.

---

## 📁 Project Tree

```text
between-us/
├── .env.example              # Template for API credentials
├── requirements.txt          # Python dependencies (Streamlit, SarvamAI, python-dotenv)
├── README.md                 # Complete documentation and verification notes
├── app.py                    # Main Streamlit application and screen router
├── prompts/
│   ├── __init__.py
│   └── analysis_prompt.py    # Strict Meaning Mirror schema and neutrality prompts
├── services/
│   ├── __init__.py
│   └── sarvam_client.py      # Sarvam AI STT & Chat completion client wrapper
├── data/
│   ├── __init__.py
│   └── demo_data.py          # Preloaded Hinglish demo scenario
├── utils/
│   ├── __init__.py
│   └── state_manager.py      # Streamlit session state and transition management
└── styles/
    └── theme.css             # Glassmorphic, responsive, accessible dark theme
```

---

## 🚀 Quick Setup & Run

### 1. Prerequisites
- Python 3.11 or higher (tested on 3.11 - 3.14)
- A valid Sarvam AI API subscription key from [dashboard.sarvam.ai](https://dashboard.sarvam.ai/)

### 2. Installation

Clone or navigate to the project directory:
```bash
cd between-us
```

Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit `.env` to include your key:
```env
SARVAM_API_KEY=your_actual_sarvam_api_key_here
```

*(Note: If no key is set in `.env`, the UI will allow entering a temporary key held in memory for that session).*

### 4. Run the Application
Launch the Streamlit app:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📱 Single-Device Flow ("Pass the Phone")

1. **Screen 1 — Home:** Read overview, counselling disclaimer, and privacy pledge. Click **Start New Conversation** or **Load Demo Scenario**.
2. **Screen 2A — Person A Input:** Person A speaks or types their account using the 4 guided prompts (What happened, What you felt, What you understood, What you want them to understand). Upon submission, Person A's account is sealed.
3. **Interstitial Screen — Pass Device:** Prompts handing the phone/laptop to Person B.
4. **Screen 2B — Person B Input:** Person B enters their account in private.
5. **Screen 3 — Mutual Consent:** Both participants check their respective consent boxes. Only when both agree is the **Reveal the Meaning Mirror** button unlocked.
6. **Screen 4 — Results:** View the divergence point, side-by-side readings, ambiguous phrases, shared facts, feelings, and questions. Either person can click *"This isn't what I meant"* to refine the analysis.

---

## 🔍 Verify Before Demo (Sarvam AI API Checklist)

During development with the official `sarvamai` Python SDK (v0.1.37), the following parameters and behavior were verified and cross-referenced:

| Component | Identifier / Call | Verification Status | Notes |
| :--- | :--- | :--- | :--- |
| **Client Initialization** | `SarvamAI(api_subscription_key=key)` | **VERIFIED** | Successfully initializes and authenticates |
| **Chat Completion Model** | `model="sarvam-105b"` | **VERIFIED** | High-capacity multilingual model (Hindi, Telugu, Tamil, Kannada, English) |
| **JSON Mode** | `response_format={"type": "json_object"}` | **VERIFIED** | Model returns direct, parseable JSON |
| **Speech-to-Text Model** | `client.speech_to_text.transcribe` with `model="saaras:v3"` | **VERIFIED against SDK signature** | `'saaras:v3'` is standard; `'saaras:v4'` also present in SDK |
| **STT Mode** | `mode="codemix"` or `mode="transcribe"` | **VERIFIED against SDK signature** | `'codemix'` handles Hinglish/Tenglish code-switching |
| **STT Language Codes** | `'en-IN'`, `'hi-IN'`, `'te-IN'`, `'ta-IN'`, `'kn-IN'`, `'unknown'` | **VERIFIED against SDK signature** | Exact literals supported by Sarvam STT |
| **Audio File Size Limit** | 25 MB / ~10 minutes | **VERIFY AGAINST DOCS** | Standard REST payload ceiling; client enforces 25MB check |
| **Response Payload** | `response.choices[0].message.content` | **VERIFIED** | Parsed directly; fallback retry on malformed JSON included |

---

## 🛡️ Privacy & Counselling Notices

- **Not Professional Counselling:** BETWEEN US is a conversational reflection tool. It does not provide psychological diagnosis, therapy, or formal legal mediation.
- **Strict Privacy Guarantee:** All audio, transcripts, drafts, and inferences reside entirely inside Streamlit's temporary browser session state (`st.session_state`). Nothing is written to any external database or disk.
