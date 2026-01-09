import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/rr"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# Baseline paziente (RR a riposo ~12–18)
BASE_RR = random.uniform(12, 18)

# Target dinamico e stato corrente
target_rr = BASE_RR
rr = BASE_RR

while True:
    # 1) Cambiamenti rari del target
    r = random.random()
    if r < 0.0025:          # tachipnea (utile per regole tipo RR > 30)
        target_rr = random.uniform(28, 40)
    elif r < 0.0025 + 0.0010:  # bradipnea (rara)
        target_rr = random.uniform(6, 10)
    elif r < 0.0025 + 0.0010 + 0.015:  # ritorno verso normalità
        target_rr = BASE_RR

    # 2) RR si muove lentamente verso il target + rumore lieve
    rr += (target_rr - rr) * 0.12 + random.gauss(0, 0.6)

    # 3) Vincoli fisiologici
    rr = clamp(rr, 4, 60)

    meas_rr = int(round(rr + random.gauss(0, 0.4)))

    payload = {
        "ts": int(time.time() * 1000),
        "rr": meas_rr,
        "unit": "breaths/min",
        "source": "sim"
    }

    client.publish(TOPIC, json.dumps(payload))
    print(f"[RR] → {meas_rr}", flush=True)

    time.sleep(1)
