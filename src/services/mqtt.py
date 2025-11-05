import time
import logging
from typing import Any, Optional
from paho.mqtt import client as mqtt_client


logger = logging.getLogger("mqtt")


class CustomMQTTClient:
    FIRST_RECONNECT_DELAY = 1
    RECONNECT_RATE = 2
    MAX_RECONNECT_COUNT = 5
    MAX_RECONNECT_DELAY = 60

    def __init__(
        self,
        client_id: str,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: str = "username",
        password: str = "password",
    ):
        self._client = mqtt_client.Client(
            client_id=client_id,
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
        )
        self._client.username_pw_set(username, password)
        self._setup_on_connect()
        self._setup_on_disconnect()
        self._client.connect(broker_host, broker_port)

    @property
    def client(self) -> mqtt_client.Client:
        return self._client

    def _setup_on_connect(self):
        def on_connect(
            client: mqtt_client.Client,
            userdata: Any,
            flags: mqtt_client.ConnectFlags,
            rc: mqtt_client.ReasonCode,
            properties: Optional[mqtt_client.Properties]
        ):
            if rc == 0:
                logger.info("Connected to MQTT Broker!")
            else:
                logger.error(f"Failed to connect, return code {rc}")

        self._client.on_connect = on_connect

    def _setup_on_disconnect(self):
        def on_disconnect(
            client: mqtt_client.Client,
            userdata: Any,
            flags: mqtt_client.ConnectFlags,
            rc: mqtt_client.ReasonCode,
            properties: Optional[mqtt_client.Properties]
        ):
            logger.warning(f"Disconnected with result code {rc}")
            reconnect_count, reconnect_delay = 0, self.FIRST_RECONNECT_DELAY
            while reconnect_count < self.MAX_RECONNECT_COUNT:
                logger.info(f"Reconnecting in {reconnect_delay} seconds")
                time.sleep(reconnect_delay)

                try:
                    client.reconnect()
                    logger.info("Reconnected successfully")
                    return
                except Exception as e:
                    logger.warning(f"{repr(e)}. Reconnect failed. Retrying...")

                reconnect_delay *= self.RECONNECT_RATE
                reconnect_delay = min(reconnect_delay, self.MAX_RECONNECT_DELAY)
                reconnect_count += 1

            logger.error(f"Reconnect failed after {reconnect_count} attemps. Exitting...")

        self._client.on_disconnect = on_disconnect
