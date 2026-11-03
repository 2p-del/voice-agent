# Gemini Travel Advisor — Streamlit

## Run locally

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example`, add your Gemini API key, then run:

```bash
streamlit run app.py
```

For Streamlit Community Cloud, add these under **App settings → Secrets**:

```toml
GEMINI_API_KEY = "your_api_key"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_VOICE = "Kore"
```

This app uses Streamlit's browser microphone recorder (`st.audio_input`), so it
does not use `sounddevice` or require a microphone attached to the deployment
server. It records first, then sends the recording to Gemini. TTS is optional
and is generated when the user clicks the speech button.

The free Gemini API tier has rate limits and model availability restrictions.
Check current Google AI Studio availability and quotas for your account.
