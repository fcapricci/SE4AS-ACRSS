from os import getenv
from typing import Any
import json
import time
import signal
import sys

from handlers.mqtt_handler import MQTTHandler
from parser import Parser
from therapy import Therapy

from paho.mqtt.client import Client, MQTTMessage

MQTT_USERNAME = getenv("MQTT_USER")
MQTT_PASSWORD = getenv("MQTT_PASSWORD")

THERAPIES_TOPICS_PREFIX = getenv("THERAPIES_TOPICS_PREFIX")
ACTIONS_TOPICS_PREFIX = getenv("ACTIONS_TOPICS_PREFIX") 

# Initialize MQTT client
mqtt_client: Client = MQTTHandler.get_client(
    client_id="executor",              
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD,
    subscribe_topics=f"{THERAPIES_TOPICS_PREFIX}/+"
)

# Define message-handling callback
def on_message(client: Client, userdata: dict[str, Any], message: MQTTMessage) -> None:

    

    patient_id = int(message.topic.split("/")[-1])

    data = json.loads(message.payload.decode())

    therapy = Therapy(
        patient_id,
        data["ox_therapy"],
        data["fluids"],
        data["carvedilolo_beta_blocking"],
        data["alert"]
    )

    actions = Parser.define_actuators_actions(therapy)

    messages = [
        (f"{ACTIONS_TOPICS_PREFIX}/{patient_id}/{actuator}", actions[actuator])
        for actuator in actions.keys()
    ]

    
    
    MQTTHandler.publish(client=client, messages=messages)

# Graceful shutdown handler
def shutdown(sig, frame):
    print("[EXECUTOR]: Shutting down...")
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Set callback
MQTTHandler.set_on_message(mqtt_client, on_message)

# Connect
MQTTHandler.connect(mqtt_client, blocking=True)


while True:
    time.sleep(1)
