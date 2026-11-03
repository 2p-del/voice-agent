import os
import time
import base64
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

st.set_page_config(page_title="Gemini Travel Advisor", page_icon="✈️", layout="centered")
st.title("✈️ Gemini Travel Advisor")
st.caption("Ask your travel questions by voice and hear the advice spoken back to you.")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    st.error("Add your Gemini API key to a .env file as GEMINI_API_KEY=your_key, then restart the app.")
    st.stop()

client = genai.Client(api_key=api_key)

ANSWER_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
# Automatically repair the obsolete model name if it remains in the existing .env.
if TTS_MODEL == "gemini-3.8-flash-preview-tts":
    TTS_MODEL = "gemini-3.8-flash-tts"
VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore")
FALLBACK_MODELS = [
    item.strip() for item in os.getenv(
        "GEMINI_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite"
    ).split(",") if item.strip()
]

def get_travel_answer(audio_file):
    prompt = (
        "You are a friendly, knowledgeable travel advisor. Listen to the user's "
        "recorded question and answer clearly and helpfully. Give practical travel "
        "suggestions. If important details are missing, ask one short follow-up. "
        "Do not invent live prices, schedules, visa rules, or availability."
    )
    models = [ANSWER_MODEL] + [m for m in FALLBACK_MODELS if m != ANSWER_MODEL]
    last_error = None

    for model in models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=audio_file.getvalue(),
                            mime_type=audio_file.type or "audio/wav",
                        ),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(temperature=0.6),
                )
                answer = (response.text or "").strip()
                if not answer:
                    raise RuntimeError("Gemini returned an empty text response.")
                return answer, model
            except Exception as exc:
                last_error = exc
                message = str(exc).lower()
                temporary = any(term in message for term in (
                    "503", "unavailable", "overloaded", "429",
                    "resource_exhausted", "500", "internal"
                ))
                if attempt == 0 and temporary:
                    time.sleep(2)
                    continue
                break

    raise RuntimeError(f"Could not generate the answer. Last error: {last_error}")

def text_to_speech(text_to_say):
    interaction = client.interactions.create(
        model=TTS_MODEL,
        input=[{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text_to_say,
                "annotations": [{
                    "type": "speech_metadata",
                    "style": "warm, friendly, clear travel guide; natural conversational pace",
                }],
            }],
        }],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": VOICE}]},
    )

    audio_output = getattr(interaction, "output_audio", None)
    audio_data = getattr(audio_output, "data", None) if audio_output else None
    if not audio_data:
        raise RuntimeError("The TTS model returned no audio data.")
    return base64.b64decode(audio_data)


audio_input = st.audio_input("Record your travel question", sample_rate=16000)

if audio_input:
    st.audio(audio_input)
    if st.button("Ask Travel Advisor", type="primary", use_container_width=True):
        with st.spinner("Listening and preparing your travel advice..."):
            try:
                answer, model_used = get_travel_answer(audio_input)
                st.subheader("Travel Advisor")
                st.write(answer)
                st.caption(f"Answer model: {model_used}")

                with st.spinner("Creating spoken audio..."):
                    try:
                        spoken_audio = text_to_speech(answer)
                        st.subheader("🎧 Listen to your travel advice")
                        st.audio(spoken_audio, format="audio/wav")
                    except Exception as tts_error:
                        st.warning("Your text answer is ready, but speech generation failed.")
                        st.code(str(tts_error))
                        st.info(
                            "Check that your Google AI Studio project has access to "
                            f"{TTS_MODEL}, and that google-genai is up to date."
                        )
            except Exception as exc:
                st.error("I couldn't process that recording.")
                st.code(str(exc))
                st.info("Wait briefly and try again. For 429 errors, check your Gemini API quota and billing.")
else:
    st.info("Select the microphone above, record a question, and press **Ask Travel Advisor**.")

with st.expander("Troubleshooting"):
    st.markdown(
        "- **503 / overloaded:** wait briefly and try again; the model may be busy.\n"
        "- **429 / quota:** check your Google AI Studio project limits and billing.\n"
        "- **TTS model unavailable:** confirm that your API project can access the configured TTS model.\n"
        "- **API key error:** confirm the key is in `.env` and restart Streamlit."
    )
