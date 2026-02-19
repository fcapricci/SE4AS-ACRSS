from abc import ABC, abstractmethod

from os import getenv
from time import time

from typing import Any

from patient import Patient

from paho.mqtt.client import Client
from handlers.mqtt_handler import MQTTHandler

SENSORS_TOPIC_PREFIX : str = getenv("SENSORS_TOPIC_PREFIX")

class Sensor(ABC):

    def __init__(self, patient : Patient, name : str, unit : str):
        self.patient : Patient = patient

        self.name : str = name
        self.unit : str = unit
        self.data : Any = None

        self.username : str = f"{self.name}#{self.patient.get_id()}"

        print(f"[{self.username.upper()}]: Starting...")

        # Setup MQTT client
        self.mqtt_username = getenv("MQTT_USER")
        self.mqtt_password = getenv("MQTT_PASSWORD")

        self.publish_topic = f"{SENSORS_TOPIC_PREFIX}/{self.patient.get_id()}/{self.name}"

        self.mqtt_client : Client = MQTTHandler.get_client(
            client_id = self.username,
            username = self.mqtt_username,
            password = self.mqtt_password,
            subscribe_topics = None
        )

    @abstractmethod
    def sense(self) -> None:
        pass

    def connect(self) -> None:
        MQTTHandler.connect(self.mqtt_client, blocking = False)

    def publish(self) -> None:

        # Build message
        payload = {
            "ts": int(time() * 1000),
            "value": self.data,
            "unit": self.unit,
            "source": "sim"
        }

        message = (
            self.publish_topic,
            payload
        )
        

        # Publish
        MQTTHandler.publish(self.mqtt_client, message)
    