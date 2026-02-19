from os import getenv

from actuators.actuator import Actuator

from patient import Patient

ACTUATOR_NAME = getenv("BETA_BLOCKING_ACTUATOR_NAME")
FLOW_RATE_UNIT = getenv("BETA_BLOCKING_FLOW_RATE_UNIT")

class BetaBlockingActuator(Actuator):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            ACTUATOR_NAME
        )
        self.flow_rate_unit = FLOW_RATE_UNIT

    def _activate(self, flow_rate : float):
        
        if flow_rate is not None:
            self.patient.therapy.set_beta_blocking(
                float(flow_rate)
            )
            print(
                f"[{self.username.upper()}]: Set beta-blocking flow rate to {flow_rate} {self.flow_rate_unit}."
            )