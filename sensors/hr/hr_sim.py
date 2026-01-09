import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/hr"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# Baseline "paziente"
BASE_HR = random.uniform(65, 85)

# Target dinamico e stato corrente
target_hr = BASE_HR
hr = BASE_HR

while True:
    # 1) Rari cambiamenti fisiologici del target
    r = random.random()
    if r < 0.002:        # tachicardia
        target_hr = random.uniform(105, 130)
    elif r < 0.002 + 0.001:  # bradicardia
        target_hr = random.uniform(45, 55)
    elif r < 0.002 + 0.001 + 0.01:  # ritorno verso normalità
        target_hr = BASE_HR

    # 2) L'HR si muove lentamente verso il target
    hr += (target_hr - hr) * 0.1 + random.gauss(0, 1.2)

    # 3) Vincoli fisiologici
    hr = clamp(hr, 40, 160)

    meas_hr = int(round(hr + random.gauss(0, 1.0)))

    payload = {
        "ts": int(time.time() * 1000),
        "hr": meas_hr,
        "unit": "bpm",
        "source": "sim"
    }

    client.publish(TOPIC, json.dumps(payload))
    print(f"[HR] → {meas_hr}", flush=True)

    time.sleep(1)
