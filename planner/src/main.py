from handlers.mqtt_handler import MQTTHandler
from planner import Planner
import json
import threading
import time
from planner_manager import PlannerManager
import copy
from datetime import datetime
import os
from paho.mqtt.client import Client, MQTTMessage

PATIENT_ID = os.getenv("PATIENT_ID", "p1")
SYMPTOMS_TOPIX_PREFIX = os.getenv("SYMPTOMS_TOPIX_PREFIX") # input
THERAPIES_TOPICS_PREFIX = os.getenv("THERAPIES_TOPICS_PREFIX") # output
MQTT_USERNAME = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

def on_message(client, userdata, message):
    topic = message.topic
    payload = json.loads(message.payload.decode())

    # acrss/symptoms/{patient_id}
    patient_id = topic.split("/")[-1]

    therapy = PlannerManager.process_symptoms(patient_id, payload)

    topic_out = f"{THERAPIES_TOPICS_PREFIX}/{patient_id}"
    client.publish(topic_out, json.dumps(therapy), qos=1)

    print(f"[PLANNER] Therapy published for patient {patient_id}")

def main():
    mqtt_client: Client = MQTTHandler.get_client(
    client_id="planner",              
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD,
    subscribe_topics=f"{SYMPTOMS_TOPIX_PREFIX}/+")
    MQTTHandler.set_on_message(mqtt_client, on_message)
    MQTTHandler.connect(mqtt_client, blocking = True)




if __name__ == "__main__":
    main()