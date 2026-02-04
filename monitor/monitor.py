import os, json, time, threading
from collections import defaultdict, deque

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ---- ENV ----
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ["INFLUX_TOKEN"]
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

SOURCE = os.getenv("SOURCE", "sim")

AGG_EVERY = 5
WIN_SEC = 60

# ---- RANGES ----
RANGES = {
    "hr": (30, 220),
    "rr": (3, 60),
    "spo2": (50, 100),
    "sbp": (50, 230),
    "dbp": (30, 150),
}

# ---- STATE ----
windows = defaultdict(lambda: defaultdict(deque))

def in_range(k, v):
    lo, hi = RANGES[k]
    return lo <= v <= hi

def push(pid, k, ts_ms, v):
    dq = windows[pid][k]
    dq.append((ts_ms, v))
    cutoff = ts_ms - WIN_SEC * 1000
    while dq and dq[0][0] < cutoff:
        dq.popleft()

def mean(pid, k):
    dq = windows[pid][k]
    if not dq:
        return None
    return sum(v for _, v in dq) / len(dq)

# ---- MAIN ----
def main():
    influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    def write_raw(pid, metric, ts_ms, v):
        p = (Point("vitals_raw")
             .tag("patient_id", str(pid))
             .tag("metric", metric)
             .tag("source", SOURCE)
             .field("value", float(v))
             .time(ts_ms, WritePrecision.MS))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)

    def write_agg(pid, metric, ts_ms, m):
        p = (Point("vitals_agg")
             .tag("patient_id", str(pid))
             .tag("metric", metric)
             .tag("window", "60s")
             .tag("source", SOURCE)
             .field("mean", float(m))
             .time(ts_ms, WritePrecision.MS))
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)

    # ---- MQTT CALLBACKS ----
    def on_connect(client, userdata, flags, rc):
        print("[monitor] MQTT connected", rc)
        client.subscribe("acrss/sensors/+/+")

    def on_message(client, userdata, msg):
        try:
            obj = json.loads(msg.payload.decode())
        except Exception:
            return

        try:
            _, _, pid, sensor = msg.topic.split("/")
        except ValueError:
            return

        ts_ms = int(obj.get("ts", time.time() * 1000))

        # --- BP special case ---
        if sensor == "bp":
            for k in ("sbp", "dbp"):
                if k in obj["value"]:
                    v = float(obj["value"][k])
                    if in_range(k, v):
                        write_raw(pid, k, ts_ms, v)
                        push(pid, k, ts_ms, v)
            return

        # --- Normal sensors ---
        v = float(obj.get("value"))
        if sensor in RANGES and in_range(sensor, v):
            write_raw(pid, sensor, ts_ms, v)
            push(pid, sensor, ts_ms, v)

    # ---- AGGREGATION LOOP ----
    def agg_loop():
        while True:
            time.sleep(AGG_EVERY)
            ts_ms = int(time.time() * 1000)

            for pid in windows:
                for metric in windows[pid]:
                    m = mean(pid, metric)
                    if m is not None:
                        write_agg(pid, metric, ts_ms, m)

            print("[monitor] wrote aggregates")

    threading.Thread(target=agg_loop, daemon=True).start()

    m = mqtt.Client(client_id="monitor")
    m.on_connect = on_connect
    m.on_message = on_message
    m.connect(MQTT_BROKER, MQTT_PORT, 60)

    print("[monitor] running...")
    m.loop_forever()

if __name__ == "__main__":
    main()
