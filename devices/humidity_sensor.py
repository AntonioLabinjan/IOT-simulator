"""Air humidity sensor: gradual random walk, loosely inverse to temperature swings."""
from __future__ import annotations

import logging
import random
import time

from common.config import MQTT, SIM, TOPICS
from common.models import SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("humidity_sensor")


class HumiditySensor:
    """Simulates relative air humidity (%) via a bounded random walk."""

    def __init__(self, start_value: float = 55.0, min_value: float = 20.0, max_value: float = 95.0) -> None:
        self._value = start_value
        self._min = min_value
        self._max = max_value
        self._client = MQTTClientWrapper("humidity-sensor", MQTT)

    def _step(self) -> float:
        noise = random.uniform(-SIM.humidity_walk_step, SIM.humidity_walk_step)
        self._value = min(self._max, max(self._min, self._value + noise))
        return self._value

    def run(self) -> None:
        self._client.connect()
        logger.info("Humidity sensor started")
        try:
            while True:
                value = self._step()
                reading = SensorReading.now("humidity", value, "%")
                self._client.publish(TOPICS.humidity, reading.to_json())
                logger.info("Published humidity=%.2f%%", value)
                time.sleep(SIM.sensor_interval_s)
        except KeyboardInterrupt:
            logger.info("Shutting down humidity sensor")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    HumiditySensor().run()
