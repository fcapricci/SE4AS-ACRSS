from os import getenv

from typing import Any
from collections.abc import Callable

import paho.mqtt.client as mqtt
import json
from paho.mqtt.enums import MQTTProtocolVersion
from paho.mqtt.reasoncodes import ReasonCode
from paho.mqtt.subscribeoptions import SubscribeOptions

class MQTTHandler:

    MQTT_HOSTNAME = getenv("MQTT_HOSTNAME")
    MQTT_PORT = int(getenv("MQTT_PORT"))

    @classmethod
    def get_client(cls, client_id: str, username: str | None, password: str | None, subscribe_topics):

        print(f"[{client_id.upper()}]: Initializing MQTT client...")

        client = mqtt.Client(
            client_id=client_id,   
            protocol=MQTTProtocolVersion.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )

        if username and password:
            client.username_pw_set(username, password)

        client.on_connect = cls.on_connect
        client.on_subscribe = cls.on_subscribe
        client.on_disconnect = cls.on_disconnect

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
        print(f"[{client.username.upper()}]: Connecting to MQTT broker...")

        client.connect(
            cls.MQTT_HOSTNAME,
            cls.MQTT_PORT,
            keepalive=180
        )

        client.loop_start()

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

            topics_str = topics if not isinstance(topics, list) else ", ".join(topics)
            print(f"[{client.username.upper()}]: Subscribing to {topics_str}...")

            client.subscribe(
                topic = subscriptions,
            )

    @staticmethod
    def publish(client : mqtt.Client, messages : list[ tuple[str, Any] ]) -> None:

        sent : list[ tuple[str, mqtt.MQTTMessageInfo] ] = []

        for topic, payload in messages:

            # 🔥 Serializzazione sicura
            if not isinstance(payload, (str, bytes, bytearray)):
                payload = json.dumps(payload)

            msg_info = client.publish(topic=topic, payload=payload)
            sent.append((topic, msg_info))

        for topic, message in sent:

            result = "succeeded" if message.is_published else "failed"
            


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
        