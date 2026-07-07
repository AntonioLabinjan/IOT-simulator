"""Light sensor: intensity (lux) driven primarily by the day/night cycle."""
from __future__ import annotations

import logging
import random
import time

from common.config import MQTT, SIM, TOPICS
from common.daycycle import sun_intensity
from common.models import SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("light_sensor")

MAX_DAYLIGHT_LUX = 800.0


class LightSensor:
    """Simulates ambient light intensity (lux), tracking the day/night cycle with noise."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._value = 0.0
        self._client = MQTTClientWrapper("light-sensor", MQTT)

    def _step(self) -> float:
        target = sun_intensity(self._start_time) * MAX_DAYLIGHT_LUX
        noise = random.uniform(-SIM.light_walk_step, SIM.light_walk_step)
        # ease toward the target instead of jumping straight to it
        self._value += (target - self._value) * 0.3 + noise
        self._value = max(0.0, self._value)
        return self._value

    def run(self) -> None:
        self._client.connect()
        logger.info("Light sensor started")
        try:
            while True:
                value = self._step()
                reading = SensorReading.now("light", value, "lux")
                self._client.publish(TOPICS.light, reading.to_json())
                logger.info("Published light=%.1f lux", value)
                time.sleep(SIM.sensor_interval_s)
        except KeyboardInterrupt:
            logger.info("Shutting down light sensor")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    LightSensor().run()
