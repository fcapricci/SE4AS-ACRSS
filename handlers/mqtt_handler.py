from os import getenv

import json

from typing import Any
from collections.abc import Callable

import paho.mqtt.client as mqtt
from paho.mqtt.enums import MQTTProtocolVersion
from paho.mqtt.subscribeoptions import SubscribeOptions
from paho.mqtt.reasoncodes import ReasonCode

class MQTTHandler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = int(getenv("MQTT_PORT"))

    MQTT_CLIENT_KEEPALIVE = int(getenv("MQTT_CLIENT_KEEPALIVE"))

    @classmethod
    def get_client(cls, client_id: str, username: str | None, password: str | None, subscribe_topics : str | list[str] | None) -> mqtt.Client:

        # Initialize instance
        print(f"[{client_id.upper()}]: Initializing MQTT client...")

        ## Set MQTTProtocolVersion.MQTTv5 for reason codes and authentication support.
        ## Set CallbackAPIVersion.VERSION2 as VERSION1 deprecated.
        client = mqtt.Client(
            client_id = client_id,   
            protocol = MQTTProtocolVersion.MQTTv5,
            callback_api_version = mqtt.CallbackAPIVersion.VERSION2
        )

        # Setup

        ## Set username and password
        if username and password:
            client.username_pw_set(username, password)

        ## Set callbacks
        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_disconnect = cls.on_disconnect

        ## Set subscribe topics
        client.user_data_set({
            "subscribe_topics": subscribe_topics
        })

        print(f"[{client_id.upper()}]: MQTT client initialization succeeded.")

        return client

    @staticmethod
    def set_on_message(
        client : mqtt.Client,
        on_message_callback : Callable[[mqtt.Client, dict[str, Any], mqtt.MQTTMessage], None]) -> None:
        client.on_message = on_message_callback

    @classmethod
    def connect(cls, client : mqtt.Client, blocking : bool) -> None:

        # Connect client with broker
        print(f"[{client._client_id.upper()}]: Connecting to MQTT broker...")
        client.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT,
            cls.MQTT_CLIENT_KEEPALIVE
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
        print(f"[{client._client_id.upper()}]: Connection to MQTT broker {connection_result}. Reason code: {reason_code}.")

        # Subscribe on connection succeeded to handle reconnection scenarios
        if connection_result == "succeeded" and userdata["subscribe_topics"] is not None:

            # Build subscriptions: (topic, QoS)
            # Handle multiple topics scenario
            topics = userdata["subscribe_topics"]
            subscriptions = (topics, SubscribeOptions(qos=2)) if not isinstance(topics, list) else [(topic, SubscribeOptions(qos=2)) for topic in topics]

            topics_str = topics if not isinstance(topics, list) else ", ".join(topics)
            print(f"[{client._client_id.upper()}]: Subscribing to {topics_str}...")

            client.subscribe(
                topic = subscriptions
            )

    @staticmethod
    def publish(client : mqtt.Client, messages : tuple[str, Any] | list[tuple[str, Any]]) -> None:

        # Handle single message scenario
        if not isinstance(messages, list):
            messages = [messages]

        sent : list[ tuple[str, mqtt.MQTTMessageInfo] ] = []

        for topic, payload in messages:

            # Serialize payload
            payload = json.dumps(payload)

            # Publish
            msg_info = client.publish(
                topic = topic,
                payload = payload
            )
            sent.append((topic, msg_info))

        # Wait for messages to be published
        for topic, message in sent:
            message.wait_for_publish()

            # Log results
            result = "succeeded" if message.is_published else "failed"
            print(f"[{client._client_id.upper()}]: Publish to {topic} {result}. Reason code: {message.rc}")
        


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
            print(f"[{client._client_id.upper()}]: Subscription to {topic} {subscription_result}. Reason code: {reason_code}.")

            if not reason_code.is_failure:
                subscription_successes += 1

        ## Log summary
        print(f"[{client._client_id.upper()}]: Successfully subscribed to {subscription_successes} topics out of {len(topics)} passed.")

        print(f"[{client._client_id.upper()}]: Waiting for messages.")

    @staticmethod
    def on_disconnect(client : mqtt.Client, userdata : dict[str, Any], disconnect_flags, reason_code : ReasonCode, properties) -> None:

        if not reason_code == "Normal disconnection":
            print(f"[{client._client_id.upper()}]: Unexpected disconnection. Reason code: {reason_code}")
            return
        
        print(f"[{client._client_id.upper()}]: Disconnected.")
        