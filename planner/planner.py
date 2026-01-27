import os
import json
import time
from datetime import datetime
from collections import deque
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import numpy as np
import signal
import copy

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
| SHOCK                  | blocca beta-bloccanti                    |
| DISTRESS_OVERLOAD      | Vietati fluidi                          |
| BRADYPNEA              | Vietati beta-bloccanti                  |
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
            'alert': set(),
            'timestamp': None
        } 
        self.dt_incr = 5 # seconds per day
        self.MAX_NON_INVASIVE_OX_THERAPY = 6
        self.STARTING_BB_DOSE = 1.25
        self.INCR_BB_DOSE = 0.25
        self.ox_active_therapy = None
        self.bb_active_therapy = {
                                    'carvedilolo_beta_blocking': 0,
                                    'improve_beta_blocking': 0
                                }
        self.last_bb_incr = None 
        self.beta_blocking_target_dose = 10

    def stop_beta_blocking(self, patient_state):
        status = patient_state.get('status', {})

        if status.get('blood_pressure') == 'SHOCK':
            if self.therapy['carvedilolo_beta_blocking'] != 0 :
                self.bb_active_therapy['carvedilolo_beta_blocking'] = self.therapy['carvedilolo_beta_blocking']
                self.bb_active_therapy['improve_beta_blocking'] = self.therapy['improve_beta_blocking']
                self.therapy['carvedilolo_beta_blocking'] = 0
                self.therapy['improve_beta_blocking'] = 0
                self.therapy['carvedilolo_beta_blocking'] = 0
                self.therapy['improve_beta_blocking'] = 0
                print('ARBITRATION: BETA_BLOCKERS_BLOCKED_SHOCK')
        elif self.bb_active_therapy['carvedilolo_beta_blocking'] > 0 :
            print("beta bloccante riattivato")
            self.therapy['carvedilolo_beta_blocking'] = self.bb_active_therapy['carvedilolo_beta_blocking'] 
            self.therapy['improve_beta_blocking'] = self.bb_active_therapy['improve_beta_blocking']
            self.bb_active_therapy['carvedilolo_beta_blocking'] = 0
            self.bb_active_therapy['improve_beta_blocking'] = 0
        

        if status.get('oxigenation') == 'GRAVE_HYPOXIA':
            if self.therapy['carvedilolo_beta_blocking'] !=0:
                self.bb_active_therapy['carvedilolo_beta_blocking'] = self.therapy['carvedilolo_beta_blocking']
                self.bb_active_therapy['improve_beta_blocking'] = self.therapy['improve_beta_blocking']
                self.therapy['carvedilolo_beta_blocking'] = 0
                self.therapy['improve_beta_blocking'] = 0
                print('ARBITRATION: BETA_BLOCKERS_BLOCKED_GRAVE_HYPOXIA')
        elif self.bb_active_therapy['carvedilolo_beta_blocking'] > 0 :
            print("beta bloccante riattivato")
            self.therapy['carvedilolo_beta_blocking'] = self.bb_active_therapy['carvedilolo_beta_blocking'] 
            self.therapy['improve_beta_blocking'] = self.bb_active_therapy['improve_beta_blocking']
            self.bb_active_therapy['carvedilolo_beta_blocking'] = 0
            self.bb_active_therapy['improve_beta_blocking'] = 0

        if status.get('respiration') == 'BRADYPNEA' and self.therapy['carvedilolo_beta_blocking'] != 0:
            self.therapy['carvedilolo_beta_blocking'] = 0
            self.therapy['improve_beta_blocking'] = 0
            print('ARBITRATION: BETA_BLOCKERS_FORBIDDEN_BRADYPNEA')
    def stop_fluids(self, patient_state):
        status = patient_state.get('status', {})

        if status.get('respiration') == 'RESPIRATORY_DISTRESS' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            print('ARBITRATION: FLUIDS_STOP_RESPIRATORY_DISTRESS')

        if status.get('oxigenation') == 'FAILURE_OXYGEN_THERAPY' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            print('ARBITRATION: FLUIDS_STOP_OXYGEN_FAILURE')

        if status.get('blood_pressure') == 'DISTRESS_OVERLOAD' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            print('ARBITRATION: FLUIDS_FORBIDDEN_OVERLOAD')

    def calculate_dt(self):
        if self.last_bb_incr is None:
            self.last_bb_incr = int(datetime.now().timestamp())

        return int(datetime.now().timestamp()) - int(self.last_bb_incr) > self.dt_incr

    def ox_therapy(self, patient_state):
        pattern_decrease = "_DECREASE"
        pattern_stable = "STABLE_"
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        intensity = patient_state.get('intensity', {})
        ox_increased = False
        # Controllo se il paziente necessita di terapia dell'ossigeno
        if status['oxigenation']== "LIGHT_HYPOXIA" and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            if trend['spo2'] == 'IMPROVING':
                self.therapy['ox_therapy'] += 1
                ox_increased = True
                print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - IMPROVING)")
            elif trend['spo2'] == 'STABLE' and (pattern_decrease in intensity['spo2']) and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
                self.therapy['ox_therapy'] += 2
                ox_increased = True
                print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - STABLE)")
            elif trend['spo2'] == 'DETERIORING' and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
                self.therapy['ox_therapy'] += 2
                ox_increased = True
                print(f"Ossigeno aumentato a {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - DETERIORING)")
        elif status['oxigenation'] == "GRAVE_HYPOXIA" and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            self.therapy['ox_therapy'] = self.MAX_NON_INVASIVE_OX_THERAPY 
            print(f"OSSIGENO BOOST: {self.therapy['ox_therapy']} L/min (GRAVE_HYPOXIA)")
        elif status['oxigenation'] == "FAILURE_OXYGEN_THERAPY":
            self.therapy['alert'].add('FAILURE_OXYGEN_THERAPY' )
            print("ALERT: Fallimento ossigenoterapia")
        # Controllo se il paziente viene stabilizzato
        elif pattern_stable in status['oxigenation'] and trend['spo2'] != 'DETERIORING':
            self.therapy['ox_therapy'] = self.therapy['ox_therapy']-1 if self.therapy['ox_therapy'] > 0 else self.therapy['ox_therapy']  
            print(f"Ossigeno diminuito a {self.therapy['ox_therapy']} L/min" if self.therapy['ox_therapy'] > 0 else "")

        if status['respiration'] == 'MODERATE_TACHYPNEA' and trend['rr'] in ['STABLE', 'DETERIORING'] and ox_increased == False and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            if trend['rr'] == 'STABLE':
                self.therapy['ox_therapy'] +=1
                ox_increased = True
            elif trend['rr'] == 'DETERIORING' and pattern_decrease in intensity['rr']:
                 self.therapy['ox_therapy'] +=2
                 ox_increased = True
        elif status['respiration'] == 'RESPIRATORY_DISTRESS':
            self.therapy['alert'].add('RESPIRATORY_DISTRESS')
            print("ALERT: RESPIRATORY_DISTRESS - fluidi sospesi")
        elif status['respiration'] == 'BRADYPNEA':
            self.therapy['alert'].add('BRADYPNEA')
            

    def pharmacy_therapy(self, patient_state):
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        intensity = patient_state.get('intensity', {})

        # Gestione beta-bloccanti
        # Gestione decremento bb
        if status['heart_rate'] == 'STABLE_HR' and trend.get('hr') != 'IMPROVING':
            if self.therapy['improve_beta_blocking'] > 0 and self.calculate_dt():
                self.last_bb_incr = int(datetime.now().timestamp())
                self.therapy['improve_beta_blocking'] -= self.INCR_BB_DOSE
                print(f"Beta-bloccante diminuito a {self.therapy['improve_beta_blocking']}")
            if self.therapy['improve_beta_blocking'] == 0 and self.therapy['carvedilolo_beta_blocking'] == self.STARTING_BB_DOSE:
                if self.calculate_dt():
                    self.last_bb_incr = int(datetime.now().timestamp())
                    self.therapy['carvedilolo_beta_blocking'] -= self.INCR_BB_DOSE
                    print(f"Beta-bloccante base diminuito a {self.therapy['carvedilolo_beta_blocking']}")
        # Gestione incremento bb
        elif status['heart_rate'] == 'PRIMARY_TACHYCARDIA':
                if trend['hr'] == 'STABLE' and self.therapy['carvedilolo_beta_blocking'] == 0:
                    self.last_bb_incr = int(datetime.now().timestamp())
                    self.therapy['carvedilolo_beta_blocking'] = self.STARTING_BB_DOSE
                    print(f"Beta-bloccante dose iniziale a {self.therapy['carvedilolo_beta_blocking']} mg (PRIMARY_TACHYCARDIA - STABLE)")
                elif trend['hr'] == 'DETERIORING' and intensity['hr'] == 'STRONG_INCREASE' and (self.therapy['carvedilolo_beta_blocking'] + self.therapy['improve_beta_blocking']) <= self.beta_blocking_target_dose:
                    print("è dentro il ramo che controlla se incrementare o aggiungere la dose base \n diff time verifica:", self.calculate_dt())
                    if self.calculate_dt():
                        self.last_bb_incr = int(datetime.now().timestamp())
                        if self.therapy['carvedilolo_beta_blocking'] == 1.25:
                            self.therapy['improve_beta_blocking'] += self.INCR_BB_DOSE
                            print(f"Beta-bloccante aumentato a {self.therapy['improve_beta_blocking']} mg (PRIMARY_TACHYCARDIA - DETERIORATING)")
                    else:
                        self.therapy['carvedilolo_beta_blocking'] = self.STARTING_BB_DOSE

        
        # Gestione fluidi e pressione
        if status.get('blood_pressure') == 'MODERATE_HYPOTENSION':
            if trend.get('map') == 'STABLE':
                self.therapy['fluids'] = 'BOLUS'
                print("Fluidi: BOLUS attivato (MODERATE_HYPOTENSION - STABLE)")
            elif trend.get('map') == 'DETERIORING':
                self.therapy['fluids'] = 'BOLUS'
                self.therapy['alert'].add("MODERATE_HYPOTENSION")
                print("ALERT: Ipotensione moderata in peggioramento - BOLUS attivato")
        elif self.therapy['fluids'] == 'BOLUS':
            self.therapy['fluids'] = None

        
        if status.get('blood_pressure') == 'SHOCK' and trend.get('map') != 'IMPROVING' and intensity['map'] not in ['MODERATE_INCREASE', 'STRONG_INCREASE']:
            self.therapy['alert'].add("SHOCK")
            print("ALERT: Shock rilevato")
        if status.get('blood_pressure') == 'DISTRESS_OVERLOAD' and trend.get('spo2') == 'DETERIORING':
            self.therapy['alert'].add("DISTRESS_OVERLOAD")
            print("ALERT: Sovraccarico + distress - fluidi STOP")
        
        if status.get('blood_pressure') == 'CIRCULARITY_UNSTABILITY':
            if trend.get('map') == 'IMPROVING':
                self.therapy['fluids'] = 'BOLUS'
                print("Fluidi: BOLUS attivato (CIRCULARITY_UNSTABILITY - IMPROVING)")
            elif trend.get('map') in ['STABLE', 'DETERIORING'] and self.therapy['carvedilolo_beta_blocking'] == 0 and self.therapy['improve_beta_blocking'] == 0:
                self.therapy['carvedilolo_beta_blocking'] = 1.25
                self.therapy['fluids'] = 'BOLUS'
                print(f"Beta-bloccante impostato a {self.therapy['carvedilolo_beta_blocking']} mg (CIRCULARITY_UNSTABILITY)")
        elif self.therapy['fluids'] == 'BOLUS':
            self.therapy['fluids'] = None
            print("Fluidi: BOLUS disattivato (CIRCULARITY_UNSTABILITY -> STABILIZED)")

        if status['respiration'] == 'BRADYPNEA':
            print("ALERT: BRADYPNEA - fluidi sospesi")
            self.therapy['fluids'] = None
