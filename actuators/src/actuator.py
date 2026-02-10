from abc import ABC, abstractmethod

from os import getenv
from typing import Any

import paho.mqtt.client as mqtt
from handlers.mqtt_handler import MQTTHandler

ACTIONS_TOPICS_PREFIX : str = getenv("ACTIONS_TOPICS_PREFIX")

# Actuator abstract base class
class Actuator(ABC):

    def __init__(self, patient_id : int, name : str):
        self.patient_id : int = patient_id
        self.name : str = name
        self.username : str = f"{name}#{patient_id}"

        print(f"[{self.username.upper()}]: Starting...")

        # Setup MQTT client

        ## Initialize client
        password = None
        subscribe_topic = f"{ACTIONS_TOPICS_PREFIX}/{patient_id}/{name}"

        self.mqtt_client : mqtt.Client = MQTTHandler.get_client(
            self.username,
            password,
            subscribe_topic
        )

        ## Set instance as client data: needed to trigger activation on message.
        userdata : dict = self.mqtt_client.user_data_get()
        userdata["parent"] = self

        ## Set on message callback
        MQTTHandler.set_on_message(self.mqtt_client, Actuator._on_message)

    @abstractmethod
    def _activate(self, action : Any)-> None:
        pass

    @staticmethod
    def _on_message(client : mqtt.Client, userdata : dict[str, Any], message : mqtt.MQTTMessage):

        # Parse action
        action = message.payload.decode()

        # Activate
        parent : Actuator = userdata["parent"]
        parent._activate(action)

    def connect(self) -> None:
        MQTTHandler.connect(self.mqtt_client, blocking = False)