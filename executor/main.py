from mqtt_handler import MQTT_Handler
from parser import Parser

# Initialize and setup client instance
MQTT_Handler.initialize_client()

# Connect client with broker
# Subscribe to "therapies" topic
# Start network loop
MQTT_Handler.get_therapies()

# Define actuators actions given the therapy
actions : dict = Parser.define_actuators_actions(therapy)

# Notify actuators with their actions
MQTT_Handler.publish_actuators_actions(
    actions, 
    therapy.get_patient_id()
)