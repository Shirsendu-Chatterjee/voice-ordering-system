# 🛒 Voice Command Shopping Assistant

A voice-first shopping list app that understands natural speech, organizes your list automatically, and talks back — built entirely with **free, key-free** services (no OpenAI/Google Cloud API keys anywhere).

**[🔗 Live Demo](#)** &nbsp;•&nbsp; **[📦 Source Code](#)** &nbsp;•&nbsp; Built with Streamlit

---

## ✨ Features

| Category | What it does |
|---|---|
| 🎙️ **Voice input** | Push-to-talk recording, transcribed via Google's free speech recognizer — handles varied phrasing ("add milk", "I need apples", "I want to buy bananas") |
| ⚡ **Instant interrupt (barge-in)** | A live mic-volume listener runs only while the assistant is talking. The moment you speak, it cancels the assistant's voice mid-sentence — no waiting for it to finish |
| 🌍 **Multilingual** | Speak in English, Hindi, Gujarati, Spanish, or French — auto-translated to English before parsing |
| 🧠 **Smart NLP parsing** | Local rule-based parser extracts intent, quantity ("2 bottles of water"), and price filters ("toothpaste under $5") — no external NLU API |
| 🗂️ **Auto-categorization** | Items are automatically sorted into Dairy, Produce, Bakery, Snacks, Household, etc. |
| 💡 **Smart suggestions** | Nudges you about staples you might be running low on |
| 🍂 **Seasonal picks** | Suggests what's in season based on the current month and hemisphere |
| 🔄 **Substitutes** | Suggests alternatives (e.g. almond milk instead of regular milk) |
| 🔎 **Voice search** | "Find toothpaste under $5" filters a mock product catalog by price/brand |
| ⌨️ **Text fallback** | Every voice command also works by typing — useful if the mic isn't available |

---

## 🏗️ How it works

```
🎤 Mic tap  ──▶  streamlit-mic-recorder  ──▶  Google free STT  ──▶  (translate if needed)
                                                                          │
                                                                          ▼
                                                     Local rule-based intent parser
                                                        (add / remove / search,
                                                         quantity, price filter)
                                                                          │
                                                                          ▼
                                        Shopping list state  ──▶  Category / seasonal /
                                                                   substitute engines
                                                                          │
                                                                          ▼
                                              Browser Web Speech API (speechSynthesis)
                                                     speaks the confirmation
                                                                          │
                                            (while speaking) mic-volume VAD listener
                                              barges in and cancels speech on interrupt
```

**No API keys required:**
- **Speech-to-text** — `SpeechRecognition` library → Google's free web recognizer
- **Text-to-speech** — the browser's native Web Speech API (`speechSynthesis`), 100% client-side
- **Translation** — `deep-translator`'s free Google endpoint, used only as a bridge for non-English input
- **NLP** — a dependency-free regex/rule-based parser in `utils.py`

---

## 📁 Project structure

```
.
├── app.py             # Streamlit UI, voice engine glue, session state
├── utils.py           # Intent parser + category/seasonal/substitute/catalog tables
├── requirements.txt   # Python dependencies
└── README.md
```

---

## 🚀 Getting started

### Run locally

```bash
git clone <your-repo-url>
cd voice-shopping-assistant
pip install -r requirements.txt
streamlit run app.py
```

Open the printed local URL (usually `http://localhost:8501`) in **Chrome or Edge** for the most reliable microphone and speech-synthesis support.

### Deploy for free (Streamlit Community Cloud)

1. Push this repo to **GitHub** (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo/branch, set **Main file path** to `app.py`, click **Deploy**.
4. You'll get a public **HTTPS** URL — required for microphone access, and provided automatically by Streamlit Cloud.

> Any host that serves over HTTPS and runs a long-lived Python process (AWS, GCP, Firebase Hosting + Cloud Run, Render, etc.) works too — Streamlit Cloud is just the fastest free option.

---

## 🧪 Testing checklist

Use **Chrome or Edge** on the deployed HTTPS URL:

- [ ] **Permission** — allow the mic prompt on first tap
- [ ] **Basic add** — say *"add milk"* → appears under Dairy, assistant confirms aloud
- [ ] **Phrasing variety** — *"I need apples"*, *"buy 5 oranges"*, *"add 2 bottles of water"*
- [ ] **Remove** — *"remove milk from my list"*
- [ ] **Search + price filter** — *"find toothpaste under $5"*
- [ ] **Interrupt** — talk over the assistant mid-sentence; it should stop instantly. Also try the sidebar's **"Interrupt assistant now"** button
- [ ] **Multilingual** — switch language, speak a command, confirm correct translation + action
- [ ] **Text fallback** — same commands typed into the text box behave identically
- [ ] **Offline edge case** — disable Wi-Fi briefly and record; should show a friendly error, not crash
- [ ] **Seasonal/substitute panels** — check they match the current month/hemisphere and surface sensible alternatives

---

## ⚠️ Known limitations

- STT and translation are free web endpoints, so they need an internet connection at runtime.
- `speechSynthesis` / mic support varies by browser — Chrome and Edge are the most reliable; Safari and Firefox are inconsistent.
- The NLP is rule-based rather than ML-based, which keeps it fast and free of API keys, but very unusual phrasings may not parse — use the text-box fallback in that case.

---

## 🛠️ Tech stack

`Streamlit` · `streamlit-mic-recorder` · `SpeechRecognition` · `deep-translator` · Web Speech API (browser-native)
