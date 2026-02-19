from os import getenv

from actuators.actuator import Actuator

from patient import Patient

ACTUATOR_NAME = getenv("ALERT_ACTUATOR_NAME")

class AlertActuator(Actuator):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            ACTUATOR_NAME
        )
    
    def _activate(self, alert : str):
        
        if not alert is None:
            self.patient.therapy.set_alert(alert)
            print(
                f"[{self.username.upper()}]: Notified medical team of emergency with alert: {alert}."
            )