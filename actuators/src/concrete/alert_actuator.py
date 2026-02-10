from actuator import Actuator

from os import getenv

ACTUATOR_NAME = getenv("ALERT_ACTUATOR_NAME")

class AlertActuator(Actuator):

    def __init__(self, patient_id):
        super().__init__(
            patient_id,
            ACTUATOR_NAME
        )
    
    def _activate(self, alert : str):
        
        if not alert is None:
            print(
                f"[{self.username.upper()}]: Notified medical team of emergency with alert: {alert}."
            )