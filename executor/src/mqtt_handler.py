from os import getenv
import paho.mqtt.client as mqtt

from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.enums import MQTTProtocolVersion

class MQTT_Handler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = getenv("MQTT_PORT")

    THERAPIES_TOPICS = "therapies/+"
    ACTUATORS_TOPIC= "actuators"

    CLIENT = None

    @classmethod
    def initialize_client(cls) -> None:

        # Initialize instance
        print("[EXECUTOR]: Initializing MQTT client...")

        ## MQTTProtocolVersion 3.1.1 obsolete
        ## CallbackAPIVersion.VERSION1 deprecated
        client = mqtt.Client(
            protocol = MQTTProtocolVersion.MQTTv5,
            callback_api_version = mqtt.CallbackAPIVersion.VERSION2
        )

        # Setup

        ## Set callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_publish = cls.on_publish
        client.on_disconnect = cls.on_disconnect

        # Set instance
        cls.CLIENT = client
        print("[EXECUTOR]: MQTT client initialization succeeded.")
    
    @classmethod
    def set_on_message(cls, on_message_callback) -> None:
        cls.CLIENT.on_message = on_message_callback

    @classmethod
    def get_therapies(cls) -> None:

        # Connect client with broker
        print("[EXECUTOR]: Connecting to broker...")

        cls.CLIENT.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT
        )

        # Start network loop
        cls.CLIENT.loop_forever()

    @classmethod
    def on_connect(cls, client, userdata, flags, reason_code : ReasonCode, properties) -> None:

        connection_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f"[EXECUTOR]: Connection to broker {connection_result} with reason code {reason_code}.")

        if connection_result == "succeeded":

            # Subscribe on connection succeeded
            # Handles reconnection scenarios
            print(f"[EXECUTOR]: Subscribing to \"{cls.THERAPIES_TOPICS}\"...")

            cls.CLIENT.subscribe(
                topic = cls.THERAPIES_TOPICS,
                qos = 2
            )

    @classmethod
    def publish_actuators_actions(cls, actions : dict, patientID : int) -> None:

        # Send publish messages
        publish_messages : tuple[str, mqtt.MQTTMessageInfo] = [
            cls.CLIENT.publish(topic = f'{cls.ACTUATORS_TOPIC}/{patientID}/{actuator}', payload = actions[actuator])
            for actuator in actions.keys()
        ]
        
        # Wait for all messages to return (either with success or failure)
        for topic, message in publish_messages:
            message.wait_for_publish()

            # Print results
            publish_result = "succeeded" if message.is_published() else "failed"
            print(f"[EXECUTOR]: Actuator action publish at {topic} {publish_result} with reason code {message}")


    
    #
    # Monitoring callbacks
    #
    
    @staticmethod
    def on_subscribe(client, userdata, mid, reason_code_list : list[ReasonCode], properties) -> None:
        
        # Log subscriptions results
        # Assume topics subscribed in ascending order

        subscription_successes : int = 0

        topics = [ f"therapies/{patient_id}" for patient_id in range(1, len(reason_code_list) + 1) ]
        for topic, reason_code in zip(topics, reason_code_list):

            subscription_result = "succeeded" if not reason_code.is_failure else "failed"
            # print(f"[EXECUTOR]: Subscription to \"{topic}\" {subscription_result} with reason code {reason_code}.")

            if subscription_result == "succeeded":
                
                # Increase subscription_successes
                subscription_successes += 1

                # Print topic QoS
                # print(f"[EXECUTOR]: Broker granted QoS level {reason_code.value}.")

        print(f"[EXECUTOR]: {len(reason_code_list)} therapies topics found. Successfully subscribed to {subscription_successes}.")
        

    # QoS = 2 => Called on broker PUBCOMP
    @staticmethod
    def on_publish(client, userdata, mid, reason_code : ReasonCode, properties) -> None:

        publish_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f"[EXECUTOR]: Actuator action publish at {topic} {publish_result} with reason code {reason_code}.")
        

    @staticmethod
    def on_disconnect() -> None:
        print("Disconnect")
