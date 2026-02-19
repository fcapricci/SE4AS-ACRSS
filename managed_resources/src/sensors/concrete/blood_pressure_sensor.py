from os import getenv

from sensors.sensor import Sensor

from patient import Patient

BLOOD_PRESSURE_SENSOR_NAME = getenv("BLOOD_PRESSURE_SENSOR_NAME")
BLOOD_PRESSURE_MEASUREMENT_UNIT = getenv("BLOOD_PRESSURE_MEASUREMENT_UNIT")

class BloodPressureSensor(Sensor):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            BLOOD_PRESSURE_SENSOR_NAME, 
            BLOOD_PRESSURE_MEASUREMENT_UNIT
        )

    def sense(self) -> None:
        self.data : dict[str, int] = {
            "sbp" : int(round(self.patient.get_systolic_blood_pressure())),
            "dbp" : int(round(self.patient.get_diastolic_blood_pressure()))
        }