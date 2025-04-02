from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech

# Initialize classes
stt = SpeechToText()
tts = TextToSpeech()

# === STT Test ===
with open("test_input.wav", "rb") as f:
    audio_bytes = f.read()

transcribed_text = stt.transcribe(audio_bytes)
print("🗣️ Transcribed Text:", transcribed_text)

# === TTS Test ===
tts_audio = tts.synthesize(transcribed_text)

with open("test_output.wav", "wb") as f:
    f.write(tts_audio)

print("🔊 TTS Audio saved to test_output.wav")