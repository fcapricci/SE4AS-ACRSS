from handlers.mqtt_handler import MQTTHandler
from planner_manager import PlannerManager
import json
import time
import os

SYMPTOMS_TOPICS_PREFIX = os.getenv("SYMPTOMS_TOPICS_PREFIX")
THERAPIES_TOPICS_PREFIX = os.getenv("THERAPIES_TOPICS_PREFIX")
MQTT_USERNAME = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")


def on_message(client, userdata, message):
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode())

        patient_id = topic.split("/")[-1]

        therapy = PlannerManager.process_symptoms(patient_id, payload)

        topic_out = f"{THERAPIES_TOPICS_PREFIX}/{patient_id}"

        MQTTHandler.publish(
            client,
            [(topic_out, therapy)]
        )

        print(f"[PLANNER] Therapy published for patient {patient_id}")

    except Exception as e:
        print("Planner error:", e)


def main():
    mqtt_client = MQTTHandler.get_client(
        client_id="planner",
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        subscribe_topics=f"{SYMPTOMS_TOPICS_PREFIX}/+"
    )

    MQTTHandler.set_on_message(mqtt_client, on_message)
    MQTTHandler.connect(mqtt_client, blocking=False)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
