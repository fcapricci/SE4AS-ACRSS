from mqtt_handler import MQTT_Handler
from planner import Planner
import json
import threading
import time
import copy
from datetime import datetime
import os
PATIENT_ID = os.getenv("PATIENT_ID", "p1")

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

def planner_loop(planner):
    MQTT_Handler.initialize_client()
    MQTT_Handler.connect_to_mqtt()
    old_therapy = None
    while True:
        time.sleep(10)
        status = MQTT_Handler.get_received_message()
        if status is None:
            continue
        print(f"\n{'='*60}")
        print(f"Timestamp: {status.get('timestamp', 'N/A')}")
        print(f"Dati: {json.dumps(status, indent=2)}")
         

        planner.pharmacy_therapy(status)
        planner.ox_therapy(status)
        planner.fluids_escalation(status)
        planner.handle_beta_blocking(status)
        planner.stop_fluids(status)
        print("Terapia pubblicata dal planner \n",planner.therapy)
        if has_therapy_changed(old_therapy,planner.therapy):
                
                therapy = planner.get_serializable_therapy()
                therapy['timestamp'] = datetime.now().isoformat()
                MQTT_Handler.publish(therapy)

                
            
        old_therapy = copy.deepcopy(planner.therapy)
        planner.therapy['alert'].clear()

def main():

    planner = Planner()

    thread = threading.Thread(target=planner_loop,args=(planner,), daemon=False)
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