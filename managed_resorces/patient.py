import json
import random
import time

class Patient:

    def __init__(self, patient_id):
        self.patient_id = patient_id

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

    def publish_sensors(self, client):

        now = int(time.time() * 1000)

        # HR
        hr_payload = {
            "ts": now,
            "value": int(round(self.hr)),
            "unit": "bpm",
            "source": "sim"
        }

        client.publish(
            f"acrss/sensors/{self.patient_id}/hr",
            json.dumps(hr_payload)
        )

        # RR
        rr_payload = {
            "ts": now,
            "value": int(round(self.rr)),
            "unit": "breaths/min",
            "source": "sim"
        }

        client.publish(
            f"acrss/sensors/{self.patient_id}/rr",
            json.dumps(rr_payload)
        )

        # SPO2
        spo2_payload = {
            "ts": now,
            "value": int(round(self.spo2)),
            "unit": "%",
            "source": "sim"
        }

        client.publish(
            f"acrss/sensors/{self.patient_id}/spo2",
            json.dumps(spo2_payload)
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

        client.publish(
            f"acrss/sensors/{self.patient_id}/bp",
            json.dumps(bp_payload)
        )
