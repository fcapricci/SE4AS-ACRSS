from os import getenv
from typing import Any
import json

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
def on_message(client : Client, userdata : dict[str, Any], message : MQTTMessage) -> None:

    print(f"[{client.username.upper()}]: Received therapy at {message.topic}.") 
    
    # Build therapy object

    ## Parse patient id from topic name: "therapies/{patient_id}"
    patient_id = int(message.topic.split("/")[1])


    ## Parse fields values from message payload
    data = json.loads(message.payload.decode())

    therapy : Therapy = Therapy(
        patient_id,
        data["oxygen"],
        data["fluids"],
        data["beta_blocking"],
        data["alert"]
    )

    # Define actuators actions given the therapy
    print(f"[{client.username.upper()}]: Defining actuators actions based on given therapy...")
    actions : dict[str, Any] = Parser.define_actuators_actions(therapy)

    # Notify actuators with their actions

    ## Build messages: (topic, payload)
    messages = [
        (f"{ACTIONS_TOPICS_PREFIX}/{patient_id}/{actuator}", actions[actuator])
        for actuator in actions.keys()
    ]

    ## Publish
    print(f"[{client.username.upper()}]: Publishing actuators actions...")
    MQTTHandler.publish(
        client = client,
        messages = messages
    )

# Set callback
MQTTHandler.set_on_message(mqtt_client, on_message)

# Start catching messages
MQTTHandler.connect(mqtt_client, blocking = True)