# Variabili globali per gestire lo shutdown
planner = Planner()
new_message = False
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
        global planner
        global new_message
        payload = msg.payload.decode()
        obj = json.loads(payload)
        
        """print(f"\n{'='*60}")
        print(f"Ricevuto messaggio da {msg.topic}")
        print(f"Timestamp: {obj.get('timestamp', 'N/A')}")
        print(f"Dati: {json.dumps(obj, indent=2)}")"""
        
        # Applica logica del planner
        """planner.pharmacy_therapy(obj)
        planner.ox_therapy(obj)
        planner.stop_beta_blocking(obj)
        planner.stop_fluids(obj)"""
        new_message = True
            
    except json.JSONDecodeError as e:
        print(f"Errore nel parsing JSON: {e}")
        print(f"Payload ricevuto: {msg.payload}")
    except Exception as e:
        print(f"Errore nell'elaborazione del messaggio: {e}")
        import traceback
        traceback.print_exc()
def has_therapy_changed(old_therapy, therapy):
    if old_therapy is None or therapy is None:
        return True
    for key in therapy.keys():
        if key == 'timestamp':
            continue  
        old_val = old_therapy.get(key)
        new_val = therapy.get(key)
        
        if old_val != new_val:
            return True
    return False


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
def planner_loop(influx_client,query_api,mqtt_client,planner):
    old_therapy = None
    global new_message
    try:
        print("\n[PLANNER] Planner in esecuzione...")
        print("[PLANNER] Premi Ctrl+C per fermare\n")
        obj = {
                'status':{  'oxigenation':'STABLE_SATURATION',
                            'respiration':'STABLE_RESPIRATION', 
                            'heart_rate':'PRIMARY_TACHYCARDIA',
                            'blood_pressure':'CIRCULARITY_UNSTABILITY'},
                'trend':{'spo2':'STABLE',
                         'rr':'STABLE',
                         'hr':'DETERIORING',
                         'sbp':'STABLE',
                         'dbp':'STABLE',
                         'MAP':'DETERIORING'
                },
                'intensity':{
                    'spo2':'STABLE',
                    'rr':'STABLE',
                    'hr':'STRONG_INCREASE',
                    'sbp':'STABLE',
                    'dbp':'STABLE',
                    'MAP':'DETERIORING'
                }
        }
        while running:
            time.sleep(10)
            print(obj)
            planner.pharmacy_therapy(obj)
            planner.ox_therapy(obj)
            planner.stop_beta_blocking(obj)
            planner.stop_fluids(obj)
            
            print("old_therapy: \n",old_therapy)
            print("therapy: \n", planner.therapy)

            if has_therapy_changed(old_therapy,planner.therapy) and new_message == True:
                planner.therapy['timestamp'] = datetime.now().isoformat()
                send_status(mqtt_client, planner.therapy)
                print("dentro")
                new_message = False
            
            old_therapy = copy.deepcopy(planner.therapy)
            planner.therapy['alert'].clear()    
            
    except KeyboardInterrupt:
        print("\n[PLANNER] Interruzione da tastiera ricevuta")
    except Exception as e:
        print(f"\n[PLANNER] Errore nel loop principale: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
        print("\n[PLANNER] Planner terminato")
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
        query_api = influx_client.query_api()
        write_api = influx_client.write_api(write_options=SYNCHRONOUS)
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
    global planner
    import threading
    thread = threading.Thread(target=planner_loop,args=(influx_client,query_api,mqtt_client,planner), daemon=False)
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