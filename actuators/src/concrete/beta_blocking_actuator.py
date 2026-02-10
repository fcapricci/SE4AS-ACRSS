from actuator import Actuator

from os import getenv

ACTUATOR_NAME = getenv("BETA_BLOCKING_ACTUATOR_NAME")
FLOW_RATE_UNIT = getenv("BETA_BLOCKING_FLOW_RATE_UNIT")


class BetaBlockingActuator(Actuator):

    def __init__(self, patient_id):
        super().__init__(
            patient_id,
            ACTUATOR_NAME
        )
        self.flow_rate_unit = FLOW_RATE_UNIT

    def _activate(self, flow_rate : float):
        
        if not flow_rate is None:
            print(
                f"[{self.username.upper()}]: Set beta-blocking flow rate to {flow_rate} {self.flow_rate_unit}."
            )