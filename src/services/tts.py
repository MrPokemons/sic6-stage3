from abc import ABC
import secrets
import io
import torch
import soundfile as sf
from typing import List, Optional
from logging import Logger
from transformers import AutoTokenizer, VitsModel
from elevenlabs import AsyncElevenLabs, VoiceSettings


class TextToSpeech(ABC):
    def synthesize(self, text: str) -> bytes:
        raise NotImplementedError("synthesize() not implemented.")

    async def synthesize_async(self, text: str) -> bytes:
        raise NotImplementedError("synthesize_async() not implemented.")



class FacebookMMSTextToSpeech(TextToSpeech):
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            "facebook/mms-tts-ind",
            local_files_only=True,
        )
        self.model = VitsModel.from_pretrained(
            "facebook/mms-tts-ind",
            local_files_only=True,
        )
        self.model.eval()

    def synthesize(self, text: str) -> bytes:
        inputs = self.tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
            waveform = outputs.waveform.squeeze().cpu().numpy()

        with io.BytesIO() as buffer:
            sf.write(buffer, waveform, 16000, format="WAV")
            return buffer.getvalue()


class ElevenlabsTextToSpeech(TextToSpeech):
    def __init__(self, api_keys: str):
        api_keys: List[str] = api_keys.split(';')
        self.clients = []
        for _api_key in api_keys:
            self.clients.append(AsyncElevenLabs(api_key=_api_key))
        self.voice_id = "RWiGLY9uXI70QL540WNd"
        self.voice_settings = VoiceSettings(
            speed=.95,
            stability=.7,
            similarity_boost=.75
        )

    def get_client(self) -> AsyncElevenLabs:
        return secrets.choice(self.clients)

    async def synthesize_async(self, text: str) -> bytes:
        client = self.get_client()
        audio_generator = client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            voice_settings=self.voice_settings
        )
        chunks = []
        async for chunk in audio_generator:
            chunks.append(chunk)
        return b''.join(chunks)


class TextToSpeechCollection:
    def __init__(self, facebook_mms: FacebookMMSTextToSpeech, elevenlabs: Optional[ElevenlabsTextToSpeech] = None, *, logger: Logger):
        self.facebook_mms = facebook_mms
        self.elevenlabs = elevenlabs
        self.logger = logger

    async def synthesize_async(self, text: str) -> bytes:
        try:
            if self.elevenlabs is None:
                raise ValueError("Elevenlabs not provided")
            self.logger.info("TTS: using elevenlabs asynchronous")
            return await self.elevenlabs.synthesize_async(text=text)
        except Exception as e:
            self.logger.info(f"TTS: using facebook MMS, others failed due to {e}")
            return self.facebook_mms.synthesize(text=text)
