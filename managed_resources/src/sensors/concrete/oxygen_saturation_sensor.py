from os import getenv

from sensors.sensor import Sensor

from patient import Patient

OXYGEN_SATURATION_SENSOR_NAME = getenv("OXYGEN_SATURATION_SENSOR_NAME")
OXYGEN_SATURATION_MEASUREMENT_UNIT = getenv("OXYGEN_SATURATION_MEASUREMENT_UNIT")

class OxygenSaturationSensor(Sensor):

    def __init__(self, patient : Patient):

        super().__init__(
            patient,
            OXYGEN_SATURATION_SENSOR_NAME,
            OXYGEN_SATURATION_MEASUREMENT_UNIT
        )

    def sense(self) -> None:
        self.data : int = int(round(self.patient.get_oxygen_saturation()))