import json
import threading
from collections import defaultdict
import os
import pandas as pd
import paho.mqtt.client as mqtt


class MQTTHandler:
    def __init__(self, broker, port=1883):
        self.broker = broker
        self.port = port

        # buffer: patient_id -> latest values
        self.patient_data = defaultdict(dict)
        self.lock = threading.Lock()

        mqtt_user = os.getenv("MQTT_USER")
        mqtt_password = os.getenv("MQTT_PASSWORD")

        self.client = mqtt.Client()
        if mqtt_user and mqtt_password:
            self.client.username_pw_set(mqtt_user, mqtt_password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(self.broker, self.port, 60)

    # ---------------- MQTT CALLBACKS ---------------- #

    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected with result code", rc)
        client.subscribe("acrss/states/+/+")

    def on_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split("/")
            patient_id = topic_parts[2]
            sensor_type = topic_parts[3]

            payload = json.loads(msg.payload.decode())

            with self.lock:
                ts = payload.get("ts")

                if sensor_type == "bp":
                    sbp = payload["value"].get("sbp")
                    dbp = payload["value"].get("dbp")

                    if sbp is not None and dbp is not None:
                        self.patient_data[patient_id]["sbp"] = sbp
                        self.patient_data[patient_id]["dbp"] = dbp
                        self.patient_data[patient_id]["map"] = (
                            sbp + 2 * dbp
                        ) / 3

                else:
                    self.patient_data[patient_id][sensor_type] = payload.get(
                        "value"
                    )

                self.patient_data[patient_id]["time"] = ts

        except Exception as e:
            print("MQTT parse error:", e)

    # ---------------- PUBLIC API ---------------- #

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
    
    def publish(self, topic: str, payload: dict):
        """
        Publish JSON payload to MQTT.
        """
        try:
            self.client.publish(
                topic,
                json.dumps(payload)
            )
        except Exception as e:
            print("MQTT publish error:", e)


    def get_patient_dataframe(self, patient_id):
        """
        Returns a pandas DataFrame with the exact format
        expected by the Analyzer.
        """
        with self.lock:
            data = self.patient_data.get(patient_id)

            if not data:
                return None

            df = pd.DataFrame([{
                "time": data.get("time"),
                "hr": data.get("hr"),
                "rr": data.get("rr"),
                "spo2": data.get("spo2"),
                "sbp": data.get("sbp"),
                "dbp": data.get("dbp"),
                "map": data.get("map"),
            }])

        df["time"] = pd.to_datetime(df["time"], unit="ms")
        return df
