from os import getenv
import json
import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode
import os
from planner_manager import PlannerManager

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

SOURCE = "sim"
SYMPTOMS_TOPIC = "acrss/symptoms/+"
PLANNER_TOPIC = "acrss/plan/{PATIENT_ID}" #write
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")


class MQTT_Handler:



    CLIENT = None

    @classmethod
    def initialize_client(cls) -> None:

        # Initialize instance

        ## CallbackAPIVersion.VERSION1 deprecated 
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if MQTT_USER and MQTT_PASSWORD:
           client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        # Setup

        ## Callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_message = cls.on_message
        client.on_disconnect = cls.on_disconnect

        # Set instance
        cls.CLIENT = client
        cls.received_message = None

    @classmethod
    def connect_to_mqtt(cls) -> None:

        # Connect client to broker
        cls.CLIENT.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        # Start network loop
        cls.CLIENT.loop_start()

    @staticmethod
    def on_connect(client, userdata, flags, reason_code: ReasonCode, properties) -> None:
        if not reason_code.is_failure:
            print("[PLANNER] Connected to MQTT broker")
            client.subscribe(SYMPTOMS_TOPIC, qos=1)


    
    @staticmethod
    def on_message(client, userdata, message):
        topic = message.topic
        payload = json.loads(message.payload.decode())

        # acrss/symptoms/{patient_id}
        patient_id = topic.split("/")[-1]

        therapy = PlannerManager.process_symptoms(patient_id, payload)

        topic_out = f"acrss/therapies/{patient_id}"
        client.publish(topic_out, json.dumps(therapy), qos=1)

        print(f"[PLANNER] Therapy published for patient {patient_id}")


    @classmethod
    def get_received_message(cls):
        return cls.received_message 
    
    

    @staticmethod
    def on_subscribe(client, userdata, mid, reason_code_list : list[ReasonCode], properties) -> None:
        
        print(f"{len(reason_code_list)} topics found.")

        for reason_code in reason_code_list:
            print(reason_code)
           

    # QoS = 2 => Called on broker PUBCOMP
    @staticmethod
    def on_publish() -> None:
        print("Publish")
        return NotImplemented

    @staticmethod
    def on_disconnect(client, userdata, reason_code, properties) -> None:
        print("Disconnect")
