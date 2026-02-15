import time, json, random, os
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
PORT = 1883
SENSOR = "bp"
UNIT = "mmHg"

PATIENTS_NUMBER = int(os.environ["PATIENTS_NUMBER"])
PATIENTS = range(1, PATIENTS_NUMBER + 1)

MQTT_USER = os.environ["MQTT_USER"]
MQTT_PASSWORD = os.environ["MQTT_PASSWORD"]

client = mqtt.Client(
    client_id="sensor_bp",
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

client.connect(BROKER, PORT, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

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
