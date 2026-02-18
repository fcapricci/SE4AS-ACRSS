import json
import random
import time
import os
from handlers.mqtt_handler import MQTTHandler

SENSORS_TOPICS_PREFIX =  os.getenv("SENSORS_TOPICS_PREFIX")

username = os.getenv("MQTT_USER")
password = os.getenv("MQTT_PASSWORD")


class Patient:

    def __init__(self, patient_id):
        self.patient_id = patient_id

        subscribe_topics = None
        self.client = MQTTHandler.get_client(
            client_id=f"{patient_id}",
            username=username,
            password=password,
            subscribe_topics=subscribe_topics
        )
        MQTTHandler.connect(self.client, blocking=False)

        # Stato fisiologico base
        self.hr = 80.0
        self.spo2 = 97.0
        self.rr = 16.0
        self.sbp = 120.0
        self.dbp = 80.0

        # Effetti attuatori 
        self.oxygen_flow = 0.0
        self.beta_blocker_rate = 0.0
        self.fluids_rate = 0.0

    def step(self):
        """Evoluzione fisiologica ogni secondo"""

        # Dinamica naturale
        self.hr += random.gauss(0, 0.3)
        self.spo2 += random.gauss(0, 0.05)

        # Effetto ossigeno
        self.spo2 += 0.2 * self.oxygen_flow
        self.rr -= 0.05 * self.oxygen_flow

        # Effetto beta bloccante
        self.hr -= 0.4 * self.beta_blocker_rate
        self.sbp -= 0.2 * self.beta_blocker_rate

        # Effetto fluidi
        self.sbp += 0.3 * self.fluids_rate
        self.dbp += 0.2 * self.fluids_rate

        # Clamp fisiologico
        self.hr = max(30, min(160, self.hr))
        self.spo2 = max(75, min(100, self.spo2))
        self.rr = max(4, min(40, self.rr))
        self.sbp = max(60, min(200, self.sbp))
        self.dbp = max(40, min(120, self.dbp))

    def on_message(self, client, userdata, msg):

        now = int(time.time() * 1000)
        base_topic  = f"{SENSORS_TOPICS_PREFIX}/{self.patient_id}"
        # HR
        hr_payload = {
            "ts": now,
            "value": int(round(self.hr)),
            "unit": "bpm",
            "source": "sim"
        }


        MQTTHandler.publish(
            client,
            [(f"{base_topic}/hr", json.dumps(hr_payload))]
        )

        # RR
        rr_payload = {
            "ts": now,
            "value": int(round(self.rr)),
            "unit": "breaths/min",
            "source": "sim"
        }

        MQTTHandler.publish(
            client,
            [(f"{base_topic}/rr", json.dumps(rr_payload))]
        )

        # SPO2
        spo2_payload = {
            "ts": now,
            "value": int(round(self.spo2)),
            "unit": "%",
            "source": "sim"
        }

        MQTTHandler.publish(
            client,
            [(f"{base_topic}/spo2", json.dumps(spo2_payload))]
        )
        # BP
        bp_payload = {
            "ts": now,
            "value": {
                "sbp": int(round(self.sbp)),
                "dbp": int(round(self.dbp))
            },
            "unit": "mmHg",
            "source": "sim"
        }
        MQTTHandler.publish(
            client,
            [(f"{base_topic}/bp", json.dumps(bp_payload))]
        )
