from os import getenv
import json
import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode

from therapy import Therapy

class MQTT_Handler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = getenv("MQTT_PORT")

    THERAPIES_TOPICS = "therapies/+"
    ACTUATORS_TOPIC= "actuators"

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
        client.on_publish = cls.on_publish
        client.on_disconnect = cls.on_disconnect

        # Set instance
        cls.CLIENT = client

    @classmethod
    def get_therapies(cls) -> None:

        # Connect client to broker
        cls.CLIENT.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT
        )

        # Start network loop
        cls.CLIENT.loop_forever()

    @classmethod
    def on_connect(cls, client, userdata, flags, reason_code : ReasonCode, properties) -> None:

        connection_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f'[EXECUTOR]: Connection to broker {connection_result} with reason code {reason_code}.')

        if connection_result == "succeeded":

            # Subscribe on connection succeeded
            # to handle reconnection scenarios
            cls.CLIENT.subscribe(cls.THERAPIES_TOPICS, qos=2)
    
    @staticmethod
    def on_message(client, userdata, message : mqtt.MQTTMessage) -> None:
        
        # Build therapy object

        ## Parse patient id from topic name: "therapies/{patient_id}"
        patient_id = int(message.topic.split("/")[1])

        ## Parse fields values from message payload
        data = json.loads(message.payload.decode())

        therapy : Therapy = Therapy(
            patient_id,
            data["ox_therapy"],
            data["fluids"],
            data["carvedilolo_beta_blocking"],
            data["alert"]
        )

    @classmethod
    def publish_actuators_actions(cls, actions : dict, patientID : int) -> None:

        for actuator in actions.keys():
            cls.CLIENT.publish(
                topic = f'{cls.ACTUATORS_TOPIC}/{patientID}/{actuator}',
                payload = actions[actuator],
                qos = 2
            )
    
    #
    # Monitoring Callbacks
    #
    
    @staticmethod
    def on_subscribe(client, userdata, mid, reason_code_list : list[ReasonCode], properties) -> None:
        
        print(f"[EXECUTOR]: {len(reason_code_list)} topics found.")

        for reason_code in reason_code_list:

            subscription_result = "succeeded" if not reason_code.is_failure else "failed"
            print(f"[EXECUTOR]: Subscription to {topic} {subscription_result} with reason code {reason_code}.")

            if subscription_result == "succeeded":
                print(f"[EXECUTOR]: Broker grants QoS level {reason_code.value}.")

    # QoS = 2 => Called on broker PUBCOMP
    @staticmethod
    def on_publish() -> None:
        print("Publish")
        return NotImplemented

    @staticmethod
    def on_disconnect() -> None:
        print("Disconnect")
