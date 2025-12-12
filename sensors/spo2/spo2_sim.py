import time
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/spo2"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start() 

def generate_spo2():
    # Valore normale con rare oscillazioni
    base = random.gauss(97, 1)
    return max(80, min(100, int(base)))

while True:
    spo2 = generate_spo2()
    client.publish(TOPIC, spo2)
    print(f"[SpO2] → {spo2}")
    time.sleep(1)
