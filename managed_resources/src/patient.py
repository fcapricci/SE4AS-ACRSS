from os import getenv

import random

from models.therapy import Therapy

FLUIDS_ADMINISTRATION_RATE : float = getenv("FLUIDS_ADMINISTRATION_RATE") 

class Patient:

    def __init__(self, patient_id : int):
        self.patient_id = patient_id

        # Stato fisiologico base
        self.heart_rate : float = 80.0
        self.oxygen_saturation : float = 97.0
        self.respiration_rate : float = 16.0
        self.systolic_blood_pressure : float = 120.0
        self.diastolic_blood_pressure : float = 80.0

        # Therapy
        self.therapy : Therapy = Therapy(
            oxygen = 0.0,
            fluids = None,
            beta_blocking = 0.0,
            alert = None
        )

    def update_state(self):
        """Evoluzione fisiologica ogni secondo"""

        # Dinamica naturale
        self.heart_rate += random.gauss(0, 0.3)
        self.oxygen_saturation += random.gauss(0, 0.05)

        # Effetto ossigeno
        self.oxygen_saturation += 0.2 * self.therapy.oxygen
        self.respiration_rate -= 0.05 * self.therapy.oxygen

        # Effetto beta bloccante
        self.heart_rate -= 0.4 * self.therapy.beta_blocking
        self.systolic_blood_pressure -= 0.2 * self.therapy.beta_blocking

        # Effetto fluidi
        self.systolic_blood_pressure += 0.3 * FLUIDS_ADMINISTRATION_RATE if self.therapy.fluids is not None else 0
        self.diastolic_blood_pressure += 0.2 * FLUIDS_ADMINISTRATION_RATE if self.therapy.fluids is not None else 0
        
        # Clamp fisiologico
        self.heart_rate = max(30, min(160, self.heart_rate))
        self.oxygen_saturation = max(75, min(100, self.oxygen_saturation))
        self.respiration_rate = max(4, min(40, self.respiration_rate))
        self.systolic_blood_pressure = max(60, min(200, self.systolic_blood_pressure))
        self.diastolic_blood_pressure = max(40, min(120, self.diastolic_blood_pressure))

    #
    # Getters
    #

    def get_id(self) -> int:
        return self.patient_id
    
    def get_heart_rate(self) -> float:
        return self.heart_rate
    
    def get_oxygen_saturation(self) -> float:
        return self.oxygen_saturation

    def get_respiratory_rate(self) -> float:
        return self.respiration_rate
    
    def get_systolic_blood_pressure(self) -> float:
        return self.systolic_blood_pressure
    
    def get_diastolic_blood_pressure(self) -> float:
        return self.diastolic_blood_pressure
