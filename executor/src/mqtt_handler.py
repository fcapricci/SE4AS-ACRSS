from os import getenv
import paho.mqtt.client as mqtt

from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.enums import MQTTProtocolVersion

class MQTT_Handler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = int(getenv("MQTT_PORT"))

    THERAPIES_TOPICS = "therapies/+"
    ACTUATORS_TOPIC= "actuators"

    CLIENT = None

    @classmethod
    def initialize_client(cls) -> None:

        # Initialize instance
        print("[EXECUTOR]: Initializing MQTT client...")

        ## MQTTProtocolVersion 3.1.1 obsolete => No reason codes
        ## CallbackAPIVersion.VERSION1 deprecated
        client = mqtt.Client(
            protocol = MQTTProtocolVersion.MQTTv5,
            callback_api_version = mqtt.CallbackAPIVersion.VERSION2
        )

        # Setup

        ## Set callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_disconnect = cls.on_disconnect

        # Set instance
        cls.CLIENT = client

        # Print result
        print("[EXECUTOR]: MQTT client initialization succeeded.")
    
    @classmethod
    def set_on_message(cls, on_message_callback) -> None:
        cls.CLIENT.on_message = on_message_callback

    @classmethod
    def get_therapies(cls) -> None:

        # Connect client with broker
        print("[EXECUTOR]: Connecting to MQTT broker...")
        cls.CLIENT.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT
        )

        # Start network loop
        cls.CLIENT.loop_forever()

    @classmethod
    def on_connect(cls, client, userdata, flags, reason_code : ReasonCode, properties) -> None:

        connection_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f"[EXECUTOR]: Connection to MQTT broker {connection_result}. Reason code: {reason_code}.")

        if connection_result == "succeeded":

            # Subscribe on connection succeeded
            # Handles reconnection scenarios
            print(f"[EXECUTOR]: Subscribing to {cls.THERAPIES_TOPICS}...")

            cls.CLIENT.subscribe(
                topic = cls.THERAPIES_TOPICS,
                qos = 2
            )

    @classmethod
    def publish_actuators_actions(cls, actions : dict, patient_id : int) -> None:
        
        # Build patient actuators base topic
        patient_actuators_topic = f"{cls.ACTUATORS_TOPIC}/{patient_id}"
        print(f"[EXECUTOR]: Publishing actions...")

        # Loop over actuators
        # Send publish messages
        # Store messages with topic
        messages : list[tuple[str, mqtt.MQTTMessageInfo]] = [
            (
                f"{patient_actuators_topic}/{actuator}",
                cls.CLIENT.publish(f"{patient_actuators_topic}/{actuator}", actions[actuator])
            )
            for actuator in actions.keys()
        ]

        # Wait for messages to return
        for topic, message in messages:
            message.wait_for_publish(timeout=60)

            # Log results
            result = "succeeded" if message.is_published else "failed"
            print(f"[EXECUTOR]: Action publish to {topic} {result}. Reason code: {message.rc}.")

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
            print(f"[EXECUTOR]: Subscription to {topic} {subscription_result}. Reason code: {reason_code}.")

            if subscription_result == "succeeded":
                
                # Increase subscription_successes
                subscription_successes += 1

        print(f"[EXECUTOR]: {len(reason_code_list)} therapies topics found. Successfully subscribed to {subscription_successes}.")

    @staticmethod
    def on_disconnect(client, userdata, disconnect_flags, reason_code : ReasonCode, properties) -> None:

        if not reason_code == "Normal disconnection":
            print(f"[EXECUTOR]: Unexpected disconnection. Reason code: {reason_code}")
        
