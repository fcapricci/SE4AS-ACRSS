from os import getenv
from typing import Any
import random
from models.therapy import Therapy

FLUIDS_ADMINISTRATION_RATE: float = float(getenv("FLUIDS_ADMINISTRATION_RATE"))


class Patient:

    def __init__(self, patient_id: int):
        self.patient_id = patient_id

        self.heart_rate = self._initialize_random_base(65, 85)
        self.oxygen_saturation = self._initialize_random_base(96, 99)
        self.respiration_rate = self._initialize_random_base(12, 18)
        self.systolic_blood_pressure = self._initialize_random_base(110, 130)
        self.diastolic_blood_pressure = self._initialize_random_base(70, 85)

        self.episode: dict[str, Any] = {
            "type": None,
            "duration": 0
        }

        self.therapy = Therapy(
            oxygen=0.0,
            fluids=None,
            beta_blocking=0.0,
            alert=None
        )

    def update_state(self):

        self._update_heart_rate()
        self._update_oxygen_saturation()
        self._update_respiration_rate()
        self._update_blood_pressure()

        self._apply_therapy_effects()

        self._final_clamp()

    def _apply_therapy_effects(self):

        # OXYGEN
        if self.therapy.oxygen > 0:
            # Increase SpO2 target
            self.oxygen_saturation["target"] = min(
                100,
                98 + 0.5 * self.therapy.oxygen
            )

            # Reduce respiratory drive
            self.respiration_rate["target"] -= 0.6 * self.therapy.oxygen

        # BETA BLOCKING
        if self.therapy.beta_blocking > 0:
            self.heart_rate["target"] -= 8 * self.therapy.beta_blocking
            self.systolic_blood_pressure["target"] -= 3 * self.therapy.beta_blocking

        # FLUIDS 
        if self.therapy.fluids is not None:
            self.systolic_blood_pressure["target"] += 10 * FLUIDS_ADMINISTRATION_RATE
            self.diastolic_blood_pressure["target"] += 5 * FLUIDS_ADMINISTRATION_RATE

            # Fluids shorten shock duration
            if self.episode["type"] == "shock":
                self.episode["duration"] -= 2

    # HEART RATE

    def _update_heart_rate(self):

        rand = random.random()

        if rand < 0.02:
            self.heart_rate["target"] = random.uniform(105, 130)
        elif rand < 0.03:
            self.heart_rate["target"] = random.uniform(45, 55)
        elif rand < 0.015:
            self.heart_rate["target"] = self.heart_rate["base"]

        # Shock compensation
        if self.episode["type"] == "shock":
            self.heart_rate["target"] = 120

        self.heart_rate["value"] += (
            (self.heart_rate["target"] - self.heart_rate["value"]) * 0.1
            + random.gauss(0, 1.2)
        )

    # SPO2

    def _update_oxygen_saturation(self):

        rand = random.random()

        if rand < 0.02:
            self.oxygen_saturation["target"] = random.uniform(82, 88)
        elif rand < 0.06:
            self.oxygen_saturation["target"] = random.uniform(88, 92)
        elif rand < 0.015:
            self.oxygen_saturation["target"] = self.oxygen_saturation["base"]

        self.oxygen_saturation["value"] += (
            (self.oxygen_saturation["target"] - self.oxygen_saturation["value"]) * 0.15
            + random.gauss(0, 0.3)
        )

    # RESPIRATION

    def _update_respiration_rate(self):

        rand = random.random()

        if rand < 0.025:
            self.respiration_rate["target"] = random.uniform(28, 40)
        elif rand < 0.035:
            self.respiration_rate["target"] = random.uniform(6, 10)
        elif rand < 0.02:
            self.respiration_rate["target"] = self.respiration_rate["base"]

        # Hypoxia-driven tachypnea
        if self.oxygen_saturation["value"] < 90:
            self.respiration_rate["target"] = 30

        self.respiration_rate["value"] += (
            (self.respiration_rate["target"] - self.respiration_rate["value"]) * 0.12
            + random.gauss(0, 0.6)
        )

    # BLOOD PRESSURE

    def _update_blood_pressure(self):

        if self.episode["type"] is None:

            rand = random.random()

            if rand < 0.01:
                self.episode["type"] = "shock"
                self.episode["duration"] = random.randint(40, 80)

            elif rand < 0.04:
                self.episode["type"] = "hypotension"
                self.episode["duration"] = random.randint(40, 100)

        if self.episode["type"] == "hypotension":
            self.systolic_blood_pressure["target"] = 85
            self.diastolic_blood_pressure["target"] = 55

        if self.episode["type"] == "shock":
            self.systolic_blood_pressure["target"] = 70
            self.diastolic_blood_pressure["target"] = 45

        self.systolic_blood_pressure["value"] += (
            (self.systolic_blood_pressure["target"] - self.systolic_blood_pressure["value"]) * 0.1
            + random.gauss(0, 0.6)
        )

        self.diastolic_blood_pressure["value"] += (
            (self.diastolic_blood_pressure["target"] - self.diastolic_blood_pressure["value"]) * 0.1
            + random.gauss(0, 0.4)
        )

        self.episode["duration"] -= 1

        if self.episode["duration"] <= 0:
            self.episode["type"] = None

    def _final_clamp(self):

        self.heart_rate["value"] = self._clamp(self.heart_rate["value"], 40, 160)
        self.oxygen_saturation["value"] = self._clamp(self.oxygen_saturation["value"], 75, 100)
        self.respiration_rate["value"] = self._clamp(self.respiration_rate["value"], 4, 60)
        self.systolic_blood_pressure["value"] = self._clamp(self.systolic_blood_pressure["value"], 55, 190)
        self.diastolic_blood_pressure["value"] = self._clamp(self.diastolic_blood_pressure["value"], 35, 120)

    @staticmethod
    def _clamp(x, lo, hi):
        return max(lo, min(hi, x))

    @staticmethod
    def _initialize_random_base(min_val: float, max_val: float):

        base = random.uniform(min_val, max_val)

        return {
            "base": base,
            "target": base,
            "value": base
        }

    def get_id(self):
        return self.patient_id

    def get_heart_rate(self):
        return self.heart_rate["value"]

    def get_oxygen_saturation(self):
        return self.oxygen_saturation["value"]

    def get_respiratory_rate(self):
        return self.respiration_rate["value"]

    def get_systolic_blood_pressure(self):
        return self.systolic_blood_pressure["value"]

    def get_diastolic_blood_pressure(self):
        return self.diastolic_blood_pressure["value"]