from mqtt_handler import MQTTHandler
from analyzer import Analyzer
import threading
import time
import pandas as pd
from datetime import datetime
from datetime import timedelta
import os
from influx_handler import read_data, close_connection

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")

# numero pazienti
PATIENTS_NUMBER = int(os.getenv("PATIENTS_NUMBER", 1))
PATIENT_IDS = [str(i + 1) for i in range(PATIENTS_NUMBER)]

therapy_old = {
    'ox_therapy': 0,
    'fluids': None,
    'carvedilolo_beta_blocking': 0,
    'improve_beta_blocking': 0,
    'alert': [],
    'timestamp': None
}


def compute_agg_from_raw(raw_data, window_seconds=60):
    """
    Replica vitals_agg:
    media sugli ultimi window_seconds
    restituisce DataFrame con 1 riga
    """
    if raw_data.empty:
        return pd.DataFrame()

    df = raw_data.copy()

    # usiamo una delle colonne temporali dell'Analyzer
    time_col = "time_hr"
    df[time_col] = pd.to_datetime(df[time_col])

    end_time = df[time_col].max()
    start_time = end_time - timedelta(seconds=window_seconds)

    window = df[df[time_col] >= start_time]

    if window.empty:
        return pd.DataFrame()

    agg = window[["hr", "rr", "spo2", "sbp", "dbp", "map"]].mean()
    agg_df = agg.to_frame().T

    # ricrea time_* come vuole l'Analyzer
    for m in ["hr", "rr", "spo2", "sbp", "dbp", "map"]:
        agg_df[f"time_{m}"] = end_time

    return agg_df


def analysis_loop(patient_id, analyzer):

    publish_topic = f"acrss/symptoms/{patient_id}"


    mqtt = MQTTHandler(MQTT_BROKER)
    mqtt.start()

    try:
        while True:
            time.sleep(1)

            # ============================
            # BOOTSTRAP (una sola volta)
            # ============================
            if not analyzer.par_initialized:
                print(f"[{patient_id}] Initializing baseline")

                raw_data = read_data(
                    patient_id=patient_id,
                    full_history=True
                )

                if raw_data.isna().any().any():    
                    print(f"[{patient_id}] Baseline initialized")
                else:
                    analyzer.initialize_baseline(raw_data)
                    analyzer.par_initialized = True

            if raw_data.isna().any().any():
                    print(f"[{patient_id}] No historical data yet, waiting...")
                    continue
            # ============================
            # RUNTIME
            # ============================
            raw_data = read_data(
                patient_id=patient_id,
                minutes=5
            )

            if raw_data.empty:
                print(f"[{patient_id}] No data available, waiting...")
                continue
            
            # ---- EWMA ----
            data_slow_filtered = analyzer.filter_EWMA(raw_data.copy())
            data_fast_filtered = analyzer.filter_EWMA(
                raw_data.copy(),
                alpha_min=0.2,
                alpha_max=0.3
            )

            # ---- trend & slope ----
            trend = analyzer.calculate_trend(data_slow_filtered)
            metric_trend = analyzer.classify_trend(trend)
            
            slope = analyzer.calculate_slope(
                raw_data,
                data_slow_filtered,
                data_fast_filtered
            )
            slope_trend = analyzer.classify_all_slopes(slope)

            therapy = therapy_old

            agg_data = compute_agg_from_raw(raw_data, window_seconds=60)


            if agg_data.empty:
                print(f"[{patient_id}] Not enough data for aggregation yet")
                continue

            # ---- status ----
            status = analyzer.generate_status(agg_data, therapy)

            analyzer.hypoxia_starting_time = (
                int(datetime.now().timestamp())
                if status['oxigenation'] not in analyzer.hypoxia_status
                else analyzer.hypoxia_starting_time
            )

            ts_ms = int(datetime.now().timestamp() * 1000)
            
            status_patient = {
                'timestamp': ts_ms,
                'status': status,
                'trend': metric_trend,
                'intensity': slope_trend
            }
            mqtt.publish(publish_topic, status_patient)

    except KeyboardInterrupt:
        print(f"[{patient_id}] Interrupted by user")
    except Exception as e:
        print(f"[{patient_id}] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mqtt.stop()


def main():
    threads = []

    for patient_id in PATIENT_IDS:
        analyzer = Analyzer()

        thread = threading.Thread(
            target=analysis_loop,
            args=(patient_id, analyzer),
            daemon=False
        )
        thread.start()
        threads.append(thread)

        print(f"Started analyzer thread for patient {patient_id}")

    try:
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=1)
    except KeyboardInterrupt:
        print("\nMain thread interrupted")
    finally:
        print("Shutting down...")
        close_connection()


if __name__ == "__main__":
    main()
