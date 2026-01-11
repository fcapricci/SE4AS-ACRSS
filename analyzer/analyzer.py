import os
import json
import time
from datetime import datetime
from collections import deque

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

# ========== CONFIGURAZIONE ==========
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

PATIENT_ID = os.getenv("PATIENT_ID", "p1")

# Metriche da monitorare
METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]

class Analyzer:
    def __init__(self):
        """Inizializza connessioni"""

        try:
            self.influx_client = InfluxDBClient(
                url=INFLUX_URL,
                token=INFLUX_TOKEN,
                org=INFLUX_ORG
            )
            self.query_api = self.influx_client.query_api()
        except Exception as e:
            print(f"Connection error {e}")
            self.influx_client = None
            return
        try:
            self.mqtt_client = mqtt.Client(
                client_id="analyzer"
            )
            
            #callback per mqtt
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            print("Connected to MQTT!")
            
        except Exception as e:
            print(f"MQTT connection error: {e}")
            self.mqtt_client = None
    
    def send_status(self, client,status):
        client.publish('acrss/analyzer/status',payload=status)
    def _on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        """Callback per disconnessione MQTT"""
        print(f"  MQTT disconnesso (code: {rc})")
    def read_latest_influx_data(self, minutes=5, limit=10):
        """Legge gli ultimi dati da InfluxDB"""
        if not self.influx_client:
            print("InfluxDB non available")
            return []
        try:
            # Query per dati raw
            query = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: -{minutes}m)
              |> filter(fn: (r) => r._measurement == "vitals_raw")
              |> filter(fn: (r) => r.patient_id == "{PATIENT_ID}")
              |> pivot(rowKey: ["_time"], columnKey: ["metric"], valueColumn: "_value")
              |> sort(columns: ["_time"], desc: true)
              |> limit(n: {limit})
            '''
            
            results = self.query_api.query(query)
            data_points = []
            
            if not results:
                print("No data available")
                return []
            
            for table_idx, table in enumerate(results):
                for record_idx, record in enumerate(table.records):
                    timestamp = record.get_time().strftime("%H:%M:%S")
                    
                    # Estrai valori
                    hr = record.values.get("hr", "N/A")
                    rr = record.values.get("rr", "N/A")
                    spo2 = record.values.get("spo2", "N/A")
                    sbp = record.values.get("sbp", "N/A")
                    dbp = record.values.get("dbp", "N/A")
                    map_val = record.values.get("map", "N/A")
                    
                    print(f"   [{record_idx + 1}] {timestamp}: ", end="")
                    print(f"HR={hr}, RR={rr}, SpO2={spo2}%, BP={sbp}/{dbp}, MAP={map_val}")
                    
                    data_points.append({
                        'time': record.get_time(),
                        'hr': hr,
                        'rr': rr,
                        'spo2': spo2,
                        'sbp': sbp,
                        'dbp': dbp,
                        'map': map_val
                    })
            
            return data_points
            
        except Exception as e:
            print(f" InfluxDB query error: {e}")
            return []
    
    def read_aggregated_data(self, minutes=10):
        """Legge dati aggregati da InfluxDB"""
        if not self.influx_client:
            return []
        try:
            query = f'''
            from(bucket: "{INFLUX_BUCKET}")
              |> range(start: -{minutes}m)
              |> filter(fn: (r) => r._measurement == "vitals_agg")
              |> filter(fn: (r) => r.patient_id == "{PATIENT_ID}")
              |> pivot(rowKey: ["_time", "metric"], columnKey: ["_field"], valueColumn: "_value")
              |> sort(columns: ["_time"], desc: true)
              |> limit(n: 5)
            '''
            
            results = self.query_api.query(query)
            
            if not results:
                print("No aggregate data available")
                return []
            
            for table in results:
                for record in table.records:
                    metric = record.values.get("metric", "N/A")
                    mean_val = record.values.get("mean", "N/A")
                    window = record.values.get("window", "N/A")
                    timestamp = record.get_time().strftime("%H:%M:%S")
                    
                    print(f"   {timestamp} - {metric}: {mean_val} (window: {window})")
            
        except Exception as e:
            print(f"   Query error on aggregate data: {e}")    

    def cleanup(self):
        """Pulizia risorse"""
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("MQTT disconnected")
        
        if self.influx_client:
            self.influx_client.close()
            print("InfluxDB closed")

def main():
    """Funzione principale"""
    analyzer = None
    
    try:
        analyzer = Analyzer()
        
        print("\n waiting for connection")
        time.sleep(3)
        
        while True:
            time.sleep(60)
            #analyzer.read_latest_influx_data(minutes=1, limit=1)
                
            analyzer.read_aggregated_data()
    except Exception as e:
        print(f"\n Errore: {e}")
    finally:
        if analyzer:
            analyzer.cleanup()

if __name__ == "__main__":
    main()