import time
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/hr"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start()

def generate_hr():
    """
    HR normale: 60–100 bpm
    Oscillazioni fisiologiche leggere
    """
    base = random.gauss(80, 5)
    return max(40, min(160, int(base)))

while True:
    hr = generate_hr()
    client.publish(TOPIC, hr)
    print(f"[HR] → {hr}", flush=True)
    time.sleep(1)
