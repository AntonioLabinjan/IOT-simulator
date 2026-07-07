"""Central controller: subscribes to sensors, applies hysteresis rules, commands actuators.

Also exposes a simple interactive CLI (running in a background thread) that lets an
operator update thresholds at runtime; updates are applied immediately and broadcast
over MQTT so other components (e.g. the dashboard) can display current thresholds.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict

from common.config import MQTT, SIM, TOPICS, Thresholds, default_thresholds
from common.models import ActuatorCommand, ActuatorState, SensorReading
from common.mqtt_client import MQTTClientWrapper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("controller")


class GreenhouseController:
    """Applies hysteresis-based rules to sensor readings and issues actuator commands."""

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self._thresholds = thresholds or default_thresholds()
        self._lock = threading.Lock()
        self._client = MQTTClientWrapper("greenhouse-controller", MQTT)
        self._fan_on = False
        self._pump_on = False
        self._lamp_on = False

    # -- sensor handlers --------------------------------------------------
    def _on_temperature(self, topic: str, payload: str) -> None:
        reading = SensorReading.from_json(payload)
        with self._lock:
            t = self._thresholds
            if reading.value > t.temp_high and not self._fan_on:
                self._fan_on = True
                self._send_command(TOPICS.cmd_fan, "fan", ActuatorState.ON,
                                    f"temp {reading.value:.1f}C > {t.temp_high}C")
            elif reading.value < t.temp_low and self._fan_on:
                self._fan_on = False
                self._send_command(TOPICS.cmd_fan, "fan", ActuatorState.OFF,
                                    f"temp {reading.value:.1f}C < {t.temp_low}C")

    def _on_soil(self, topic: str, payload: str) -> None:
        reading = SensorReading.from_json(payload)
        with self._lock:
            t = self._thresholds
            if reading.value < t.soil_low and not self._pump_on:
                self._pump_on = True
                self._send_command(TOPICS.cmd_pump, "pump", ActuatorState.ON,
                                    f"soil {reading.value:.1f}% < {t.soil_low}%")
            elif reading.value > t.soil_high and self._pump_on:
                self._pump_on = False
                self._send_command(TOPICS.cmd_pump, "pump", ActuatorState.OFF,
                                    f"soil {reading.value:.1f}% > {t.soil_high}%")

    def _on_light(self, topic: str, payload: str) -> None:
        reading = SensorReading.from_json(payload)
        with self._lock:
            t = self._thresholds
            if reading.value < t.light_low and not self._lamp_on:
                self._lamp_on = True
                self._send_command(TOPICS.cmd_lamp, "lamp", ActuatorState.ON,
                                    f"light {reading.value:.0f}lux < {t.light_low}lux")
            elif reading.value > t.light_high and self._lamp_on:
                self._lamp_on = False
                self._send_command(TOPICS.cmd_lamp, "lamp", ActuatorState.OFF,
                                    f"light {reading.value:.0f}lux > {t.light_high}lux")

    def _send_command(self, topic: str, actuator: str, state: ActuatorState, reason: str) -> None:
        command = ActuatorCommand.now(actuator, state, reason)
        self._client.publish(topic, command.to_json())
        logger.info("Command -> %s %s (%s)", actuator, state.value, reason)

    # -- threshold updates --------------------------------------------------
    def _on_threshold_update(self, topic: str, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed threshold update: %s", payload)
            return
        with self._lock:
            for key, value in data.items():
                if hasattr(self._thresholds, key):
                    setattr(self._thresholds, key, float(value))
            logger.info("Thresholds updated: %s", asdict(self._thresholds))

    def update_threshold(self, field: str, value: float) -> None:
        """Programmatic/CLI entry point to update a single threshold immediately."""
        with self._lock:
            if hasattr(self._thresholds, field):
                setattr(self._thresholds, field, value)
                payload = json.dumps({field: value})
                self._client.publish(TOPICS.threshold_update, payload, retain=True)
                logger.info("Threshold '%s' set to %s", field, value)

    def _interactive_loop(self) -> None:
        """Runs in a background thread; lets an operator tweak thresholds live.

        Commands: `<field> <value>` e.g. `temp_high 32`. Type `help` for fields.
        """
        fields = list(asdict(self._thresholds).keys())
        print("Controller interactive mode. Commands: <field> <value> | help | quit")
        print(f"Fields: {', '.join(fields)}")
        while True:
            try:
                line = input().strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line == "help":
                print(f"Fields: {', '.join(fields)}")
                continue
            if line == "quit":
                break
            parts = line.split()
            if len(parts) != 2:
                print("Usage: <field> <value>")
                continue
            field, raw_value = parts
            if field not in fields:
                print(f"Unknown field '{field}'. Fields: {', '.join(fields)}")
                continue
            try:
                value = float(raw_value)
            except ValueError:
                print("Value must be numeric")
                continue
            self.update_threshold(field, value)
            print(f"OK: {field} = {value}")

    def run(self, interactive: bool = True) -> None:
        self._client.connect()
        self._client.subscribe(TOPICS.temperature, self._on_temperature)
        self._client.subscribe(TOPICS.soil, self._on_soil)
        self._client.subscribe(TOPICS.light, self._on_light)
        self._client.subscribe(TOPICS.threshold_update, self._on_threshold_update)
        logger.info("Controller started with thresholds: %s", asdict(self._thresholds))

        if interactive:
            thread = threading.Thread(target=self._interactive_loop, daemon=True)
            thread.start()

        try:
            while True:
                time.sleep(SIM.controller_interval_s)
        except KeyboardInterrupt:
            logger.info("Shutting down controller")
        finally:
            self._client.disconnect()


if __name__ == "__main__":
    GreenhouseController().run()
