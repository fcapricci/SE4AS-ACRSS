from os import getenv

from sensors.sensor import Sensor

from patient import Patient

RESPIRATORY_RATE_SENSOR_NAME = getenv("RESPIRATORY_RATE_SENSOR_NAME")
RESPIRATORY_RATE_MEASUREMENT_UNIT = getenv("RESPIRATORY_RATE_MEASUREMENT_UNIT")

class RespiratoryRateSensor(Sensor):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            RESPIRATORY_RATE_SENSOR_NAME,
            RESPIRATORY_RATE_MEASUREMENT_UNIT
        )

    def sense(self) -> None:
        self.data : int = int(round(self.patient.get_respiratory_rate()))