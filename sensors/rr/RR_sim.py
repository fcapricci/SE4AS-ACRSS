import time
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/rr"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start() 

def generate_RR():
    # Valore normale con rare oscillazioni
    base = random.gauss(16, 2)
    return base

while True:
    rr = generate_RR()
    client.publish(TOPIC, int(rr))
    print(f"[RR] → {int(rr)}")
    time.sleep(1)
