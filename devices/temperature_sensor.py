"""Temperature sensor: random-walk value nudged by the day/night cycle."""
from __future__ import annotations

import logging
import random
import time

from common.config import MQTT, SIM, TOPICS
from common.daycycle import sun_intensity
from common.models import SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("temperature_sensor")


class TemperatureSensor:
    """Simulates greenhouse air temperature via a bounded random walk."""

    def __init__(self, start_value: float = 22.0, min_value: float = 10.0, max_value: float = 42.0) -> None:
        self._value = start_value
        self._min = min_value
        self._max = max_value
        self._start_time = time.time()
        self._client = MQTTClientWrapper("temperature-sensor", MQTT)

    def _step(self) -> float:
        # Sun intensity nudges the walk's drift upward during the day.
        drift = (sun_intensity(self._start_time) - 0.4) * 0.05
        noise = random.uniform(-SIM.temp_walk_step, SIM.temp_walk_step)
        self._value = min(self._max, max(self._min, self._value + drift + noise))
        return self._value

    def run(self) -> None:
        self._client.connect()
        logger.info("Temperature sensor started")
        try:
            while True:
                value = self._step()
                reading = SensorReading.now("temperature", value, "C")
                self._client.publish(TOPICS.temperature, reading.to_json())
                logger.info("Published temperature=%.2fC", value)
                time.sleep(SIM.sensor_interval_s)
        except KeyboardInterrupt:
            logger.info("Shutting down temperature sensor")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    TemperatureSensor().run()
