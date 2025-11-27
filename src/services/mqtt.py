import asyncio
import logging
from typing import Any
from fastapi_mqtt import FastMQTT, MQTTConfig
from gmqtt import Client as MQTTClient

from config.settings import SETTINGS


FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 5
MAX_RECONNECT_DELAY = 60

logger = logging.getLogger("mqtt")

mqtt_config = MQTTConfig(
    host=SETTINGS.MQTT.BROKER_HOST,
    port=SETTINGS.MQTT.BROKER_PORT,
    username=SETTINGS.MQTT.USERNAME,
    password=SETTINGS.MQTT.PASSWORD,
)
fast_mqtt = FastMQTT(config=mqtt_config, client_id=SETTINGS.MQTT.CLIENT_ID)


@fast_mqtt.on_connect()
def connect(client: MQTTClient, flags: int, rc: int, properties: Any):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    else:
        logger.error(f"Failed to connect, return code {rc}")


@fast_mqtt.on_disconnect()
async def disconnect(client: MQTTClient, packet, exc=None):
    logger.warning(f"Disconnected with result code {repr(exc)}")
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logger.info(f"Reconnecting in {reconnect_delay} seconds")
        await asyncio.sleep(reconnect_delay)

        try:
            await client.reconnect()
            logger.info("Reconnected successfully")
            return
        except Exception as e:
            logger.warning(f"{repr(e)}. Reconnect failed. Retrying...")

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1

    logger.error(f"Reconnect failed after {reconnect_count} attemps. Exitting...")


@fast_mqtt.on_subscribe()
def subscribe(client: MQTTClient, mid: int, qos: int, properties: Any):
    logger.info(f"Subscribed {repr(client)}, {repr(mid)}, {repr(qos)}, {repr(properties)}")
