import time, json, random
import paho.mqtt.client as mqtt
from pathlib import Path

BROKER = "mosquitto"
PORT = 1883
SENSOR = "spo2"
UNIT = "%"

patients = json.loads(Path("patients.json").read_text())["patients"]

client = mqtt.Client()
client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

state = {}
for pid in patients:
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
