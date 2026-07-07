"""Grow lamp actuator: subscribes to lamp commands, toggles state, reports status."""
from __future__ import annotations

import logging
import time

from common.config import MQTT, TOPICS
from common.models import ActuatorCommand, ActuatorState, ActuatorStatus
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("lamp")


class Lamp:
    """Virtual grow-lamp actuator."""

    def __init__(self) -> None:
        self._state = ActuatorState.OFF
        self._client = MQTTClientWrapper("lamp-actuator", MQTT)

    def _on_command(self, topic: str, payload: str) -> None:
        command = ActuatorCommand.from_json(payload)
        if command.state != self._state:
            self._state = command.state
            print(f"LAMP -> {self._state.value}  ({command.reason})")
            logger.info("Lamp state changed to %s (%s)", self._state.value, command.reason)
        self._publish_status()

    def _publish_status(self) -> None:
        status = ActuatorStatus.now("lamp", self._state)
        self._client.publish(TOPICS.status_lamp, status.to_json(), retain=True)

    def run(self) -> None:
        self._client.connect()
        self._client.subscribe(TOPICS.cmd_lamp, self._on_command)
        self._publish_status()
        logger.info("Lamp actuator started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down lamp actuator")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    Lamp().run()
