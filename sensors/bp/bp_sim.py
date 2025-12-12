import time
import random
import paho.mqtt.client as mqtt

BROKER = "mosquitto"
TOPIC = "acrss/sensors/bp"

client = mqtt.Client()
client.connect(BROKER, 1883, 60)
client.loop_start() 

def generate_bp():
    systolic = random.gauss(115, 12)
    astolic = random.gauss(75, 8)
    return int(systolic),int(astolic)


while True:
    systolic, astolic = generate_bp()
    client.publish(TOPIC, f'{systolic}/{astolic}')
    print(f"[bp] → {systolic}/{astolic}")
    time.sleep(1)
