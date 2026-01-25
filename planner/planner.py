import os
import json
import time
from datetime import datetime
from collections import deque
import re
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np
import signal
import sys


"""
    STABLE_SATURATION	Nessuna azione
    LIGHT_HYPOXIA	+1–2 L/min O₂
    GRAVE_HYPOXIA	O₂ Boost (≥ 6 L/min) + No beta-bloccanti
    FAILURE_OXYGEN_THERAPY	Alert + sospendere fluidi

    MODERATE_TACHYPNEA	+1 L/min O₂
    RESPIRATORY_DISTRESS	Alert + sospendere fluidi
    BRADYPNEA	Alert
    STABLE_RESPIRATION Nessuna azione

    STABLE_HR	Nessuna azione
    COMPENSED_TACHYCARDIA	+1 L/min di O₂
    PRIMAY_TACHYCARDIA	Dose di Beta-bloccante

    NORMAL_PERFUSION Nessuna azione
    MODERATE_HYPOTENSION	Aprire valvola fluidi bolus
    SHOCK	Alert
    DISTRESS_OVERLOAD	Chiudere valvola fluidi + Alert
    CIRCULARITY_UNSTABILITY senza distress	Aprire valvola fluidi + Dose di beta bloccante
"""


"""
DECISION TABLES:
                            OXIGENATION
| STATUS                        | Trend SpO₂    | Intensity SpO₂           | AZIONE                    |
| ----------------------        | ------------- | ------------------------ | ------------------------- |
| STABLE_SATURATION/RESPIRATION | qualsiasi     | qualsiasi                | Nessuna azione            |
| LIGHT_HYPOXIA                 | IMPROVING     | qualsiasi                | +1 L/min O₂               |
| LIGHT_HYPOXIA                 | STABLE        | MODERATE/STRONG_DECREASE | +2 L/min O₂               |
| LIGHT_HYPOXIA                 | DETERIORATING | qualsiasi                | +2 L/min O₂               |
| GRAVE_HYPOXIA                 | qualsiasi     | qualsiasi                | O₂ Boost ≥ 6 L/min        |
| FAILURE_OXYGEN_THERAPY        | qualsiasi     | qualsiasi                | Alert + sospendere fluidi |

                            RESPIRATION

| STATUS               | Trend RR      | Intensity RR             | AZIONE                    |
| -------------------- | ------------- | ------------------------ | ------------------------- |
| STABLE_RESPIRATION   | qualsiasi     | qualsiasi                | Nessuna azione            |
| MODERATE_TACHYPNEA   | IMPROVING     | qualsiasi                | Nessuna azione            |
| MODERATE_TACHYPNEA   | STABLE        | qualsiasi                | +1 L/min O₂               |
| MODERATE_TACHYPNEA   | DETERIORATING | MODERATE/STRONG_DECREASE | +2 L/min O₂             |
| RESPIRATORY_DISTRESS | qualsiasi     | qualsiasi                | Alert + sospendere fluidi |
| BRADYPNEA            | qualsiasi     | qualsiasi                | Alert                     |

                            HEART RATE

| STATUS                | Trend HR      | Intensity HR      | AZIONE                         |
| --------------------- | ------------- | ----------------- | ------------------------------ |
| STABLE_HR             | qualsiasi     | qualsiasi         | Nessuna azione                 |
| COMPENSED_TACHYCARDIA | IMPROVING     | qualsiasi         | Nessuna azione                 |
| COMPENSED_TACHYCARDIA | STABLE        | qualsiasi         | +1 L/min O₂                    |
| COMPENSED_TACHYCARDIA | DETERIORATING | STRONG_DECREASE   | +1 L/min O₂                    |
| PRIMARY_TACHYCARDIA   | IMPROVING     | MODERATE_INCREASE | keep_monitoring                |
| PRIMARY_TACHYCARDIA   | STABLE        | qualsiasi         | Beta-bloccante (dose standard) |
| PRIMARY_TACHYCARDIA   | DETERIORATING | STRONG_INCREASE   | Beta-bloccante (dose ↑)        |

                            BLOOD PERSSURE

| STATUS                  | Trend map           | Intensity map            | AZIONE                  |
| ----------------------- | ------------------- | ------------------------ | ----------------------- |
| NORMAL_PERFUSION        | qualsiasi           | qualsiasi                | Nessuna azione          |
| MODERATE_HYPOTENSION    | IMPROVING           | qualsiasi                | Monitor                 |
| MODERATE_HYPOTENSION    | STABLE              | qualsiasi                | Fluidi bolus            |
| MODERATE_HYPOTENSION    | DETERIORATING       | MODERATE/STRONG_DECREASE | Fluidi bolus + Alert    |
| SHOCK                   | IMPROVING           | MODERATE                 | Mantenere terapia       |
| SHOCK                   | STABLE              | qualsiasi                | Alert                   |
| SHOCK                   | DETERIORATING       | qualsiasi                | Alert critico           |
| DISTRESS_OVERLOAD       | qualsiasi           | qualsiasi                | Chiudere fluidi + Alert |
| CIRCULARITY_UNSTABILITY | IMPROVING           | qualsiasi                | Fluidi                  |
| CIRCULARITY_UNSTABILITY | STABLE/DTERIORATING | qualsiasi                | Fluidi + Beta-bloccante |


ARBITRATION TABLE


| CONDIZIONE             | AZIONE                                  |
| ---------------------- | --------------------------------------- |
| RESPIRATORY_DISTRESS   | Sospendere TUTTI i fluidi               |
| FAILURE_OXYGEN_THERAPY | Sospendere fluidi                       |
| SHOCK                  | blocca beta-bloccanti |
| DISTRESS_OVERLOAD      | Vietati fluidi                          |
| BRADYPNEA              | Vietati beta-bloccanti                  |
| map < 55               | Vietati beta-bloccanti                  |
| SpO₂ < 88              | Vietati beta-bloccanti                  |

"""

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
SOURCE = "sim"
PATIENT_ID = os.getenv("PATIENT_ID", "p1")
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "acrss-super-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "acrss")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "acrss")

METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]

class Planner():
    def __init__(self):
        self.intensity = ["STRONG_DECREASE","MODERATE_DECREASE","STABLE","MODERATE_INCREASE","STRONG_INCREASE"]
        self.trend = ["DETERIORING","IMPROVING","STABLE"]
        self.monitored_status = ['oxigenation','respiration', 'heart_rate''blood_pressure']
        self.therapy = {
            'ox_therapy': 0, 
            'fluids': None, 
            'carvedilolo_beta_blocking': 0,
            'improve_beta_blocking': 0,
            'alert': None,
            'timestamp': None
        } 
        self.beta_blocking_target_dose = 10
    
    def define_ox_therapy(self, patient_state):
        pattern = "*_DECREASE"
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        intensity = patient_state.get('intensity', {})
        ox_increased = False

        # Controllo se il paziente viene stabilizzato
        if (status.get('oxigenation') in ['STABLE_RESPIRATION', 'STABLE_SATURATION'] and 
            trend.get('spo2') != 'DETERIORING' and 
            status.get('respiration') != 'MODERATE_TACHYPNEA' and 
            status.get('heart_rate') != 'COMPENSED_TACHYCARDIA'):
            if self.therapy['ox_therapy'] > 0:
                self.therapy['ox_therapy'] -= 1
                """print(f"Ossigeno diminuito a {self.therapy['ox_therapy']} L/min")"""
        else:
            # Controllo se il paziente necessita di terapia dell'ossigeno
            if status.get('oxigenation') == 'LIGHT_HYPOXIA':
                ox_increased = True
                if trend.get('spo2') == 'IMPROVING':
                    self.therapy['ox_therapy'] += 1
                    """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - IMPROVING)")"""
                elif trend.get('spo2') == 'STABLE':
                    if intensity.get('spo2') in ['STRONG_DECREASE', 'MODERATE_DECREASE']:
                        self.therapy['ox_therapy'] += 2
                        """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - STABLE - DECREASING)")"""
                else:
                    self.therapy['ox_therapy'] += 2
                    """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - DETERIORATING)")"""
            
            elif status.get('oxigenation') == 'GRAVE_HYPOXIA':
                ox_increased = True
                if self.therapy['ox_therapy'] < 6:
                    self.therapy['ox_therapy'] = 6
                else:
                    self.therapy['ox_therapy'] += 1
                """print(f"OSSIGENO BOOST: {self.therapy['ox_therapy']} L/min (GRAVE_HYPOXIA)")"""
            
            elif status.get('oxigenation') == "FAILURE_OXYGEN_THERAPY":
                self.therapy['alert'] = "FAILURE_OXYGEN_THERAPY"
                ox_increased = True
                """print("ALERT: Fallimento ossigenoterapia")"""

            # Controlli per respirazione
            if trend.get('rr') != 'IMPROVING':
                if trend.get('rr') == 'DETERIORATING' and intensity.get('rr') in ['MODERATE_DECREASE', 'STRONG_DECREASE'] and not ox_increased:
                    self.therapy['ox_therapy'] += 2
                    """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (RR DETERIORATING)")"""
                elif trend.get('rr') == 'STABLE' and not ox_increased:
                    self.therapy['ox_therapy'] += 2
                    """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (RR STABLE)")"""

            # Controlli per frequenza cardiaca
            if (trend.get('hr') == 'STABLE' or (trend.get('hr') == 'DETERIORING' and intensity.get('hr') == 'STRONG_INCREASE')) and not ox_increased:
                self.therapy['ox_therapy'] += 1
                """print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (HR condition)")"""

        # Alert per problemi respiratori
        if status.get('respiration') == 'BRADYPNEA':
            self.therapy['alert'] = "BRADYPNEA"
            """print("ALERT: Bradipnea rilevata")"""
        elif status.get('respiration') == 'RESPIRATORY_DISTRESS':
            self.therapy['alert'] = "RESPIRATORY_DISTRESS"
            self.therapy['fluids'] = 'STOP'
            """print("ALERT: Distress respiratorio - fluidi sospesi")"""

    def pharmacy_therapy(self, patient_state):
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        
        # Gestione beta-bloccanti
        if status.get('heart_rate') == 'STABLE_HR' and trend.get('hr') != 'DETERIORING':
            if self.therapy['improve_beta_blocking'] >= 0.25:
                self.therapy['improve_beta_blocking'] -= 0.25
                """print(f"Beta-bloccante miglioramento diminuito a {self.therapy['improve_beta_blocking']}")"""
            if self.therapy['improve_beta_blocking'] == 0 and self.therapy['carvedilolo_beta_blocking'] >= 0.25:
                self.therapy['carvedilolo_beta_blocking'] -= 0.25
                """print(f"Beta-bloccante base diminuito a {self.therapy['carvedilolo_beta_blocking']}")"""
        else:
            if status.get('heart_rate') == 'PRIMARY_TACHYCARDIA':
                if trend.get('hr') == 'STABLE' and self.therapy['carvedilolo_beta_blocking'] < 1.25:
                    self.therapy['carvedilolo_beta_blocking'] = 1.25
                    """print(f"Beta-bloccante impostato a {self.therapy['carvedilolo_beta_blocking']} mg (PRIMARY_TACHYCARDIA - STABLE)")"""
                elif trend.get('hr') == 'DETERIORING' and (self.therapy['carvedilolo_beta_blocking'] + self.therapy['improve_beta_blocking']) < self.beta_blocking_target_dose:
                    self.therapy['improve_beta_blocking'] += 0.25
                    """print(f"Beta-bloccante miglioramento aumentato a {self.therapy['improve_beta_blocking']} mg (PRIMARY_TACHYCARDIA - DETERIORATING)")"""
        
        # Gestione fluidi e pressione
        if status.get('blood_pressure') == 'MODERATE_HYPOTENSION':
            if trend.get('map') == 'STABLE':
                self.therapy['fluids'] = 'BOLUS'
                """print("Fluidi: BOLUS attivato (MODERATE_HYPOTENSION - STABLE)")"""
            elif trend.get('map') == 'DETERIORATING':
                self.therapy['fluids'] = 'BOLUS'
                self.therapy['alert'] = "MODERATE_HYPOTENSION_DETERIORATING"
                """print("ALERT: Ipotensione moderata in peggioramento - BOLUS attivato")"""
        
        if status.get('blood_pressure') == 'SHOCK' and trend.get('map') not in ['IMPROVING', 'DETERIORING']:
            self.therapy['alert'] = "SHOCK"
            """print("ALERT: Shock rilevato")"""
        
        if status.get('blood_pressure') == 'DISTRESS_OVERLOAD' and trend.get('spo2') == 'DETERIORING':
            self.therapy['fluids'] = 'STOP'
            self.therapy['alert'] = "DISTRESS_OVERLOAD"
            """print("ALERT: Sovraccarico + distress - fluidi STOP")"""
        
        if status.get('blood_pressure') == 'CIRCULARITY_UNSTABILITY':
            if trend.get('map') == 'IMPROVING':
                self.therapy['fluids'] = 'BOLUS'
                """print("Fluidi: BOLUS attivato (CIRCULARITY_UNSTABILITY - IMPROVING)")"""
            elif trend.get('map') in ['STABLE', 'DETERIORING'] and self.therapy['carvedilolo_beta_blocking'] == 0 and self.therapy['improve_beta_blocking'] == 0:
                self.therapy['carvedilolo_beta_blocking'] = 1.25
                """print(f"Beta-bloccante impostato a {self.therapy['carvedilolo_beta_blocking']} mg (CIRCULARITY_UNSTABILITY)")"""

