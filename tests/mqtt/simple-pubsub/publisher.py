import time
from paho.mqtt import client as mqtt_client

from src.services.mqtt import CustomMQTTClient


def publish(client: mqtt_client.Client, topic: str):
    msg_count = 1
    while True:
        time.sleep(1)
        msg = f"messages: {msg_count}"
        result = client.publish(topic, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{msg}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic {topic}")
        msg_count += 1
        if msg_count > 5:
            break



def main():
    client = CustomMQTTClient(
        client_id="python-paho-publisher-1",
        username="user-test-1",
        password="user-test-password",
    ).client
    client.loop_start()
    publish(client, topic="python/paho")
    client.loop_stop()


if __name__ == "__main__":
    main()
