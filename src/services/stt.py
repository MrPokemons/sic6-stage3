import tempfile
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration


class SpeechToText:
    def __init__(self):
        self.processor = WhisperProcessor.from_pretrained("cahya/whisper-medium-id", local_files_only=True)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            "cahya/whisper-medium-id",
            local_files_only=True,
        )
        self.model.eval()

    def transcribe(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()

            waveform, sample_rate = torchaudio.load(temp_audio.name)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=16000
                )
                waveform = resampler(waveform)

            inputs = self.processor(
                waveform.squeeze(), return_tensors="pt", sampling_rate=16000
            )
            with torch.no_grad():
                generated_ids = self.model.generate(inputs.input_features)
                transcription = self.processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0]
                return transcription
