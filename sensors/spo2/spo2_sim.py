import time, json, random, os
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
PORT = 1883
SENSOR = "spo2"
UNIT = "%"

PATIENTS_NUMBER = int(os.environ["PATIENTS_NUMBER"])
PATIENTS = range(1, PATIENTS_NUMBER + 1)

MQTT_USER = os.environ["MQTT_USER"]
MQTT_PASSWORD = os.environ["MQTT_PASSWORD"]

client = mqtt.Client(
    client_id="sensor_spo2",
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

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
