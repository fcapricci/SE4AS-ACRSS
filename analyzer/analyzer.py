import os
import json
import time
from datetime import datetime
from collections import deque

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
import pandas as pd
import numpy as np
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

PATIENT_ID = os.getenv("PATIENT_ID", "p1")

METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]

""" 
Condizione osservata (parametri)	Valutazione del sistema	Azione primaria
SpO₂ ≥ 92% AND RR 12–24	Stato respiratorio stabile	Nessuna azione
SpO₂ < 92% AND ≥ 88%	Ipossia lieve	+1–2 L/min O₂
SpO₂ < 88% per ≥ 10 sec	Ipossia severa	O₂ Boost (≥ 6 L/min) + No beta-bloccanti
SpO₂ < 88% AND O₂ > 4 L/min	Fallimento ossigenoterapia	Alert + sospendere fluidi
RR 24–30 AND SpO₂ ≥ 92%	Tachipnea moderata	+1 L/min O₂
RR > 30	Distress respiratorio	Alert + sospendere fluidi
RR < 12	Bradipnea	Alert 
HR 60–120	Stato cardiaco stabile	Nessuna azione
HR 120–140 AND SpO₂ ≥ 92%	Tachicardia compensata	+1 L/min di O₂
HR > 125 AND SpO₂ ≥ 92% AND BP ≥ 90	Tachicardia primaria	Dose di Beta-bloccante
BP ≥ 90	Perfusione adeguata	Nessuna azione
BP 80–90	Ipotensione moderata	Aprire valvola fluidi bolus
BP < 80	Shock	Alert
BP < 90 AND RR > 30	Sovraccarico + distress	Chiudere valvola fluidi + Alert
BP < 90 AND HR > 120 AND RR < 30	Instabilità circolatoria senza distress	Aprire valvola fluidi + Dose di beta bloccante
 """


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
        """
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
        """
    #def send_status(self, client,status):
    #   client.publish('acrss/analyzer/status',payload=status)
    #def _on_mqtt_disconnect(self, client, userdata, rc, properties=None):
    #    """Callback per disconnessione MQTT"""
    #    print(f"  MQTT disconnesso (code: {rc})")
    def read_data(self, aggregate=False, minutes = 5, limit=1000):
        """Legge gli ultimi dati da InfluxDB"""
        if not self.influx_client:
            print("InfluxDB not available")
            return pd.DataFrame()
        
        data_dict = {}
        if aggregate is True:
            measurement = "vitals_agg"
        else:
            measurement = "vitals_raw"
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
                results = self.query_api.query(query)
                if not results:
                    print("No data available")
                    return False
        
                for table in results:
                    timestamps = []
                    values = []
                    for record in table.records:
                        #print(record)
                        timestamps.append( record.get_time())

                        values.append(record.get_value())
                    
                    
                    data_dict[f'time_{m}'] = timestamps
                    data_dict[m] = values

            except Exception as e:
                print(f"Error in InfluxDB query: {e}")
                import traceback
                traceback.print_exc()
                return False
            except Exception as e:
                print(f" InfluxDB query error: {e}")
                return False
        col = [i for i in data_dict.keys()]
        data = pd.DataFrame(columns=col)
        min_len = min([len(data_dict[i]) for i in data_dict.keys()])
        for k in col:
            data[k] = data_dict[k][:min_len]

        return data
    def read_latest_raw_data(self, minutes=5, limit=100):
        """Legge gli ultimi dati da InfluxDB"""
        if not self.influx_client:
            print("InfluxDB not available")
            return pd.DataFrame()
        data = pd.DataFrame()
        
        for m in METRICS:
            try:
                query = f'''
                from(bucket: "{INFLUX_BUCKET}")
                |> range(start: -{minutes}m)
                |> filter(fn: (r) => r._measurement == "vitals_raw")
                |> filter(fn: (r) => r.patient_id == "{PATIENT_ID}")
                |> filter(fn: (r) => r.metric == "{m}")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: {limit})
                '''
                results = self.query_api.query(query)
                if not results:
                    print("No data available")
                    return False
        
                for table in results:
                    timestamps = []
                    values = []
                    for record in table.records:
                        timestamps.append( record.get_time())
                        values.append(record.get_value())
                        
                    data[f'time_{m}'] = timestamps
                    data[m] = values    
                
            except Exception as e:
                print(f"Error in InfluxDB query: {e}")
                import traceback
                traceback.print_exc()
                return False
            except Exception as e:
                print(f" InfluxDB query error: {e}")
                return False
        return data
    
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
            print(f"   Query error on aggregated data: {e}")    

    def cleanup(self):
        """Pulizia risorse"""
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("MQTT disconnected")
        
        if self.influx_client:
            self.influx_client.close()
            print("InfluxDB closed")


def print_res_agg():
    analyzer = None
    try:
        analyzer = Analyzer()    
        if not analyzer.influx_client:
            print("Cannot connect to InfluxDB")
            return
            
        while True:
            print("\n=== Reading data ===")
            df = analyzer.read_data(aggregate=True,minutes=5)
            """
            if df is not False:
                for m in METRICS:
                    print(df[f'time_{m}'], "\t", df[m])
            """    
            time.sleep(5)  # Aspetta 5 secondi tra le letture
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()



def main():
    """Funzione principale"""
    import threading
    thread = threading.Thread(target=print_res_agg, daemon=False)
    thread.start()
    try:
        while thread.is_alive():
            thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nMain thread interrupted")
    finally:
        print("Shutting down...")   
if __name__ == "__main__":
    main()