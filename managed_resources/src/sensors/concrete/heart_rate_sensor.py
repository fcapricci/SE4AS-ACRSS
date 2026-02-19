from os import getenv

from sensors.sensor import Sensor

from patient import Patient

HEART_RATE_SENSOR_NAME = getenv("HEART_RATE_SENSOR_NAME")
HEART_RATE_MEASURE_UNIT = getenv("HEART_RATE_MEASURE_UNIT")

class HeartRateSensor(Sensor):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            HEART_RATE_SENSOR_NAME,
            HEART_RATE_MEASURE_UNIT
        )

    def sense(self) -> None:
        self.data : int = int(round(self.patient.get_heart_rate()))