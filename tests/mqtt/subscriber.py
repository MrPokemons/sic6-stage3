from paho.mqtt import client as mqtt_client
from src.services.mqtt import CustomMQTTClient


def subscribe(client: mqtt_client.Client, topic: str):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(topic)
    client.on_message = on_message


def main():
    client = CustomMQTTClient(
        client_id="python-paho-subscriber-1",
        username="user-test-1",
        password="user-test-password",
    ).client
    subscribe(client, topic="python/paho")
    client.loop_forever()


if __name__ == "__main__":
    main()
