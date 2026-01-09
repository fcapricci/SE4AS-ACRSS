import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/spo2"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# Baseline fisiologica
BASE_SPO2 = random.uniform(96, 99)

# Target dinamico e stato corrente
target_spo2 = BASE_SPO2
spo2 = BASE_SPO2

while True:
    # 1) Cambiamenti rari del target
    r = random.random()
    if r < 0.002:           # ipossia moderata/severa
        target_spo2 = random.uniform(82, 88)
    elif r < 0.002 + 0.004:  # ipossia lieve
        target_spo2 = random.uniform(88, 92)
    elif r < 0.002 + 0.004 + 0.02:  # ritorno verso normalità
        target_spo2 = BASE_SPO2

    # 2) SpO2 si muove lentamente verso il target
    spo2 += (target_spo2 - spo2) * 0.15 + random.gauss(0, 0.3)

    # 3) Vincoli fisiologici
    spo2 = clamp(spo2, 75, 100)

    meas_spo2 = int(round(spo2 + random.gauss(0, 0.5)))

    payload = {
        "ts": int(time.time() * 1000),
        "spo2": meas_spo2,
        "unit": "%",
        "source": "sim"
    }

    client.publish(TOPIC, json.dumps(payload))
    print(f"[SpO2] → {meas_spo2}", flush=True)

    time.sleep(1)