# Variabili globali per gestire lo shutdown
planner = Planner()
mqtt_client = None
influx_client = None
running = True

def signal_handler(sig, frame):
    """Gestisce i segnali di interruzione (Ctrl+C)."""
    global running
    print("\nRicevuto segnale di interruzione, shutdown in corso...")
    running = False
    cleanup()

def on_connect(client, userdata, flags, rc, properties):
    """Callback per connessione MQTT."""
    if rc == 0:
        print(f"[PLANNER] Connesso al broker MQTT con successo")
        client.subscribe("acrss/analyzer/#")
        print(f"[PLANNER] Sottoscritto a acrss/analyzer/#")
    else:
        print(f"[PLANNER] Errore di connessione MQTT: {rc}")

def on_message(client, userdata, msg):
    """Callback per messaggi MQTT in arrivo."""
    try:
        payload = msg.payload.decode()
        obj = json.loads(payload)
        """ 
        print(f"\n{'='*60}")
        print(f"Ricevuto messaggio da {msg.topic}")
        print(f"Timestamp: {obj.get('timestamp', 'N/A')}")
        print(f"Dati: {json.dumps(obj, indent=2)}")
        """
        
        # Aggiorna timestamp della terapia
        planner.therapy['timestamp'] = datetime.now().isoformat()
        
        # Applica logica del planner
        planner.define_ox_therapy(obj)
        planner.pharmacy_therapy(obj)
        
        # Invia stato aggiornato
        send_status(client, planner.therapy)
        
        # Resetta alert (se non critico)
        if planner.therapy['alert'] not in ['SHOCK', 'RESPIRATORY_DISTRESS', 'FAILURE_OXYGEN_THERAPY']:
            planner.therapy['alert'] = None
            
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
        print(f"Payload ricevuto: {msg.payload}")
    except Exception as e:
        print(f"Errore nell'elaborazione del messaggio: {e}")
        import traceback
        traceback.print_exc()

