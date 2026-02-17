import os
import paho.mqtt.client as mqtt

ACTIONS_TOPICS_PREFIX = os.getenv("ACTIONS_TOPICS_PREFIX")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

class OxygenFlowRegulator:

    def __init__(self, patient):
        self.patient = patient

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            reconnect_on_failure=True
        )

        if MQTT_USER and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect("mosquitto", 1883)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties=None):

        if rc == 0:
            topic = f"{ACTIONS_TOPICS_PREFIX}/{self.patient.patient_id}/oxygen_flow_regulator"
            client.subscribe(topic)
            print(f"[OXYGEN-{self.patient.patient_id}] Subscribed to {topic}")
        else:
            print(f"MQTT connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            flow = float(msg.payload.decode())
            self.patient.oxygen_flow = flow
            print(f"[OXYGEN-{self.patient.patient_id}] Flow set to {flow}")
        except ValueError:
            print("Invalid oxygen flow payload")
