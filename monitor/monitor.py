import os
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

IN_PREFIX  = "acrss/sensors"
OUT_PREFIX = "acrss/states"

def on_connect(client, userdata, flags, rc):
    print("[monitor] connected", rc)
    client.subscribe(f"{IN_PREFIX}/+/+")

def on_message(client, userdata, msg):
    try:
        # acrss/sensors/{patient_id}/{sensor}
        _, _, patient_id, sensor = msg.topic.split("/")
    except ValueError:
        return

    out_topic = f"{OUT_PREFIX}/{patient_id}/{sensor}"

    # ripubblica IDENTICO payload
    client.publish(out_topic, msg.payload)

def main():
    client = mqtt.Client(client_id="monitor")

    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    print("[monitor] running (MQTT → MQTT bridge)")
    client.loop_forever()

if __name__ == "__main__":
    main()
