from os import getenv

from typing import Any
from collections.abc import Callable

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.subscribeoptions import SubscribeOptions

class MQTTHandler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = int(getenv("MQTT_PORT"))

    @classmethod
    def get_client(cls, username : str, password : str, subscribe_topics : str | list[str] | None) -> mqtt.Client:

        # Initialize instance
        print(f"[{username.upper()}]: Initializing MQTT client...")

        ## Set MQTTProtocolVersion 5 for reason codes and authentication support.
        ## Set CallbackAPIVersion.VERSION2 as VERSION1 deprecated.
        client = mqtt.Client(
            protocol = MQTTProtocolVersion.MQTTv5,
            callback_api_version = mqtt.CallbackAPIVersion.VERSION2
        )

        # Setup

        ## Set username and password
        client.username_pw_set(
            username,
            password
        )

        ## Set callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_disconnect = cls.on_disconnect

        ## Set subscribe topics
        client.user_data_set({
            "subscribe_topics" : subscribe_topics
        })

        # Print result
        print(f"[{username.upper()}]: MQTT client initialization succeeded.")

        # Return instance
        return client
    
    @staticmethod
    def set_on_message(
        client : mqtt.Client,
        on_message_callback : Callable[[mqtt.Client, dict[str, Any], mqtt.MQTTMessage], None]) -> None:
        client.on_message = on_message_callback

    @classmethod
    def connect(cls, client : mqtt.Client, blocking : bool) -> None:

        # Connect client with broker
        print(f"[{client.username.upper()}]: Connecting to MQTT broker...")
        client.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT
        )

        # Start network loop
        if not blocking:

            ## On background thread
            client.loop_start()

        else:

            ## On main thread
            client.loop_forever()

    @staticmethod
    def on_connect(client : mqtt.Client, userdata : dict[str, Any], flags, reason_code : ReasonCode, properties) -> None:

        connection_result = "succeeded" if not reason_code.is_failure else "failed"
        print(f"[{client.username.upper()}]: Connection to MQTT broker {connection_result}. Reason code: {reason_code}.")

        # Subscribe on connection succeeded to handle reconnection scenarios
        if connection_result == "succeeded" and userdata["subscribe_topics"] is not None:

            topics = userdata["subscribe_topics"]

            # Build subscriptions: (topic, QoS)
            # Handle multiple topics scenario
            subscriptions = (topics, SubscribeOptions(qos=2)) if not isinstance(topics, list) else [(topic, SubscribeOptions(qos=2)) for topic in topics]

            print(f"[{client.username.upper()}]: Subscribing to {topics if not isinstance(topics, list) else ", ".join(topics)}...")
            client.subscribe(
                topic = subscriptions,
            )

    @staticmethod
    def publish(client : mqtt.Client, messages : list[ tuple[str, Any] ]) -> None:

        # Send messages
        # Store sent messages
        sent : list[ tuple[str, mqtt.MQTTMessageInfo] ] = [ 
            (topic, client.publish(topic = topic, payload = payload))
            for topic, payload in messages
        ]

        # Wait for messages to return, either with success or failure.
        for topic, message in sent:
            message.wait_for_publish(timeout = 60)

            # Log results
            result = "succeeded" if message.is_published else "failed"
            print(f"[{client.username.upper()}]: Publish to {topic} {result}. Reason code: {message.rc}.")

    #
    # Monitoring callbacks
    #
    
    @staticmethod
    def on_subscribe(client : mqtt.Client, userdata : dict[str, Any], mid, reason_code_list : list[ReasonCode], properties) -> None:
        
        # Log subscriptions results

        ## Compute number of subscription successes
        subscription_successes : int = 0

        ## Build (topic, reason_code) pairs
        ## Topics subscribed in the same order they are passed
        topics = userdata["subscribe_topics"] if isinstance(userdata["subscribe_topics"], list) else [userdata["subscribe_topics"]]
        for topic, reason_code in zip(topics,reason_code_list):

            ## Log single subscriptions results
            subscription_result = "succeeded" if not reason_code.is_failure else "failed"
            print(f"[{client.username.upper()}]: Subscription to {topic} {subscription_result}. Reason code: {reason_code}.")

            if not reason_code.is_failure:
                subscription_successes += 1

        ## Log summary
        print(f"[{client.username.upper()}]: Successfully subscribed to {subscription_successes} topics out of {len(topics)} passed.")

        print(f"[{client.username.upper()}]: Waiting for messages.")

    @staticmethod
    def on_disconnect(client : mqtt.Client, userdata : dict[str, Any], disconnect_flags, reason_code : ReasonCode, properties) -> None:

        if not reason_code == "Normal disconnection":
            print(f"[{client.username.upper()}]: Unexpected disconnection. Reason code: {reason_code}")
            return
        
        print(f"[{client.username.upper()}]: Disconnected.")
        