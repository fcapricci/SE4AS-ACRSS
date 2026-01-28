from os import getenv
import paho.mqtt.client as mqtt
from paho.mqtt.reasoncodes import ReasonCode

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

        ## Set monitoring callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_publish = cls.on_publish
        client.on_disconnect = cls.on_disconnect

        # Set instance
        cls.CLIENT = client
    
    @classmethod
    def set_on_message(cls, on_message_callback) -> None:
        cls.CLIENT.on_message = on_message_callback

    @classmethod
    def get_therapies(cls) -> None:

        # Connect client with broker
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
