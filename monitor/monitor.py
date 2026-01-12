import os, json, time
from collections import deque

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

PATIENT_ID = os.getenv("PATIENT_ID", "p1")
SOURCE = os.getenv("SOURCE", "sim")

AGG_EVERY = 5   # seconds
WIN_SEC = 60    # 60s window

RANGES = {
    "hr": (30, 220),
    "rr": (3, 60),
    "spo2": (50, 100),
    "sbp": (50, 230),
    "dbp": (30, 150),
    "map": (30, 170),
}

metrics = ["hr", "rr", "spo2", "sbp", "dbp", "map"]
windows = {k: deque() for k in metrics}

def in_range(k, v):
    lo, hi = RANGES[k]
    return lo <= v <= hi

def push(k, ts_ms, v):
    dq = windows[k]
    dq.append((ts_ms, v))
    cutoff = ts_ms - WIN_SEC * 1000
    while dq and dq[0][0] < cutoff:
        dq.popleft()

def mean(k):
    dq = windows[k]
    if not dq:
        return None
    return sum(v for _, v in dq) / len(dq)

def main():
    influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    def write_raw(k, ts_ms, v):
        p = (Point("vitals_raw")
             .tag("patient_id", PATIENT_ID)
             .tag("source", SOURCE)
             .tag("metric", k)
             .field("value", float(v))
             .time(ts_ms, WritePrecision.MS))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
    def write_agg(k, ts_ms, m):
        p = (Point("vitals_agg")
             .tag("patient_id", PATIENT_ID)
             .tag("source", SOURCE)
             .tag("metric", k)
             .tag("window", "60s")
             .field("mean", float(m))
             .time(ts_ms, WritePrecision.MS))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)

    def on_connect(client, userdata, flags, rc):
        print("[monitor] MQTT connected", rc)
        client.subscribe("acrss/sensors/#")

    def on_message(client, userdata, msg):
        try:
            obj = json.loads(msg.payload.decode())
        except Exception:
            return

        ts_ms = int(obj.get("ts", time.time() * 1000))

        for k in metrics:
            if k in obj:
                v = float(obj[k])
                if in_range(k, v):
                    write_raw(k, ts_ms, v)
                    push(k, ts_ms, v)

    def agg_loop():
        while True:
            time.sleep(AGG_EVERY)
            ts_ms = int(time.time() * 1000)
            for k in metrics:
                m = mean(k)
                if m is not None:
                    write_agg(k, ts_ms, m)
            print("[monitor] wrote mean(60s)")

    import threading
    threading.Thread(target=agg_loop, daemon=True).start()

    m = mqtt.Client(client_id="monitor")
    m.on_connect = on_connect
    m.on_message = on_message
    m.connect(MQTT_BROKER, MQTT_PORT, 60)
    print("[monitor] running...")
    m.loop_forever()

if __name__ == "__main__":
    main()
