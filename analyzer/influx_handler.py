from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.query_api import QueryApi
import pandas as pd
from influxdb_client.client.write_api import SYNCHRONOUS
import os
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")
PATIENT_ID = os.getenv("PATIENT_ID", "p1")
METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]


try:
    influx_client = InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG
    )
    query_api = influx_client.query_api()
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
except Exception as e:
    print(f"Connection error {e}")
    influx_client = None



def read_data(measurement='vitals_raw', minutes=5, limit=1000):
        """Reads data from InfluxDB"""
        data_dict = {}
        for m in METRICS:
            try:
                query = f'''
                from(bucket: "{INFLUX_BUCKET}")
                |> range(start: -{minutes}m)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> filter(fn: (r) => r.patient_id == "{PATIENT_ID}")
                |> filter(fn: (r) => r.metric == "{m}")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: {limit})
                '''
                results = query_api.query(query)
                if not results:
                    print("No data available")
                    return pd.DataFrame()
        
                for table in results:
                    timestamps = []
                    values = []
                    for record in table.records:
                        timestamps.append(record.get_time())
                        values.append(record.get_value())
                    data_dict[f'time_{m}'] = timestamps
                    data_dict[m] = values
            except Exception as e:
                print(f"Error in InfluxDB query: {e}")
                import traceback
                traceback.print_exc()
                return pd.DataFrame()
        col = [i for i in data_dict.keys()]
        data = pd.DataFrame(columns=col)
        min_len = min([len(data_dict[i]) for i in data_dict.keys()])
        for k in col:
            data[k] = data_dict[k][:min_len]
        data = data.iloc[::-1].reset_index(drop=True)
        return data

def close_connection():
    if influx_client:
        influx_client.close()
        print("InfluxDB closed")