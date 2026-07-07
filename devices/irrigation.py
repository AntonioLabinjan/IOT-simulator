"""Irrigation pump actuator: subscribes to pump commands, toggles state, reports status."""
from __future__ import annotations

import logging
import time

from common.config import MQTT, TOPICS
from common.models import ActuatorCommand, ActuatorState, ActuatorStatus
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("irrigation")


class IrrigationPump:
    """Virtual irrigation pump actuator."""

    def __init__(self) -> None:
        self._state = ActuatorState.OFF
        self._client = MQTTClientWrapper("irrigation-actuator", MQTT)

    def _on_command(self, topic: str, payload: str) -> None:
        command = ActuatorCommand.from_json(payload)
        if command.state != self._state:
            self._state = command.state
            print(f"PUMP -> {self._state.value}  ({command.reason})")
            logger.info("Pump state changed to %s (%s)", self._state.value, command.reason)
        self._publish_status()

    def _publish_status(self) -> None:
        status = ActuatorStatus.now("pump", self._state)
        self._client.publish(TOPICS.status_pump, status.to_json(), retain=True)

    def run(self) -> None:
        self._client.connect()
        self._client.subscribe(TOPICS.cmd_pump, self._on_command)
        self._publish_status()
        logger.info("Irrigation pump actuator started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down irrigation actuator")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    IrrigationPump().run()
