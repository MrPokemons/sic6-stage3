import math
import soundfile as sf
import librosa
from typing import Any, Optional
from paho.mqtt import client as mqtt_client

from src.services.custom_mqtt import CustomMQTTClient
from src.utils.message_packer import MessagePacker, MessageMetadata
from src.controllers.pawpal_v2 import TOPIC_SPEAKER, TOPIC_COMMAND, TOPIC_RECORDING


DEVICE_ID = "pawpal-uuid-003"
MOCK_RECORDING = "/Users/appfuxion/Documents/Project/sic6-stage3/tests/test.wav"

def publish_mock_recording(
    client: mqtt_client.Client,
    message_packer: MessagePacker,
    *,
    target_sample_rate: Optional[int] = None
):
    audio_array, sample_rate = sf.read(MOCK_RECORDING, dtype="float32")
    if target_sample_rate and sample_rate != target_sample_rate:
        audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
        sample_rate = target_sample_rate

    num_channels = 1 if len(audio_array.shape) == 1 else audio_array.shape[1]
    samples_per_chunk = sample_rate * 20 // 1000
    total_seq = math.ceil(audio_array.shape[0] / samples_per_chunk)
    for seq in range(total_seq):
        chunk = audio_array[samples_per_chunk * seq : samples_per_chunk * (seq + 1)]
        chunk_metadata = MessageMetadata(
            seq=seq + 1,
            total_seq=total_seq,
            sample_rate=sample_rate,
            channels=num_channels,
            dtype=str(audio_array.dtype),
        )
        packet = message_packer.pack(metadata=chunk_metadata, data=chunk)
        client.publish(
            topic=TOPIC_RECORDING.format(device_id=DEVICE_ID),
            payload=packet,
            qos=2 if seq + 1 == total_seq else 0,
        )


def subscribe_server_message(client: mqtt_client.Client, message_packer: MessagePacker):
    def on_message(client: mqtt_client.Client, userdata: Any, msg: mqtt_client.MQTTMessage):
        _t = (msg.topic.rsplit("/", 1) or [""])[-1]
        if _t == "command":
            server_cmd = msg.payload.decode()
            print(f"Received COMMAND {server_cmd!r} from {msg.topic!r} topic")
            if server_cmd == "record":
                print("Running 'record' command")
                publish_mock_recording(client=client, message_packer=message_packer)
        elif _t == "speaker":
            metadata, chunk = message_packer.unpack(msg.payload)
            print(f"Received SPEAKER {metadata!r} from {msg.topic!r} topic")

    client.subscribe(TOPIC_COMMAND.format(device_id=DEVICE_ID), qos=2)
    client.subscribe(TOPIC_SPEAKER.format(device_id=DEVICE_ID), qos=2)
    client.on_message = on_message


def main():
    message_packer = MessagePacker()
    client = CustomMQTTClient(
        client_id="client-pawpal-test1",
        username="client-pawpal-test1",
        password="client-pawpal-test1",
    ).client
    subscribe_server_message(client, message_packer)
    print("running, waiting for Server MQTT")
    client.loop_forever()


if __name__ == "__main__":
    main()
