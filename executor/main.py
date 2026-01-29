from mqtt_handler import MQTT_Handler
from parser import Parser
import json

from paho.mqtt.client import MQTTMessage
from therapy import Therapy

# Initialize and setup MQTT client instance
MQTT_Handler.initialize_client()

# Define message-handling callback
def on_message(client, userdata, message : MQTTMessage) -> None:
    
    # Build therapy object

    ## Parse patient id from topic name: "therapies/{patient_id}"
    patient_id = int(message.topic.split("/")[1])

    ## Parse fields values from message payload
    data = json.loads(message.payload.decode())

    therapy : Therapy = Therapy(
        patient_id,
        data["ox_therapy"],
        data["fluids"],
        data["esmolo_beta_blocking"],
        data["alert"]
    )

    # Define actuators actions given the therapy
    actions : dict = Parser.define_actuators_actions(therapy)

    # Notify actuators with their actions
    MQTT_Handler.publish_actuators_actions(
        actions, 
        therapy.get_patient_id()
    )

# Set callback
MQTT_Handler.set_on_message(on_message)

# Start catching messages
MQTT_Handler.get_therapies()