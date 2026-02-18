import os
import paho.mqtt.client as mqtt
from handlers.mqtt_handler import MQTTHandler

ACTIONS_TOPICS_PREFIX = os.getenv("ACTIONS_TOPICS_PREFIX")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")



class OxygenFlowRegulator:

    def __init__(self, patient):
        self.patient = patient

        subscribe_topics = f"{ACTIONS_TOPICS_PREFIX}/{self.patient.patient_id}/oxygen_flow_regulator"
        self.client = MQTTHandler.get_client(
        client_id=f"ox_flow_regulator_{patient}",
        username=MQTT_USER,
        password=MQTT_PASSWORD,
        subscribe_topics=subscribe_topics
        )
        MQTTHandler.connect(self.client, blocking=False)
        MQTTHandler.set_on_message(self.client,self.on_message)

    def on_message(self, client, userdata, msg):
        try:
            flow = float(msg.payload.decode())
            self.patient.oxygen_flow = flow
            print(f"[OXYGEN-{self.patient.patient_id}] Flow set to {flow}")
        except ValueError:
            print("Invalid oxygen flow payload")
