import os
import json
import time
from datetime import datetime
from collections import deque
from config_loader import CLINICAL_RULES
import pandas as pd
import numpy as np

SLOPE_THRESHOLDS_5MIN = {
    "hr":   [-75, -25,  25,  75],   # bpm / 5 min
    "sbp":  [-50, -15,  15,  50],   # mmHg / 5 min
    "dbp":  [-30, -10,  10,  30],
    "map":  [-25,  -5,   5,  25],
    "rr":   [-30, -10,  10,  30],
    "spo2": [-15,  -5,   5,  15],
}


METRICS = ["hr", "rr", "spo2", "sbp", "dbp", "map"]

class Analyzer:
    def __init__(self):
        """Initialize pipeline data"""
        self.hypoxia_starting_time = 0
        self.ox_therapy_monitoring = 600 #secondi
        self.hypoxia_status = ['LIGHT_HYPOXIA', 'GRAVE_HYPOXIA']
        self.par_initialized = False
        self.EWMA = {}
        self.mu_baseline = None
        self.sigma_baseline = None
        self.baseline_history = {metric: {'mu': [], 'sigma': []} for metric in METRICS}
        self.adaptive_window = 100  # Numero di campioni per adattamento baseline
        self.alpha_baseline = 0.05  # Fattore di smoothing per baseline adattativa
        self.outlier_threshold = 3.0  # Soglia per identificare outlier (in deviazioni standard)
        self.therapy = None

    def update_adaptive_baseline(self, metric, new_value, is_outlier=False):
        """
        Updates the baseline dynamically
        
        Args:
            metric: Nome della metrica (es. 'hr', 'spo2')
            new_value: Nuovo valore misurato
            is_outlier: Se True, il valore è considerato outlier e influenza meno la baseline
        """
        if metric not in self.mu_baseline or metric not in self.sigma_baseline:
            return
        
        # Aggiorna il buffer storico
        self.baseline_history[metric]['mu'].append(self.mu_baseline[metric])
        self.baseline_history[metric]['sigma'].append(self.sigma_baseline[metric])
        
        # Mantieni solo gli ultimi N valori
        if len(self.baseline_history[metric]['mu']) > self.adaptive_window:
            self.baseline_history[metric]['mu'].pop(0)
            self.baseline_history[metric]['sigma'].pop(0)
        
        # Fattore di adattamento: più basso per outlier, più alto per valori normali
        if is_outlier:
            alpha = self.alpha_baseline * 0.1  # Influenza ridotta per outlier
        else:
            alpha = self.alpha_baseline
        
        # Aggiorna mu_baseline con EWMA
        old_mu = self.mu_baseline[metric]
        self.mu_baseline[metric] = alpha * new_value + (1 - alpha) * old_mu
        
        # Calcola varianza incrementale (Welford's online algorithm)
        if len(self.baseline_history[metric]['mu']) > 1:
            # Calcola deviazione incrementale
            delta = new_value - old_mu
            old_sigma = self.sigma_baseline[metric]
            
            # Aggiorna varianza con approccio adattativo
            # Usa la media mobile della varianza
            current_variance = (new_value - self.mu_baseline[metric]) ** 2
            
            # Calcola media mobile della varianza sugli ultimi N campioni
            if len(self.baseline_history[metric]['sigma']) > 0:
                # Usa EWMA per la varianza
                self.sigma_baseline[metric] = alpha * current_variance + (1 - alpha) * old_sigma
                
                # Assicurati che la varianza non sia troppo piccola
                min_variance = np.percentile(self.baseline_history[metric]['sigma'], 10) if len(self.baseline_history[metric]['sigma']) > 10 else 0.1
                self.sigma_baseline[metric] = max(self.sigma_baseline[metric], min_variance)
        
    
    def detect_outlier(self, metric, value):
        """
        checks for outliers respect to the baseline
        
        Returns:
            bool: True se è outlier, False altrimenti
        """
        if metric not in self.mu_baseline or metric not in self.sigma_baseline:
            return False
        
        # Calcola z-score
        if self.sigma_baseline[metric] > 0:
            z_score = abs(value - self.mu_baseline[metric]) / np.sqrt(self.sigma_baseline[metric])
            return z_score > self.outlier_threshold
        return False
    
    def calculate_alpha(self, metric, sigma, sigma_max, g, g_max, x_t, 
                       alpha_min=0.02, alpha_max=0.1, w1=1, w2=1, w3=1):
        """
        Calcola alpha_t con baseline adattativa e controllo outlier
        """
        # Rileva se il valore è un outlier
        is_outlier = self.detect_outlier(metric, x_t)
        
        # Calcola c_t con baseline corrente
        if self.sigma_baseline[metric] > 0:
            c_t = abs(x_t - self.mu_baseline[metric]) / np.sqrt(self.sigma_baseline[metric])
        else:
            c_t = 0
        
        # Limita c_t e normalizza
        c_t = min(c_t, 5) / 5  # Normalizza tra 0 e 1
        
        # Normalizza sigma
        sigma_norm = sigma / sigma_max if sigma_max > 0 else 0
        sigma_norm = min(sigma_norm, 1)
        
        # Normalizza gradiente
        g_norm = abs(g) / g_max if g_max > 0 else 0
        g_norm = min(g_norm, 1)
        
        s_t = (w1 * sigma_norm + w2 * g_norm + w3 * c_t) / (w1 + w2 + w3)
        
        # Se è un outlier, aumenta alpha per rispondere più rapidamente
        if is_outlier:
            s_t = min(s_t * 1.5, 1.0)  
        
        alpha_t = alpha_min + (alpha_max - alpha_min) * s_t
        self.update_adaptive_baseline(metric, x_t, is_outlier)
        
        return alpha_t
    
    #def generate_status(self, average_data, therapy: dict):
    def generate_status(self, average_data):
        status = {}

        # =========================
        # LOAD THRESHOLDS
        # =========================

        spo2_stable = CLINICAL_RULES.getfloat("oxygen", "stable_spo2")
        spo2_light = CLINICAL_RULES.getfloat("oxygen", "light_hypoxia_min")
        #oxygen_fail = CLINICAL_RULES.getfloat("oxygen", "oxygen_failure_threshold")
        oxygen_fail_time = CLINICAL_RULES.getfloat("oxygen", "oxygen_failure_threshold")
        rr_min = CLINICAL_RULES.getfloat("respiration", "rr_min")
        rr_max = CLINICAL_RULES.getfloat("respiration", "rr_max")
        rr_tachy = CLINICAL_RULES.getfloat("respiration", "tachy_min")
        rr_distress = CLINICAL_RULES.getfloat("respiration", "distress_min")

        hr_min = CLINICAL_RULES.getfloat("heart_rate", "hr_min")
        hr_max = CLINICAL_RULES.getfloat("heart_rate", "hr_max")
        hr_tachy = CLINICAL_RULES.getfloat("heart_rate", "tachy_min")
        hr_primary = CLINICAL_RULES.getfloat("heart_rate", "primary_min")
        max_tachy = CLINICAL_RULES.getfloat("heart_rate", "max_tachy")

        map_shock = CLINICAL_RULES.getfloat("pressure", "map_shock")
        map_hypo = CLINICAL_RULES.getfloat("pressure", "map_hypo")
        sbp_shock = CLINICAL_RULES.getfloat("pressure", "sbp_shock")

        # =========================
        # COMPUTE MEAN VALUES
        # =========================

        mean_spo2 = average_data["spo2"].mean()
        mean_rr = average_data["rr"].mean()
        mean_hr = average_data["hr"].mean()
        mean_map = average_data["map"].mean()
        mean_sbp = average_data["sbp"].mean()

        # =========================
        # OXYGENATION
        # =========================

        if mean_spo2 >= spo2_stable and rr_min <= mean_rr <= rr_max:
            status["oxigenation"] = "STABLE_RESPIRATION"

        elif spo2_light <= mean_spo2 < spo2_stable:
            status["oxigenation"] = "LIGHT_HYPOXIA"

        elif mean_spo2 < spo2_light:
            #if therapy.get("ox_therapy", 0) >= oxygen_fail:
            if self.hypoxia_starting_time > 0 and \
                (datetime.now().timestamp() - self.hypoxia_starting_time) > oxygen_fail_time:
                status["oxigenation"] = "FAILURE_OXYGEN_THERAPY"
            else:
                status["oxigenation"] = "GRAVE_HYPOXIA"

        else:
            status["oxigenation"] = "STABLE_SATURATION"

        # =========================
        # RESPIRATION
        # =========================

        if rr_tachy <= mean_rr <= rr_distress:
            status["respiration"] = "MODERATE_TACHYPNEA"

        elif mean_rr > rr_distress:
            status["respiration"] = "RESPIRATORY_DISTRESS"

        elif mean_rr < rr_min:
            status["respiration"] = "BRADYPNEA"

        else:
            status["respiration"] = "STABLE_RESPIRATION_EFFORT"

        # =========================
        # HEART RATE
        # =========================

        if hr_min <= mean_hr <= hr_max:
            status["heart_rate"] = "STABLE_HR"

        elif (average_data["spo2"] >= spo2_stable).all() and \
            (average_data["hr"] > hr_primary).all() and \
            (average_data["map"] >= map_hypo).all():
            status["heart_rate"] = "PRIMARY_TACHYCARDIA"

        elif (average_data["spo2"] >= spo2_stable).all() and \
            (average_data["hr"] > hr_tachy).all():
            status["heart_rate"] = "COMPENSED_TACHYCARDIA"

        else:
            status["heart_rate"] = "HIGH_HR"


        # =========================
        # BLOOD PRESSURE
        # =========================

        if mean_map < map_hypo:

            if mean_map < map_shock or mean_sbp < sbp_shock:
                status["blood_pressure"] = "SHOCK"

            elif mean_rr > rr_distress:
                status["blood_pressure"] = "DISTRESS_OVERLOAD"

            elif mean_hr > hr_tachy:
                status["blood_pressure"] = "CIRCULARITY_UNSTABILITY"

            else:
                status["blood_pressure"] = "MODERATE_HYPOTENSION"

        else:
            status["blood_pressure"] = "NORMAL_PERFUSION"

        return status

    def apply_EWMA(self, alpha_t, x_t, metric):
        """Applica EWMA con alpha_t calcolato"""
        new_EWMA = alpha_t * x_t + ((1 - alpha_t) * self.EWMA[metric])
        self.EWMA[metric] = new_EWMA
        return new_EWMA

    def filter_EWMA(self, data: pd.DataFrame, alpha_min=0.02, alpha_max=0.1 ):
        """Filtraggio EWMA con baseline adattativa"""
        if data.empty:
            return data
        
        float_cols = data.select_dtypes(include=['float'])
        # Differenze temporali
        timestamps_cols = {
            i: (data[i].astype('int64') / 1e9).diff().fillna(1) 
            for i in data.select_dtypes(include=['datetimetz','datetime']).columns
        }
        # Gradiente dei valori
        diff = {
            str(i): float_cols[i].diff().replace(0, 1e-9).fillna(1e-9) 
            for i in float_cols.columns
        }
        
        diff = {
            val_k: diff[val_k] / timestamps_cols[time_k] 
            for (time_k, val_k) in zip(timestamps_cols.keys(), diff.keys())
        }
        # Gradiente massimo (95° percentile) per evitare spike
        g_max = {i: np.percentile(np.abs(diff[i].values), 95) for i in diff.keys()}
        
        # Varianza mobile
        sigma = {}
        window = 1
        for col in float_cols.columns:
            values = float_cols[col]
            sigma[col] = values.ewm(span=window).var().fillna(0)
            window += 1
        
        # Sigma massimo per normalizzazione
        all_sigma_values = []
        for col in sigma.keys():
            all_sigma_values.extend(sigma[col].values)
        
        sigma_max = np.percentile(all_sigma_values, 95) if all_sigma_values else 1
        
        # Applica EWMA per ogni colonna
        for c in float_cols.columns:
            # Inizializza EWMA con il primo valore
            self.EWMA[c] = data.iloc[0][c]
            alpha_t = [
                self.calculate_alpha(
                    c, 
                    sigma[c][i], 
                    sigma_max, 
                    diff[c][i], 
                    g_max[c], 
                    data.iloc[i][c],
                    alpha_min=alpha_min, alpha_max=alpha_max
                ) 
                for i in data[c].index
            ]
            
            # Applica EWMA
            ewma_values = []
            for i in range(len(alpha_t)):
                ewma_val = self.apply_EWMA(alpha_t[i], data.iloc[i][c], c)
                ewma_values.append(ewma_val)
            
            data[c] = ewma_values
            time.sleep(1)
        return data
    
    def initialize_baseline(self, data):
        """Inizializza la baseline con i dati storici"""
        float_cols = data.select_dtypes(include=['float'])
        print(float_cols)
        self.mu_baseline = {str(i): float_cols[i].mean() for i in float_cols.columns}
        self.sigma_baseline = {str(i): float_cols[i].var() for i in float_cols.columns}
        
        """print("Baseline initialized:")
        for metric in float_cols.columns:
            print(f"  {metric}: μ = {self.mu_baseline[metric]:.2f}, σ = {np.sqrt(self.sigma_baseline[metric]):.2f}")
        """        
        # Inizializza buffer storico
        for metric in float_cols.columns:
            self.baseline_history[metric]['mu'] = [self.mu_baseline[metric]]
            self.baseline_history[metric]['sigma'] = [self.sigma_baseline[metric]]
    
    """
    def calculate_trend(self,slow_EWMA_data, fast_EWMA_data):
            trend = fast_EWMA_data - slow_EWMA_data
            trend_mean = pd.DataFrame()

            for c in trend.select_dtypes(include=['float']).columns:
                trend_mean[c] = [trend[c].mean()/self.sigma_baseline[c]]
            return trend_mean
    
    def calculate_trend(self, slow_EWMA_data, fast_EWMA_data):
      
        trend_mean = pd.DataFrame()
        phase = fast_EWMA_data - slow_EWMA_data
        for c in phase.select_dtypes(include=['float']).columns:
            d_phase = phase[c].diff()
            d_phase = d_phase.dropna()
            if len(d_phase) == 0 or self.sigma_baseline[c] == 0:
                trend_mean[c] = [0.0]
                continue
            trend_mean[c] = [
                d_phase.mean() / np.sqrt(self.sigma_baseline[c])
            ]

        return trend_mean

    

    def calculate_trend(self, slow_EWMA_data):

        trend_mean = pd.DataFrame()

        for c in slow_EWMA_data.select_dtypes(include=['float']).columns:

            y = slow_EWMA_data[c].values
            x = np.arange(len(y))
            if len(y) < 2 or self.sigma_baseline[c] == 0:
                trend_mean[c] = [0.0]
                continue

            slope = np.polyfit(x, y, 1)[0]

            trend_mean[c] = [
                slope / np.sqrt(self.sigma_baseline[c])
            ]
        return trend_mean

    """    
    
    def calculate_trend(self, slow_EWMA_data):

        trend_mean = pd.DataFrame()

        for c in slow_EWMA_data.select_dtypes(include=['float']).columns:
            
            delta = slow_EWMA_data[c].iloc[-1] - slow_EWMA_data[c].iloc[0]

            if self.sigma_baseline[c] == 0:
                trend_mean[c] = [0.0]
                continue

            trend_mean[c] = [
                delta.mean() / np.sqrt(self.sigma_baseline[c])
            ]
        return trend_mean

    def calculate_delta_time(self, time_col):
        """Compute medio Δt  in seconds"""
        if len(time_col) < 2:
            return 0.0
        
        delta_series = time_col.diff().dropna()
        
        if len(delta_series) == 0:
            return 0.0
        
        delta_mean = delta_series.abs().mean()
        
        return delta_mean.total_seconds()
    
    def calculate_slope(self, data, slow_EWMA_data, fast_EWMA_data):

        slope = {}

        dt = {}
        for col in data.select_dtypes(include=['datetime64']).columns:
            dt[col] = self.calculate_delta_time(data[col])

        for c in METRICS:

            time_key = f"time_{c}"

            if time_key not in dt or dt[time_key] == 0:
                slope[c] = 0
                continue

            delta = fast_EWMA_data[c].iloc[-1] - slow_EWMA_data[c].iloc[-1]

            slope[c] = delta / dt[time_key]

        return slope

        
    def classify_slope(self,value, thresholds):
        sd, md, mi, si = thresholds

        if value <= sd:
            return "STRONG_DECREASE"
        elif value <= md:
            return "MODERATE_DECREASE"
        elif value <= mi:
            return "STABLE"
        elif value <= si:
            return "MODERATE_INCREASE"
        else:
            return "STRONG_INCREASE"

    def classify_all_slopes(self,slopes_dict):
        """
        slopes_dict: dict {metric_name: slope_value}
        returns: dict {metric_name: classification}
        """

        classifications = {}

        for metric, value in slopes_dict.items():
            if metric not in SLOPE_THRESHOLDS_5MIN:
                raise ValueError(f"Soglie non definite per {metric}")

            thresholds = SLOPE_THRESHOLDS_5MIN[metric]
            classifications[metric] = self.classify_slope(value, thresholds)

        return classifications

    def classify_trend(self,trend):
        metric_trends = {}
        for c in trend.columns:
            """print(f"colonna {c} e trend {trend[c]}")"""
            if (trend[c] <= -0.005).all():
                metric_trends[c] = "DETERIORING"
            elif (trend[c] > 0.005).all() :
                metric_trends[c] = "IMPROVING"
            else:
                metric_trends[c] = "STABLE"
        return metric_trends