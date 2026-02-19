from os import getenv
import json
import signal
import sys

from typing import Any

from paho.mqtt.client import Client, MQTTMessage
from handlers.mqtt_handler import MQTTHandler

from models.therapy import Therapy

from parser import Parser

MQTT_USERNAME = getenv("MQTT_USER")
MQTT_PASSWORD = getenv("MQTT_PASSWORD")

THERAPIES_TOPICS_PREFIX = getenv("THERAPIES_TOPICS_PREFIX")
ACTIONS_TOPICS_PREFIX = getenv("ACTIONS_TOPICS_PREFIX") 

# Initialize MQTT client
mqtt_client: Client = MQTTHandler.get_client(
    client_id="executor",              
    username = MQTT_USERNAME,
    password = MQTT_PASSWORD,
    subscribe_topics = f"{THERAPIES_TOPICS_PREFIX}/+"
)

# Define message-handling callback
def on_message(client: Client, userdata: dict[str, Any], message: MQTTMessage) -> None:

    # Parse patient id from topic name
    patient_id = int(message.topic.split("/")[-1])

    # Parse therapy data from message payload
    data = json.loads(message.payload.decode())

    # Build therapy
    therapy = Therapy(
        data["ox_therapy"],
        data["fluids"],
        data["carvedilolo_beta_blocking"],
        data["alert"]
    )

    # Define actuators actions given the therapy
    actions = Parser.define_actuators_actions(therapy)

    # Build messages
    messages = [
        (f"{ACTIONS_TOPICS_PREFIX}/{patient_id}/{actuator}", actions[actuator])
        for actuator in actions.keys()
    ]

    # Publish actuators actions
    MQTTHandler.publish(
        client = client,
        messages = messages
    )
    
# Set callback
MQTTHandler.set_on_message(mqtt_client, on_message)

# Connect
MQTTHandler.connect(mqtt_client, blocking = True)