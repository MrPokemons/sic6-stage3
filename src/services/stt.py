from typing import Union

import tempfile
import numpy as np
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration


class SpeechToText:
    SAMPLE_RATE = 16000

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
            return self.transcribe(waveform=waveform, sample_rate=sample_rate)

    def transcribe(self, waveform: Union[torch.Tensor, np.ndarray], sample_rate: int) -> str:
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
