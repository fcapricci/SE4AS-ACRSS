from os import getenv

from typing import Any

import random

from models.therapy import Therapy

FLUIDS_ADMINISTRATION_RATE : float = getenv("FLUIDS_ADMINISTRATION_RATE") 

class Patient:

    def __init__(self, patient_id : int):
        self.patient_id = patient_id

        # Initialize standard physiological state
        self.heart_rate : dict[str, float] = Patient._initialize_random_base(65, 85)
        self.oxygen_saturation : float = Patient._initialize_random_base(96, 99)
        self.respiration_rate : float = Patient._initialize_random_base(12, 18)
        self.systolic_blood_pressure : float = Patient._initialize_random_base(110, 130)
        self.diastolic_blood_pressure : float = Patient._initialize_random_base(70, 85)

        self.episode : dict[str, Any] = {
            "type": None,
            "duration": 0 
        }

        # Therapy
        self.therapy : Therapy = Therapy(
            oxygen = 0.0,
            fluids = None,
            beta_blocking = 0.0,
            alert = None
        )

    def update_state(self):
        """Evoluzione fisiologica ogni secondo"""

        # Natural evolution
        self._update_heart_rate()

        self._update_oxygen_saturation()

        self._update_respiration_rate()

        self._update_blood_pressure()

        # Therapeutic evolution

        ## Oxygen effect
        self.oxygen_saturation["value"] += 0.2 * self.therapy.oxygen
        self.respiration_rate["value"] -= 0.05 * self.therapy.oxygen

        ## Beta-blocking effect
        self.heart_rate["value"] -= 0.4 * self.therapy.beta_blocking
        self.systolic_blood_pressure["value"] -= 0.2 * self.therapy.beta_blocking

        ## Fluids effect
        self.systolic_blood_pressure["value"] += 0.3 * FLUIDS_ADMINISTRATION_RATE if self.therapy.fluids is not None else 0
        self.diastolic_blood_pressure["value"] += 0.2 * FLUIDS_ADMINISTRATION_RATE if self.therapy.fluids is not None else 0

    def _update_heart_rate(self) -> None:

        # Select random scenario
        rand = random.random()
        if rand < 0.002:
            self.heart_rate["target"] = random.uniform(105, 130)
        elif rand < 0.003:
            self.heart_rate["target"] = random.uniform(45, 55)
        elif rand < 0.015:
            self.heart_rate["target"] = self.heart_rate["base"]

        # Compute plausible evolution
        self.heart_rate["value"] += (self.heart_rate["target"] - self.heart_rate["value"]) * 0.1 + random.gauss(0, 1.2)
        self.heart_rate["value"] = self._clamp(self.heart_rate["value"], 40, 160)

    def _update_oxygen_saturation(self) -> None:

        # Select random scenario
        rand = random.random()
        if rand < 0.002:
            self.oxygen_saturation["target"] = random.uniform(82, 88)
        elif rand < 0.006:
            self.oxygen_saturation["target"] = random.uniform(88, 92)
        elif rand < 0.015:
            self.oxygen_saturation["target"] = self.oxygen_saturation["base"]

        # Compute plausible evolution
        self.oxygen_saturation["value"] += (self.oxygen_saturation["target"] - self.oxygen_saturation["value"]) * 0.15 + random.gauss(0, 0.3)
        self.oxygen_saturation["value"] = self._clamp(self.oxygen_saturation["value"], 75, 100)
    
    def _update_respiration_rate(self) -> None:

        # Select random scenario
        rand = random.random()
        if rand < 0.0025:
            self.respiration_rate["target"] = random.uniform(28, 40)
        elif rand < 0.0035:
            self.respiration_rate["target"] = random.uniform(6, 10)
        elif rand < 0.02:
            self.respiration_rate["target"] = self.respiration_rate["base"]

        # Compute plausible evolution
        self.respiration_rate["value"] += (self.respiration_rate["target"] - self.respiration_rate["value"]) * 0.12 + random.gauss(0, 0.6)
        self.respiration_rate["value"] = self._clamp(self.respiration_rate["value"], 4, 60)

    def _update_blood_pressure(self) -> None:

        if self.episode["type"] is None:

            # Select random episode
            rand = random.random()
            if rand < 0.001:
                self.episode["type"] = "shock"
                self.episode["duration"] = random.randint(20, 60)
            elif rand < 0.004:
                self.episode["type"] = "hypotension"
                self.episode["duration"] = random.randint(30, 90)

        # Compute plausible values based on current episode
        if self.episode["type"] == "hypotension":
            self.systolic_blood_pressure["value"] -= random.uniform(2.5, 6)
            self.diastolic_blood_pressure["value"] -= random.uniform(1.5, 4)

        if self.episode["type"] == "shock":
            self.systolic_blood_pressure["value"] -= random.uniform(4, 9)
            self.diastolic_blood_pressure["value"] -= random.uniform(2.5, 6)

        self.systolic_blood_pressure["value"] += random.gauss(0, 0.6)
        self.diastolic_blood_pressure["value"] += random.gauss(0, 0.4)

        self.systolic_blood_pressure["value"] += (self.systolic_blood_pressure["base"] - self.systolic_blood_pressure["value"]) * 0.05
        self.diastolic_blood_pressure["value"] += (self.diastolic_blood_pressure["base"] - self.diastolic_blood_pressure["value"]) * 0.05

        self.systolic_blood_pressure["value"] = self._clamp(self.systolic_blood_pressure["value"], 55, 190)
        self.diastolic_blood_pressure["value"] = self._clamp(self.diastolic_blood_pressure["value"], 35, 120)
        
        # Reset episode type if duration reached zero
        self.episode["duration"] -= 1
        self.episode["type"] = "none" if self.episode["duration"] <= 0 else self.episode["type"]

    @staticmethod
    def _clamp(x, lo, hi):
        return max(lo, min(hi, x))
    
    @staticmethod
    def _initialize_random_base(min : float, max : float) -> dict[str, float]:

        base = random.uniform(min, max)

        return {
            "base": base,
            "target": base,
            "value": base
        }

    #
    # Getters
    #

    def get_id(self) -> int:
        return self.patient_id
    
    def get_heart_rate(self) -> float:
        return self.heart_rate["value"]
    
    def get_oxygen_saturation(self) -> float:
        return self.oxygen_saturation["value"]

    def get_respiratory_rate(self) -> float:
        return self.respiration_rate["value"]
    
    def get_systolic_blood_pressure(self) -> float:
        return self.systolic_blood_pressure["value"]
    
    def get_diastolic_blood_pressure(self) -> float:
        return self.diastolic_blood_pressure["value"]
