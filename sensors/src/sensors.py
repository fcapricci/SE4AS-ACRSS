import time
import json
import random
import os
import threading
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
PORT = 1883

PATIENTS_NUMBER = int(os.environ["PATIENTS_NUMBER"])
PATIENTS = range(1, PATIENTS_NUMBER + 1)

MQTT_USER = os.environ["MQTT_USER"]
MQTT_PASSWORD = os.environ["MQTT_PASSWORD"]

client = mqtt.Client(
    client_id="sensor_all",
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# =============================
# BP SENSOR (IDENTICO)
# =============================

def bp_loop():
    SENSOR = "bp"
    UNIT = "mmHg"

    state = {}
    for pid in PATIENTS:
        sbp = random.uniform(110, 130)
        dbp = random.uniform(70, 85)
        state[pid] = {
            "base_sbp": sbp,
            "base_dbp": dbp,
            "sbp": sbp,
            "dbp": dbp,
            "episode": "none",
            "left": 0
        }

    while True:
        now = int(time.time() * 1000)

        for pid, s in state.items():
            s["sbp"] += random.gauss(0, 0.6)
            s["dbp"] += random.gauss(0, 0.4)

            s["sbp"] += (s["base_sbp"] - s["sbp"]) * 0.05
            s["dbp"] += (s["base_dbp"] - s["dbp"]) * 0.05

            if s["episode"] == "none":
                r = random.random()
                if r < 0.001:
                    s["episode"] = "shock"
                    s["left"] = random.randint(20, 60)
                elif r < 0.004:
                    s["episode"] = "hypotension"
                    s["left"] = random.randint(30, 90)

            if s["episode"] == "hypotension":
                s["sbp"] -= random.uniform(2.5, 6)
                s["dbp"] -= random.uniform(1.5, 4)
                s["left"] -= 1
                if s["left"] <= 0:
                    s["episode"] = "none"

            if s["episode"] == "shock":
                s["sbp"] -= random.uniform(4, 9)
                s["dbp"] -= random.uniform(2.5, 6)
                s["left"] -= 1
                if s["left"] <= 0:
                    s["episode"] = "none"

            s["sbp"] = clamp(s["sbp"], 55, 190)
            s["dbp"] = clamp(s["dbp"], 35, 120)

            payload = {
                "ts": now,
                "value": {
                    "sbp": int(round(s["sbp"])),
                    "dbp": int(round(s["dbp"]))
                },
                "unit": UNIT,
                "source": "sim"
            }

            client.publish(f"acrss/sensors/{pid}/{SENSOR}", json.dumps(payload))

        time.sleep(1)

# =============================
# HR SENSOR (COPIA IDENTICA DEL TUO)
# RR SENSOR
# SPO2 SENSOR
# (Li incolliamo esattamente come sono,
#  solo racchiusi in funzioni hr_loop(), rr_loop(), spo2_loop())
# =============================

def hr_loop():

    SENSOR = "hr"
    UNIT = "bpm"

    state = {}
    for pid in PATIENTS:
        base = random.uniform(65, 85)
        state[pid] = {
            "base": base,
            "target": base,
            "value": base
        }

    while True:
        now = int(time.time() * 1000)

        for pid, s in state.items():
            r = random.random()
            if r < 0.002:
                s["target"] = random.uniform(105, 130)
            elif r < 0.003:
                s["target"] = random.uniform(45, 55)
            elif r < 0.015:
                s["target"] = s["base"]

            s["value"] += (s["target"] - s["value"]) * 0.1 + random.gauss(0, 1.2)
            s["value"] = clamp(s["value"], 40, 160)

            payload = {
                "ts": now,
                "value": int(round(s["value"])),
                "unit": UNIT,
                "source": "sim"
            }

            topic = f"acrss/sensors/{pid}/{SENSOR}"
            client.publish(topic, json.dumps(payload))

        time.sleep(1)

def rr_loop():
    SENSOR = "rr"
    UNIT = "breaths/min"

    state = {}
    for pid in PATIENTS:
        base = random.uniform(12, 18)
        state[pid] = {"base": base, "target": base, "value": base}

    while True:
        now = int(time.time() * 1000)

        for pid, s in state.items():
            r = random.random()
            if r < 0.0025:
                s["target"] = random.uniform(28, 40)
            elif r < 0.0035:
                s["target"] = random.uniform(6, 10)
            elif r < 0.02:
                s["target"] = s["base"]

            s["value"] += (s["target"] - s["value"]) * 0.12 + random.gauss(0, 0.6)
            s["value"] = clamp(s["value"], 4, 60)

            payload = {
                "ts": now,
                "value": int(round(s["value"])),
                "unit": UNIT,
                "source": "sim"
            }

            client.publish(f"acrss/sensors/{pid}/{SENSOR}", json.dumps(payload))

        time.sleep(1)


def spo2_loop():
    SENSOR = "spo2"
    UNIT = "%"

    state = {}
    for pid in PATIENTS:
        base = random.uniform(96, 99)
        state[pid] = {"base": base, "target": base, "value": base}

    while True:
        now = int(time.time() * 1000)

        for pid, s in state.items():
            r = random.random()
            if r < 0.002:
                s["target"] = random.uniform(82, 88)
            elif r < 0.006:
                s["target"] = random.uniform(88, 92)
            elif r < 0.02:
                s["target"] = s["base"]

            s["value"] += (s["target"] - s["value"]) * 0.15 + random.gauss(0, 0.3)
            s["value"] = clamp(s["value"], 75, 100)

            payload = {
                "ts": now,
                "value": int(round(s["value"])),
                "unit": UNIT,
                "source": "sim"
            }

            client.publish(f"acrss/sensors/{pid}/{SENSOR}", json.dumps(payload))

        time.sleep(1)



# =============================
# START THREADS
# =============================

threads = [
    threading.Thread(target=bp_loop),
    threading.Thread(target=hr_loop),
    threading.Thread(target=rr_loop),
    threading.Thread(target=spo2_loop)
]

for t in threads:
    t.start()

for t in threads:
    t.join()
