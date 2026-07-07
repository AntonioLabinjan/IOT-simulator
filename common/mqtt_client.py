"""Reusable MQTT client wrapper built on paho-mqtt.

Provides a small, dependency-light abstraction so devices, controller and
dashboard don't repeat connection/callback boilerplate.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from common.config import MQTTConfig

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, str], None]  # (topic, payload) -> None


class MQTTClientWrapper:
    """Thin wrapper around paho-mqtt with simple subscribe/publish helpers."""

    def __init__(self, client_id: str, config: MQTTConfig) -> None:
        self._config = config
        self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._handlers: dict[str, MessageHandler] = {}
        self._connected = False

    # -- connection lifecycle -------------------------------------------------
    def connect(self) -> None:
        logger.info("Connecting to MQTT broker %s:%s", self._config.host, self._config.port)
        self._client.connect(self._config.host, self._config.port, self._config.keepalive)
        self._client.loop_start()

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if rc == 0:
            self._connected = True
            logger.info("MQTT connected (rc=%s)", rc)
            for topic in self._handlers:
                client.subscribe(topic)
        else:
            logger.error("MQTT connection failed (rc=%s)", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        self._connected = False
        logger.warning("MQTT disconnected (rc=%s)", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        handler = self._handlers.get(msg.topic)
        if handler is None:
            # fall back to wildcard-registered handlers
            for pattern, h in self._handlers.items():
                if mqtt.topic_matches_sub(pattern, msg.topic):
                    handler = h
                    break
        if handler is not None:
            try:
                handler(msg.topic, msg.payload.decode("utf-8"))
            except Exception:  # noqa: BLE001 - log and continue, one bad message shouldn't crash the client
                logger.exception("Error handling message on topic %s", msg.topic)

    # -- pub/sub ---------------------------------------------------------------
    def publish(self, topic: str, payload: str, retain: bool = False, qos: int = 0) -> None:
        self._client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic: str, handler: MessageHandler, qos: int = 0) -> None:
        self._handlers[topic] = handler
        if self._connected:
            self._client.subscribe(topic, qos=qos)

    @property
    def connected(self) -> bool:
        return self._connected
