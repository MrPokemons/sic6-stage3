import io
import soundfile as sf
import torch
from transformers import AutoTokenizer, VitsModel


class TextToSpeech:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-ind", local_files_only=True,)
        self.model = VitsModel.from_pretrained("facebook/mms-tts-ind", local_files_only=True,)
        self.model.eval()

    def synthesize(self, text: str) -> bytes:
        inputs = self.tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)
            waveform = outputs.waveform.squeeze().cpu().numpy()

        with io.BytesIO() as buffer:
            sf.write(buffer, waveform, 16000, format="WAV")
            return buffer.getvalue()
