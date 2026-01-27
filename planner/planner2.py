# FULL PLANNER FILE - EVENT DRIVEN, DATACLASS, DECISION/ARBITRATION ARCHITECTURE
# READY TO RUN

import os
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List
import signal
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================
# ENV CONFIG
# ==========================

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PATIENT_ID = os.getenv("PATIENT_ID", "p1")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

# ==========================
# DATA MODEL
# ==========================

@dataclass
class TherapyState:
    ox_therapy: int = 0
    fluids: Optional[str] = None
    carvedilolo_beta_blocking: float = 0.0
    improve_beta_blocking: float = 0.0
    alert: List[str] = field(default_factory=list)
    timestamp: Optional[str] = None

    def snapshot(self):
        return (
            self.ox_therapy,
            self.fluids,
            self.carvedilolo_beta_blocking,
            self.improve_beta_blocking,
        )

    def clone(self):
        return TherapyState(**asdict(self))

# ==========================
# DECISION ENGINE
# ==========================

class DecisionEngine:
    def __init__(self, planner):
        self.p = planner

    def ox_therapy(self, patient_state, therapy: TherapyState):
        status = patient_state['status']
        trend = patient_state['trend']
        intensity = patient_state['intensity']

        pattern_decrease = "_DECREASE"
        pattern_stable = "STABLE_"
        ox_increased = False

        if status['oxigenation'] == "LIGHT_HYPOXIA" and therapy.ox_therapy < self.p.MAX_NON_INVASIVE_OX_THERAPY:
            if trend['spo2'] == 'IMPROVING':
                therapy.ox_therapy += 1
                ox_increased = True
            elif trend['spo2'] == 'STABLE' and pattern_decrease in intensity['spo2']:
                therapy.ox_therapy += 2
                ox_increased = True
            elif trend['spo2'] == 'DETERIORING':
                therapy.ox_therapy += 2
                ox_increased = True

        elif status['oxigenation'] == "GRAVE_HYPOXIA":
            therapy.ox_therapy = self.p.MAX_NON_INVASIVE_OX_THERAPY

        elif status['oxigenation'] == "FAILURE_OXYGEN_THERAPY":
            therapy.alert.append("FAILURE_OXYGEN_THERAPY")

        elif pattern_stable in status['oxigenation'] and trend['spo2'] != 'DETERIORING':
            therapy.ox_therapy = max(0, therapy.ox_therapy - 1)

        if status['respiration'] == 'MODERATE_TACHYPNEA' and not ox_increased:
            if trend['rr'] == 'STABLE':
                therapy.ox_therapy += 1
            elif trend['rr'] == 'DETERIORING' and pattern_decrease in intensity['rr']:
                therapy.ox_therapy += 2

        elif status['respiration'] in ['RESPIRATORY_DISTRESS', 'BRADYPNEA']:
            therapy.alert.append(status['respiration'])

# ==========================
# ARBITRATOR
# ==========================

class Arbitrator:
    def apply(self, patient_state, therapy: TherapyState):
        status = patient_state['status']

        if status['respiration'] == 'RESPIRATORY_DISTRESS':
            therapy.fluids = None

        if status['oxigenation'] == 'FAILURE_OXYGEN_THERAPY':
            therapy.fluids = None

        if status['blood_pressure'] == 'DISTRESS_OVERLOAD':
            therapy.fluids = None

        if status['blood_pressure'] == 'SHOCK':
            therapy.carvedilolo_beta_blocking = 0
            therapy.improve_beta_blocking = 0

        if status['respiration'] == 'BRADYPNEA':
            therapy.carvedilolo_beta_blocking = 0
            therapy.improve_beta_blocking = 0

# ==========================
# PLANNER
# ==========================

class Planner:
    def __init__(self):
        self.therapy = TherapyState()
        self.last_sent_state: Optional[TherapyState] = None

        self.dt_incr = 80640
        self.MAX_NON_INVASIVE_OX_THERAPY = 6
        self.STARTING_BB_DOSE = 1.25
        self.INCR_BB_DOSE = 0.25
        self.beta_blocking_target_dose = 10
        self.last_bb_incr = None

        self.decision = DecisionEngine(self)
        self.arbitrator = Arbitrator()

    def calculate_dt(self):
        if self.last_bb_incr is None:
            return True
        return int(datetime.now().timestamp()) - self.last_bb_incr > self.dt_incr

    def pharmacy_therapy(self, patient_state):
        status = patient_state['status']
        trend = patient_state['trend']

        if status['heart_rate'] == 'PRIMARY_TACHYCARDIA':
            if trend['hr'] == 'STABLE' and self.therapy.carvedilolo_beta_blocking == 0:
                self.therapy.carvedilolo_beta_blocking = self.STARTING_BB_DOSE
                self.last_bb_incr = int(datetime.now().timestamp())

            elif trend['hr'] == 'DETERIORING' and self.calculate_dt():
                if (self.therapy.carvedilolo_beta_blocking + self.therapy.improve_beta_blocking) < self.beta_blocking_target_dose:
                    self.therapy.improve_beta_blocking += self.INCR_BB_DOSE
                    self.last_bb_incr = int(datetime.now().timestamp())

        if status['blood_pressure'] == 'MODERATE_HYPOTENSION':
            if trend['map'] in ['STABLE', 'DETERIORING']:
                self.therapy.fluids = 'BOLUS'
                if trend['map'] == 'DETERIORING':
                    self.therapy.alert.append("MODERATE_HYPOTENSION")

        if status['blood_pressure'] == 'SHOCK':
            self.therapy.alert.append("SHOCK")

    def step(self, patient_state):
        self.pharmacy_therapy(patient_state)
        self.decision.ox_therapy(patient_state, self.therapy)
        self.arbitrator.apply(patient_state, self.therapy)

    def has_changed(self):
        if self.last_sent_state is None:
            return True
        return self.last_sent_state.snapshot() != self.therapy.snapshot()

    def commit(self):
        self.last_sent_state = self.therapy.clone()
        self.therapy.alert.clear()

# ==========================
# MQTT / INFLUX
# ==========================

planner = Planner()
mqtt_client = None
influx_client = None


def send_status(client, therapy: TherapyState):
    therapy.timestamp = datetime.now().isoformat()
    payload = json.dumps(asdict(therapy), default=str)
    topic = f"acrss/plan/{PATIENT_ID}"
    client.publish(topic, payload=payload, qos=1)
    print("[PLANNER] Terapia pubblicata:")
    print(payload)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[PLANNER] MQTT connected")
        client.subscribe("acrss/analyzer/#")
    else:
        print("[PLANNER] MQTT connection error", rc)


def on_message(client, userdata, msg):
    global planner

    obj = json.loads(msg.payload.decode())
    planner.step(obj)

    if planner.has_changed():
        send_status(client, planner.therapy)
        planner.commit()


def cleanup():
    global mqtt_client, influx_client

    print("[PLANNER] Shutdown...")
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if influx_client:
        influx_client.close()


def signal_handler(sig, frame):
    cleanup()
    exit(0)

# ==========================
# MAIN
# ==========================

def main():
    global mqtt_client, influx_client

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # InfluxDB
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    influx_client.write_api(write_options=SYNCHRONOUS)
    print("[PLANNER] InfluxDB connected")

    # MQTT
    mqtt_client = mqtt.Client(client_id=f"planner_{PATIENT_ID}", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
