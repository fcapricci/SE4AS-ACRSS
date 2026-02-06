from influxdb_client import InfluxDBClient
import pandas as pd
from influxdb_client.client.write_api import SYNCHRONOUS
import os

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]

try:
    influx_client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    query_api = influx_client.query_api()
except Exception as e:
    print(f"Connection error {e}")
    influx_client = None


def read_data(
    patient_id: str,
    measurement: str = "vitals_state",
    minutes: int = 5,
    limit: int = 5000,
    full_history: bool = False
) -> pd.DataFrame:
    """
    Adapter layer:
    - legge da Influx
    - normalizza i dati
    - ADATTA il formato a quello richiesto dall'Analyzer
    """

    if full_history:
        range_clause = '|> range(start: 0)'
    else:
        range_clause = f'|> range(start: -{minutes}m)'

    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      {range_clause}
      |> filter(fn: (r) => r._measurement == "{measurement}")
      |> filter(fn: (r) => r.patient_id == "{patient_id}")
      |> sort(columns: ["_time"], desc: false)
      |> limit(n: {limit})
    '''

    try:
        tables = query_api.query(query)
        if not tables:
            return pd.DataFrame()

        records = []
        for table in tables:
            for r in table.records:
                records.append({
                    "time": r.get_time(),
                    "sensor": r.values.get("sensor"),
                    "field": r.get_field(),
                    "value": r.get_value()
                })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        base = df[df["field"] == "value"].pivot_table(
            index="time",
            columns="sensor",
            values="value",
            aggfunc="last"
        )

        sbp = df[df["field"] == "value_sbp"].pivot_table(
            index="time",
            values="value",
            aggfunc="last"
        ).rename(columns={"value": "sbp"})

        dbp = df[df["field"] == "value_dbp"].pivot_table(
            index="time",
            values="value",
            aggfunc="last"
        ).rename(columns={"value": "dbp"})

        data = base.join([sbp, dbp], how="outer").reset_index()

        if "sbp" in data.columns and "dbp" in data.columns:
            data["map"] = (data["sbp"] + 2 * data["dbp"]) / 3
        else:
            data["map"] = None

        for m in METRICS:
            if m not in data.columns:
                data[m] = None

        data = data.sort_values("time").reset_index(drop=True)

        for m in METRICS:
            data[f"time_{m}"] = data["time"]

        for m in METRICS:
            data[f"time_{m}"] = data["time"]

        
        data = data.drop(columns=["time"])


        return data

    except Exception as e:
        print(f"[Influx read_data error] {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def close_connection():
    if influx_client:
        influx_client.close()
        print("InfluxDB closed")
