import os
import json
import time
from datetime import datetime
from collections import deque
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
        self.hypoxia_starting_time = None
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
    def generate_status(self,average_data,therapy:dict):
        status = {}
        # oxygen check
        #print("therapy dentro generate status ", therapy)
        if (average_data["spo2"] >= 92).all() and ((average_data["rr"] >=12).all() and (average_data["rr"] <= 24).all()):
            status["oxigenation"]="STABLE_RESPIRATION"
        elif (average_data["spo2"] < 92).all() and (average_data["spo2"] >= 88).all():
            status["oxigenation"]="LIGHT_HYPOXIA"
        elif (average_data["spo2"] < 88).all(): 
            if therapy["ox_therapy"] >= 6:
                status["oxigenation"] = "FAILURE_OXYGEN_THERAPY"
            else: 
                status["oxigenation"] = "GRAVE_HYPOXIA"
        else:
            status["oxigenation"]="STABLE_SATURATION"

        
        # respiration check
        if  (average_data["rr"] >= 24).all() and (average_data["rr"] <= 30).all():
            status["respiration"]="MODERATE_TACHYPNEA"
        elif (average_data["rr"] > 30).all():
            status["respiration"]="RESPIRATORY_DISTRESS"
        elif (average_data["rr"] < 12).all():
            status["respiration"]="BRADYPNEA"
        else:
            status['respiration'] = "STABLE_RESPIRATION_EFFORT"
        

        # tachycardia check
        print(average_data["spo2"], average_data["hr"] )
        if (average_data["hr"] >= 60).all() and (average_data["hr"] <= 120).all():
            status["heart_rate"]="STABLE_HR"
        if (average_data["spo2"] >= 92).all():
            if (average_data["hr"] > 125).all() and (average_data['map'] >= 90).all():
                status["heart_rate"]="PRIMARY_TACHYCARDIA"
            elif ((average_data["hr"] > 120).all() and (average_data["hr"] <= 140).all()) :
                status["heart_rate"]="COMPENSED_TACHYCARDIA"
            else:
                status['heart_rate'] = 'HIGH_HR'
        else:
            status['heart_rate'] = 'HIGH_HR'
            
        

        # blood pressure check
        if (average_data["map"] < 65).all():
            if (average_data["map"] < 55).all() or (average_data["sbp"] < 80).all():
                status["blood_pressure"]="SHOCK"
            if  (average_data["rr"] > 30).all():
                status["blood_pressure"]="DISTRESS_OVERLOAD"
            if  (average_data["hr"] > 120).all()   and (average_data["rr"] < 30).all() and (average_data['map'] >= 90).all():
                status["blood_pressure"]="CIRCULARITY_UNSTABILITY"
            if (55 <= average_data["map"]).all():
                status["blood_pressure"]="MODERATE_HYPOTENSION"
        else:
            status["blood_pressure"]="NORMAL_PERFUSION"
        
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
            for i in data.select_dtypes(include=['datetimetz']).columns
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
    """
    def calculate_trend(self, slow_EWMA_data):

        trend_mean = pd.DataFrame()

        for c in slow_EWMA_data.select_dtypes(include=['float']).columns:
            # derivata temporale del segnale (non della fase)
            d_signal = slow_EWMA_data[c].diff().dropna()

            if len(d_signal) == 0 or self.sigma_baseline[c] == 0:
                trend_mean[c] = [0.0]
                continue

            # normalizzazione clinica
            trend_mean[c] = [
                d_signal.mean() / np.sqrt(self.sigma_baseline[c])
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
    
    def calculate_slope(self,data,slow_EWMA_data, fast_EWMA_data):
        dt = {}
        k = {}
        t_slope = {"time_hr":30, "time_rr":90, "time_spo2":60, "time_sbp":60, "time_dbp":30, "time_map":60}
        slope = {}
        for c in data.select_dtypes(include=['datetimetz']).columns:
            dt[c] = self.calculate_delta_time(data[c])
            k[c] = int(t_slope[c] /(dt[c]))
        for c in METRICS:
            t = k[f"time_{c}"]
            i = 0
            s = []

            while t < max(slow_EWMA_data.shape[0],fast_EWMA_data.shape[0]):
                s.append((fast_EWMA_data.iloc[t][c] - slow_EWMA_data.iloc[i][c])/k[f"time_{c}"])
                i+=1
                t+=1
            slope[c] = np.sum(s)
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