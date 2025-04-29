import json
import numpy as np
from typing import Tuple, Annotated
from typing_extensions import TypedDict


class MessageMetadata(TypedDict):
    seq: int
    total_seq: int
    sample_rate: int
    channels: int
    dtype: str


class MessagePacker:
    def __init__(self, separator: bytes = b"---ENDJSON---"):
        self.separator = separator

    def pack(self, metadata: MessageMetadata, data: np.ndarray) -> bytes:
        meta_json = json.dumps(metadata)
        meta_bytes = meta_json.encode("utf-8")
        data_bytes = data.tobytes()
        return meta_bytes + self.separator + data_bytes

    def unpack(
        self, packet: bytes
    ) -> Tuple[MessageMetadata, Annotated[np.ndarray, "data"]]:
        meta_bytes, data_bytes = packet.split(self.separator, 1)
        metadata: MessageMetadata = json.loads(meta_bytes.decode("utf-8"))
        audio_chunk = np.frombuffer(data_bytes, dtype=metadata["dtype"])
        if metadata["channels"] > 1:
            audio_chunk = audio_chunk.reshape(-1, metadata["channels"])
        return metadata, audio_chunk
