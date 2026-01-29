from mqtt_handler import MQTT_Handler
from analyzer import Analyzer
import json
import threading
import time
import copy
from datetime import datetime
import os
import pandas as pd
from influx_handler import read_data, close_connection
PATIENT_ID = os.getenv("PATIENT_ID", "p1")
PUBLISH_TOPIC = f"acrss/plan/{PATIENT_ID}"
therapy_old = {
            'ox_therapy': 0, 
            'fluids': None, 
            'carvedilolo_beta_blocking': 0,
            'improve_beta_blocking': 0,
            'alert': [],
            'timestamp': None
        }



def analysis_loop(analyzer):
    MQTT_Handler.initialize_client()
    MQTT_Handler.connect_to_mqtt()
    try:

        while True:
            time.sleep(1)
            if not analyzer.par_initialized:
                print("Initialization mu and signma")
                #time.sleep(1)
                raw_data = read_data()
                analyzer.initialize_baseline(raw_data)
                analyzer.par_initialized = True    
            else:        
                raw_data = read_data()
            
            agg_data = read_data(measurement='vitals_agg', limit=1)
            if raw_data.empty or agg_data.empty:
                print("No data available, waiting...")
                continue
            

            """print("Applying adaptive EWMA slow filter...")"""
            data_slow_filtered = analyzer.filter_EWMA(raw_data).copy()
            """print("Applying adaptive EWMA fast filter...")"""
            data_fast_filtered = analyzer.filter_EWMA(raw_data,alpha_min = 0.2,alpha_max=0.3).copy()
            
            trend = analyzer.calculate_trend(data_slow_filtered)
            metric_trend = analyzer.classify_trend(trend)
            slope = analyzer.calculate_slope(raw_data,data_slow_filtered, data_fast_filtered)
            slope_trend = analyzer.classify_all_slopes(slope)
            #print("questo è quello che stampa get_receive_message: \n ", MQTT_Handler.get_received_message())
            therapy = MQTT_Handler.get_received_message() if MQTT_Handler.get_received_message() is not None else  therapy_old
            status = analyzer.generate_status(agg_data,therapy)
            analyzer.hypoxia_starting_time = int(datetime.now().timestamp()) if status['oxigenation'] not in analyzer.hypoxia_status else analyzer.hypoxia_starting_time
            ts_ms = int(datetime.now().timestamp() * 1000)
            status_patient = {
                'timestamp':ts_ms,
                'status': status,
                'trend': metric_trend,
                'intensity':slope_trend
            }
            MQTT_Handler.publish(PUBLISH_TOPIC,status_patient)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
            MQTT_Handler.cleanup()

def main():

    analyzer = Analyzer()

    thread = threading.Thread(target=analysis_loop,args=(analyzer,), daemon=False)
    thread.start()
    try:
        while thread.is_alive():
            thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\nMain thread interrupted")
    finally:
        print("Shutting down...")
        close_connection()    

if __name__ == "__main__":
    main()