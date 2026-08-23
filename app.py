"""
Voice Command Shopping Assistant — Streamlit app
No API keys required anywhere.

Speech-to-text : Google's free web recognizer via the `SpeechRecognition`
                  library (no signup / key needed, just an internet
                  connection at runtime).
Text-to-speech : Browser-native Web Speech API (SpeechSynthesis) — free,
                  runs entirely client-side.
Translation    : deep-translator's free GoogleTranslator endpoint (no key)
                  used only to bridge non-English speech into the parser.
Interrupt      : a live microphone-volume (VAD) listener that runs only
                  while the assistant is talking, and instantly cancels
                  speech the moment the user starts speaking again.
"""

import json
import streamlit as st
import streamlit.components.v1 as components
from streamlit_mic_recorder import mic_recorder

from utils import (
    categorize, get_substitute, get_seasonal_items, get_running_low_suggestions,
    search_catalog, parse_command,
)

st.set_page_config(page_title="Voice Shopping Assistant", page_icon="🛒", layout="wide")

LANGUAGES = {
    "English": {"stt": "en-US", "tts": "en-US", "translate": "en"},
    "Hindi": {"stt": "hi-IN", "tts": "hi-IN", "translate": "hi"},
    "Gujarati": {"stt": "gu-IN", "tts": "gu-IN", "translate": "gu"},
    "Spanish": {"stt": "es-ES", "tts": "es-ES", "translate": "es"},
    "French": {"stt": "fr-FR", "tts": "fr-FR", "translate": "fr"},
}

# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
defaults = {
    "shopping_list": [],       # [{"item": str, "qty": int, "category": str}]
    "transcript": [],          # [(role, text)]
    "last_response": "",
    "speak_nonce": 0,
    "stop_nonce": 0,
    "last_audio_id": None,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def add_item(item, qty):
    for row in st.session_state.shopping_list:
        if row["item"] == item:
            row["qty"] += qty
            return
    st.session_state.shopping_list.append(
        {"item": item, "qty": qty, "category": categorize(item)}
    )


def remove_item(item):
    for row in list(st.session_state.shopping_list):
        if item and (item in row["item"] or row["item"] in item):
            st.session_state.shopping_list.remove(row)
            return True
    return False


def speak(text):
    st.session_state.last_response = text
    st.session_state.speak_nonce += 1


def handle_text_command(text_en, original_text):
    parsed = parse_command(text_en)
    action, item, qty, price_max = (
        parsed["action"], parsed["item"], parsed["quantity"], parsed["price_max"]
    )

    if action == "add":
        if not item:
            response = "I didn't catch what to add. Could you say that again?"
        else:
            add_item(item, qty)
            response = f"Added {qty} {item} to your list."
            subs = get_substitute(item)
            if subs:
                response += f" By the way, you could also try {subs[0]}."
    elif action == "remove":
        if not item:
            response = "Tell me which item to remove."
        elif remove_item(item):
            response = f"Removed {item} from your list."
        else:
            response = f"I couldn't find {item} on your list."
    elif action == "search":
        results = search_catalog(item, price_max)
        if results:
            top = ", ".join(f"{r['brand']} {r['name']} (${r['price']:.2f})" for r in results[:3])
            response = f"I found {len(results)} matches. Top options: {top}."
        else:
            response = f"No results found for {item}."
        st.session_state["_last_search"] = results
    else:
        response = "Sorry, I'm not sure what you meant."

    st.session_state.transcript.append(("user", original_text))
    st.session_state.transcript.append(("assistant", response))
    speak(response)


def transcribe(audio_bytes, sample_rate, sample_width, lang_stt):
    import speech_recognition as sr
    r = sr.Recognizer()
    audio_data = sr.AudioData(audio_bytes, sample_rate, sample_width)
    try:
        text = r.recognize_google(audio_data, language=lang_stt)
        return text, None
    except sr.UnknownValueError:
        return None, "Sorry, I couldn't understand that. Please try again, a bit closer to the mic."
    except sr.RequestError as e:
        return None, f"Speech service error ({e}). Check your internet connection."


def translate_to_english(text, lang_code):
    if lang_code == "en":
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source=lang_code, target="en").translate(text)
    except Exception:
        return text  # fall back to raw text if translation fails


