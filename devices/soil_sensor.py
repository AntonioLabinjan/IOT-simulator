"""Soil moisture sensor: drains over time, rises while irrigation pump is active."""
from __future__ import annotations

import logging
import random
import time

from common.config import MQTT, SIM, TOPICS
from common.models import ActuatorState, ActuatorStatus, SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("soil_sensor")


class SoilMoistureSensor:
    """Simulates soil moisture (%) that drains naturally and rises during irrigation."""

    def __init__(self, start_value: float = 45.0, min_value: float = 0.0, max_value: float = 100.0) -> None:
        self._value = start_value
        self._min = min_value
        self._max = max_value
        self._pump_on = False
        self._client = MQTTClientWrapper("soil-sensor", MQTT)

    def _on_pump_status(self, topic: str, payload: str) -> None:
        status = ActuatorStatus.from_json(payload)
        self._pump_on = status.state == ActuatorState.ON

    def _step(self) -> float:
        noise = random.uniform(-0.2, 0.2)
        if self._pump_on:
            self._value += SIM.soil_irrigation_gain + noise
        else:
            self._value -= SIM.soil_drain_rate + max(0.0, noise)
        self._value = min(self._max, max(self._min, self._value))
        return self._value

    def run(self) -> None:
        self._client.connect()
        self._client.subscribe(TOPICS.status_pump, self._on_pump_status)
        logger.info("Soil moisture sensor started")
        try:
            while True:
                value = self._step()
                reading = SensorReading.now("soil", value, "%")
                self._client.publish(TOPICS.soil, reading.to_json())
                logger.info("Published soil=%.2f%% (pump_on=%s)", value, self._pump_on)
                time.sleep(SIM.sensor_interval_s)
        except KeyboardInterrupt:
            logger.info("Shutting down soil sensor")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    SoilMoistureSensor().run()
