import time, json, random
import paho.mqtt.client as mqtt
from pathlib import Path

BROKER = "mosquitto"
PORT = 1883
SENSOR = "hr"
UNIT = "bpm"

# ---- load patients ----
patients = json.loads(Path("patients.json").read_text())["patients"]

# ---- mqtt ----
client = mqtt.Client()
client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# ---- per-patient state ----
state = {}
for pid in patients:
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
            s["target"] = random.uniform(105, 130)  # tachy
        elif r < 0.003:
            s["target"] = random.uniform(45, 55)    # brady
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