def render_voice_engine(text_to_speak, speak_nonce, stop_nonce, tts_lang):
    """One-way Python -> JS bridge: (re)speaks `text_to_speak` whenever
    speak_nonce changes, force-stops when stop_nonce changes, and runs a
    lightweight mic-volume listener that barges in (cancels speech) the
    instant the user starts talking again."""
    html = f"""
    <div style="font-family:sans-serif;font-size:12px;color:#8a8f98;">🔊 voice engine ready</div>
    <script>
    (function() {{
        const speakNonce = {speak_nonce};
        const stopNonce  = {stop_nonce};
        const text       = {json.dumps(text_to_speak)};
        const lang       = {json.dumps(tts_lang)};
        const parentWin  = window.parent;

        if (parentWin._vsaLastStop !== stopNonce) {{
            parentWin._vsaLastStop = stopNonce;
            try {{ parentWin.speechSynthesis.cancel(); }} catch(e) {{}}
        }}

        if (parentWin._vsaLastSpeak !== speakNonce && text) {{
            parentWin._vsaLastSpeak = speakNonce;
            try {{
                parentWin.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(text);
                utter.lang = lang;
                utter.rate = 1.05;
                parentWin.speechSynthesis.speak(utter);
            }} catch(e) {{ console.log("TTS error", e); }}
        }}

        // Barge-in listener: start once, keep monitoring mic volume.
        if (!parentWin._vsaVadStarted) {{
            parentWin._vsaVadStarted = true;
            navigator.mediaDevices.getUserMedia({{ audio: true }}).then(function(stream) {{
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const src = ctx.createMediaStreamSource(stream);
                const analyser = ctx.createAnalyser();
                analyser.fftSize = 512;
                src.connect(analyser);
                const data = new Uint8Array(analyser.frequencyBinCount);
                function loop() {{
                    analyser.getByteTimeDomainData(data);
                    let sum = 0;
                    for (let i = 0; i < data.length; i++) {{
                        const v = (data[i] - 128) / 128;
                        sum += v * v;
                    }}
                    const rms = Math.sqrt(sum / data.length);
                    if (rms > 0.06 && parentWin.speechSynthesis.speaking) {{
                        parentWin.speechSynthesis.cancel();
                    }}
                    requestAnimationFrame(loop);
                }}
                loop();
            }}).catch(function(err) {{ console.log("barge-in mic unavailable", err); }});
        }}
    }})();
    </script>
    """
    components.html(html, height=24)


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    lang_name = st.selectbox("Voice language", list(LANGUAGES.keys()), index=0)
    lang = LANGUAGES[lang_name]
    hemisphere = st.radio("Hemisphere (for seasonal picks)", ["Northern", "Southern"], horizontal=True)

    if st.button("🛑 Interrupt assistant now"):
        st.session_state.stop_nonce += 1

    if st.button("🗑️ Clear shopping list"):
        st.session_state.shopping_list = []
        st.session_state.transcript = []

    with st.expander("🎤 Mic not working? Read this"):
        st.markdown(
            "- Use **Chrome** or **Edge** — Safari/Firefox support for the mic "
            "recorder & speech synthesis is inconsistent.\n"
            "- The site must be served over **HTTPS** (Streamlit Cloud is).\n"
            "- Click **Allow** on the browser's microphone permission prompt.\n"
            "- If nothing happens after recording, check your internet "
            "connection — transcription needs it.\n"
            "- You can always type a command in the text box below as a fallback."
        )

st.title("🛒 Voice Command Shopping Assistant")
st.caption("Tap the mic, speak naturally — e.g. \"add two bottles of milk\", "
           "\"remove bread\", \"find toothpaste under $5\".")

col1, col2 = st.columns([1.1, 1])

# ----------------------------------------------------------------------
# Column 1: voice input + conversation
# ----------------------------------------------------------------------
with col1:
    st.subheader("🎙️ Talk to your assistant")

    audio = mic_recorder(
        start_prompt="🎤 Tap & Speak",
        stop_prompt="⏹ Stop",
        just_once=True,
        use_container_width=True,
        format="wav",
        key="recorder",
    )

    if audio and audio.get("bytes") and audio.get("id") != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio.get("id")
        with st.spinner("🎧 Listening & understanding..."):
            text, err = transcribe(
                audio["bytes"], audio["sample_rate"], audio["sample_width"], lang["stt"]
            )
        if err:
            st.warning(err)
        else:
            with st.spinner("🌐 Processing..."):
                text_en = translate_to_english(text, lang["translate"])
            handle_text_command(text_en, text)
            st.rerun()

    with st.form("manual_form", clear_on_submit=True):
        typed = st.text_input("Or type a command (useful for quick testing):",
                               placeholder="e.g. add 3 apples")
        submitted = st.form_submit_button("Send")
        if submitted and typed.strip():
            with st.spinner("Processing..."):
                text_en = translate_to_english(typed, lang["translate"])
            handle_text_command(text_en, typed)
            st.rerun()

    st.divider()
    st.markdown("**Conversation**")
    if not st.session_state.transcript:
        st.caption("Nothing yet — say something like *\"I need apples\"*.")
    for role, msg in st.session_state.transcript[-12:]:
        with st.chat_message("user" if role == "user" else "assistant"):
            st.write(msg)

    render_voice_engine(
        st.session_state.last_response,
        st.session_state.speak_nonce,
        st.session_state.stop_nonce,
        lang["tts"],
    )

# ----------------------------------------------------------------------
# Column 2: list + smart panels
# ----------------------------------------------------------------------
with col2:
    st.subheader("📋 Your shopping list")
    if not st.session_state.shopping_list:
        st.caption("Your list is empty. Add something by voice or text!")
    else:
        by_cat = {}
        for row in st.session_state.shopping_list:
            by_cat.setdefault(row["category"], []).append(row)
        for cat, rows in by_cat.items():
            st.markdown(f"**{cat}**")
            for row in rows:
                c1, c2 = st.columns([5, 1])
                c1.write(f"• {row['qty']} × {row['item']}")
                if c2.button("❌", key=f"rm_{cat}_{row['item']}"):
                    st.session_state.shopping_list.remove(row)
                    st.rerun()

    low = get_running_low_suggestions([r["item"] for r in st.session_state.shopping_list])
    if low:
        st.info(f"💡 Looks like you might be running low on: **{', '.join(low)}**.")

    seasonal = get_seasonal_items(hemisphere)
    if seasonal:
        st.success(f"🍂 In season right now: {', '.join(seasonal)}")
        cols = st.columns(len(seasonal))
        for i, s_item in enumerate(seasonal):
            if cols[i].button(f"+ {s_item}", key=f"season_{s_item}"):
                add_item(s_item, 1)
                st.rerun()

    if st.session_state.get("_last_search"):
        st.markdown("**🔎 Search results**")
        st.table(st.session_state["_last_search"])