def send_status(client, status):
    """Pubblica lo stato della terapia."""
    try:
        payload = json.dumps(status, default=str)
        topic = f"acrss/plan/{PATIENT_ID}"
        client.publish(topic, payload=payload, qos=1)
        print(f"Terapia pubblicata su {topic}:")
        print(f"  Ossigeno: {status.get('ox_therapy', 0)} L/min")
        print(f"  Fluidi: {status.get('fluids', 'None')}")
        print(f"  Beta-bloccante: {status.get('carvedilolo_beta_blocking', 0)} mg")
        print(f"  Beta-bloccante aggiuntivo: {status.get('improve_beta_blocking', 0)} mg")
        print(f"  Alert: {status.get('alert', 'None')}")
    except Exception as e:
        print(f"Errore nella pubblicazione dello stato: {e}")

def _on_mqtt_disconnect(client, userdata, rc, properties):
    """Callback per disconnessione MQTT."""
    print(f"[PLANNER] Disconnesso dal broker MQTT (codice: {rc})")
    if rc != 0:
        print("[PLANNER] Tentativo di riconnessione...")

def cleanup():
    """Pulizia risorse."""
    global mqtt_client, influx_client
    
    print("\n[PLANNER] Pulizia risorse in corso...")
    
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("[PLANNER] Client MQTT disconnesso")
        except Exception as e:
            print(f"[PLANNER] Errore nella disconnessione MQTT: {e}")
    
    if influx_client:
        try:
            influx_client.close()
            print("[PLANNER] Client InfluxDB chiuso")
        except Exception as e:
            print(f"[PLANNER] Errore nella chiusura InfluxDB: {e}")
    
    print("[PLANNER] Pulizia completata")

