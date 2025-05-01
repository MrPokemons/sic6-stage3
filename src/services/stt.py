import secrets
from abc import ABC
from typing import Union, List, Optional
from logging import Logger
import httpx
import tempfile
import numpy as np
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)


class SpeechToText(ABC):
    SAMPLE_RATE = 16_000

    def transcribe_raw(self, raw_audio_bytes: bytes) -> str:
        raise NotImplementedError("transcribe_raw() not implemented.")

    async def transcribe_raw_async(self, raw_audio_bytes: bytes) -> str:
        raise NotImplementedError("transcribe_raw_async() not implemented.")

    def transcribe_array(self, waveform: Union[torch.Tensor, np.ndarray], sample_rate: int) -> str:
        raise NotImplementedError("transcribe_array() not implemented.")

    async def transcribe_array_async(self, waveform: Union[torch.Tensor, np.ndarray], sample_rate: int) -> str:
        raise NotImplementedError("transcribe_array_async() not implemented.")


class WhisperSpeechToText(SpeechToText):
    def __init__(self):
        self.processor = WhisperProcessor.from_pretrained(
            "cahya/whisper-medium-id", local_files_only=True
        )
        self.model = WhisperForConditionalGeneration.from_pretrained(
            "cahya/whisper-medium-id",
            local_files_only=True,
        )
        self.model.eval()

    def transcribe_raw(self, raw_audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio:
            temp_audio.write(raw_audio_bytes)
            temp_audio.flush()

            waveform, sample_rate = torchaudio.load(temp_audio.name)
            return self.transcribe_array(waveform=waveform, sample_rate=sample_rate)

    def transcribe_array(self, waveform: Union[torch.Tensor, np.ndarray], sample_rate: int) -> str:
        if isinstance(waveform, np.ndarray):
            waveform = torch.from_numpy(waveform)

        if not isinstance(waveform, torch.Tensor):
            raise TypeError(f"Invalid type '{type(waveform)}' when trying to transcribe by TTS")

        if sample_rate != self.SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate, new_freq=self.SAMPLE_RATE
            )
            waveform = resampler(waveform)

        inputs = self.processor( # must float32
            waveform.squeeze(), return_tensors="pt", sampling_rate=self.SAMPLE_RATE
        )
        with torch.no_grad():
            generated_ids = self.model.generate(inputs.input_features)
            transcription = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0]
            return transcription


class DeepgramSpeechToText:
    def __init__(self, api_keys: str):
        api_keys: List[str] = api_keys.split(';')
        self.clients = []
        for _api_key in api_keys:
            self.clients.append(DeepgramClient(api_key=_api_key))
        self.options = PrerecordedOptions(
            model="nova-2-general",
            smart_format=True,
            language="id",
        )

    def get_client(self) -> DeepgramClient:
        return secrets.choice(self.clients)

    async def transcribe_raw_async(self, audio_data: bytes):
        payload: FileSource = {
            "buffer": audio_data,
        }
        client = self.get_client()
        response = await client.listen.asyncrest.v("1").transcribe_file(
            payload, self.options, timeout=httpx.Timeout(60.0, connect=10.0)
        )
        transcripts: List[str] = []
        for channel in response.results.channels:
            for alt in channel.alternatives:
                if alt.transcript:
                    transcripts.append(alt.transcript)

        return '\n'.join(transcripts)


class SpeechToTextCollection:
    def __init__(self, whisper: WhisperSpeechToText, deepgram: Optional[DeepgramSpeechToText] = None, *, logger: Logger):
        self.whisper = whisper
        self.deepgram = deepgram
        self.logger = logger

    async def transcribe_raw_async(
        self,
        audio_data: bytes,
    ):
        try:
            if self.deepgram is None:
                raise ValueError("Deepgram STT not provided")
            self.logger.info("STT: using deepgram through asynchronous")
            return await self.deepgram.transcribe_raw_async(audio_data=audio_data)
        except Exception as e:
            self.logger.info(f"STT: using whisper, others failed due to {e}")
            return self.whisper.transcribe_raw(audio_data)
