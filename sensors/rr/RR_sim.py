import time, json, random, os
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
PORT = 1883
SENSOR = "rr"
UNIT = "breaths/min"

PATIENTS_NUMBER = int(os.environ["PATIENTS_NUMBER"])
PATIENTS = range(1, PATIENTS_NUMBER + 1)

client = mqtt.Client()
client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

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