def main():
    """Funzione principale."""
    global mqtt_client, influx_client, running
    
    # Registra handler per segnali
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    
    # Inizializzazione InfluxDB
    try:
        influx_client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        print("[PLANNER] Connesso a InfluxDB")
    except Exception as e:
        print(f"[PLANNER] Errore connessione InfluxDB: {e}")
        influx_client = None
    
    # Inizializzazione MQTT
    try:
        mqtt_client = mqtt.Client(
            client_id=f"planner_{PATIENT_ID}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.on_disconnect = _on_mqtt_disconnect
        
        # Configura reconnessione automatica
        mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        
        print("[PLANNER] Client MQTT inizializzato e connesso")
        
    except Exception as e:
        print(f"[PLANNER] Errore connessione MQTT: {e}")
        mqtt_client = None
        running = False
    
    # Loop principale
    try:
        print("\n[PLANNER] Planner in esecuzione...")
        print("[PLANNER] Premi Ctrl+C per fermare\n")
        
        heartbeat_count = 0
        while running:
            time.sleep(1)
            heartbeat_count += 1
            
            # Heartbeat ogni 30 secondi
            if heartbeat_count % 30 == 0 and mqtt_client:
                status_msg = {
                    "timestamp": datetime.now().isoformat(),
                    "component": "planner",
                    "status": "running",
                    "patient_id": PATIENT_ID,
                    "heartbeat": heartbeat_count
                }
                mqtt_client.publish(
                    f"acrss/planner/heartbeat/{PATIENT_ID}",
                    payload=json.dumps(status_msg)
                )
                print(f"[PLANNER] Heartbeat inviato ({heartbeat_count})")
    
    except KeyboardInterrupt:
        print("\n[PLANNER] Interruzione da tastiera ricevuta")
    except Exception as e:
        print(f"\n[PLANNER] Errore nel loop principale: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
        print("\n[PLANNER] Planner terminato")

if __name__ == "__main__":
    main()