import paho.mqtt.client as mqtt

def create_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect("mosquitto", 1883)
    client.loop_start()
    return client
