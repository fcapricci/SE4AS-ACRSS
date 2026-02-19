from abc import ABC, abstractmethod

from os import getenv
from typing import Any

from paho.mqtt.client import Client, MQTTMessage
from handlers.mqtt_handler import MQTTHandler

from patient import Patient

ACTIONS_TOPICS_PREFIX : str = getenv("ACTIONS_TOPICS_PREFIX")

# Actuator abstract base class
class Actuator(ABC):

    def __init__(self, patient : Patient, name : str):
        self.patient : Patient = patient

        self.name : str = name
        
        self.username : str = f"{name}#{patient.get_id()}"

        print(f"[{self.username.upper()}]: Starting...")

        # Setup MQTT client

        ## Initialize client
        mqtt_username = getenv("MQTT_USER")
        mqtt_password = getenv("MQTT_PASSWORD")

        subscribe_topic = f"{ACTIONS_TOPICS_PREFIX}/{patient.get_id()}/{name}"

        self.mqtt_client : Client = MQTTHandler.get_client(
            self.username,      
            mqtt_username,          
            mqtt_password,      
            subscribe_topic
        )

        ## Set instance as client data
        ## Needed to trigger activation on message
        userdata : dict = self.mqtt_client.user_data_get()
        userdata["parent"] = self

        ## Set on message callback
        MQTTHandler.set_on_message(self.mqtt_client, Actuator._on_message)

    @abstractmethod
    def _activate(self, action : Any)-> None:
        pass

    @staticmethod
    def _on_message(client : Client, userdata : dict[str, Any], message : MQTTMessage):

        # Parse action
        action = message.payload.decode()

        # Activate
        parent : Actuator = userdata["parent"]
        parent._activate(action)

    def connect(self) -> None:
        MQTTHandler.connect(self.mqtt_client, blocking = False)