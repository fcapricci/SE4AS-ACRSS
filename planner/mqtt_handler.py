from os import getenv
import json
import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode
import os
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

SOURCE = "sim"
PATIENT_ID = os.getenv("PATIENT_ID", "p1")
ANAYZER_TOPICS = f"acrss/analyzer/{PATIENT_ID}/status" # read 
PLANNER_TOPIC = "acrss/plan/{PATIENT_ID}" #write
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")


class MQTT_Handler:



    CLIENT = None

    @classmethod
    def initialize_client(cls) -> None:

        # Initialize instance

        ## CallbackAPIVersion.VERSION1 deprecated 
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

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

    @classmethod
    def on_connect(cls, client, userdata, flags, reason_code : ReasonCode, properties) -> None:

        connection_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f'[EXECUTOR]: Connection to broker {connection_result} with reason code {reason_code}.')

        if connection_result == "succeeded":
            cls.CLIENT.subscribe(ANAYZER_TOPICS, qos=2)
    
    @classmethod
    def on_message(cls, client, userdata, message : mqtt.MQTTMessage) -> None:
        data = json.loads(message.payload.decode())
        print(data)
        cls.received_message = data

    @classmethod
    def get_received_message(cls):
        return cls.received_message 
    
    @classmethod
    def publish(cls,topic,obj):
        cls.CLIENT.publish(topic,payload=json.dumps(obj),qos=1)
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
