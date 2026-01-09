import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/bp"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# Baseline "paziente" (tipicamente normoteso)
BASE_SBP = random.uniform(110, 130)
BASE_DBP = random.uniform(70, 85)

# Stato corrente
sbp = BASE_SBP
dbp = BASE_DBP

# Stato episodio 
episode = "none"      # none | hypotension | shock
episode_left = 0      # secondi residui

while True:
    # 1) Drift lento + richiamo al baseline (inerzia)
    sbp += random.gauss(0, 0.6)
    dbp += random.gauss(0, 0.4)

    sbp += (BASE_SBP - sbp) * 0.05
    dbp += (BASE_DBP - dbp) * 0.05

    # 2) Avvio episodi rari (solo se non già in episodio)
    if episode == "none":
        r = random.random()
        if r < 0.0010:  # shock raro (~1 volta ogni 1000 sec in media)
            episode = "shock"
            episode_left = random.randint(20, 60)
        elif r < 0.0010 + 0.0030:  # ipotensione moderata più frequente
            episode = "hypotension"
            episode_left = random.randint(30, 90)

    # 3) Effetto episodio (sposta la pressione verso il basso per un po')
    if episode == "hypotension":
        sbp -= random.uniform(2.5, 6.0)
        dbp -= random.uniform(1.5, 4.0)
        episode_left -= 1
        if episode_left <= 0:
            episode = "none"

    elif episode == "shock":
        sbp -= random.uniform(4.0, 9.0)
        dbp -= random.uniform(2.5, 6.0)
        episode_left -= 1
        if episode_left <= 0:
            episode = "none"

    # 4) Vincoli fisiologici (permettiamo < 80 per far scattare la regola shock)
    sbp = clamp(sbp, 55, 190)
    dbp = clamp(dbp, 35, 120)

    # pulse pressure ragionevole (SBP - DBP)
    pp = sbp - dbp
    if pp < 25:
        dbp = sbp - 25
    elif pp > 70:
        dbp = sbp - 70

    # 5) Rumore di misura
    meas_sbp = int(round(sbp + random.gauss(0, 1.2)))
    meas_dbp = int(round(dbp + random.gauss(0, 1.0)))

    # MAP (utile per monitoraggio/grafana, non è una "diagnosi")
    map_mmHg = meas_dbp + (meas_sbp - meas_dbp) / 3.0

    payload = {
        "ts": int(time.time() * 1000),
        "sbp": meas_sbp,
        "dbp": meas_dbp,
        "map": round(map_mmHg, 1),
        "unit": "mmHg",
        "source": "sim"
    }

    client.publish(TOPIC, json.dumps(payload))
    print(f"[bp] → {meas_sbp}/{meas_dbp}  MAP={map_mmHg:.1f}")

    time.sleep(1)

