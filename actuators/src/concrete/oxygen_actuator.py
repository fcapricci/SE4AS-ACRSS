from actuator import Actuator

from os import getenv

ACTUATOR_NAME : str = getenv("OXYGEN_ACTUATOR_NAME")
FLOW_RATE_UNIT : str = getenv("OXYGEN_FLOW_RATE_UNIT")


class OxygenActuator(Actuator):

    def __init__(self, patient_id):
        super().__init__(
            patient_id,
            ACTUATOR_NAME
        )
        self.flow_rate_unit = FLOW_RATE_UNIT

    def _activate(self, flow_rate : float) -> None:

        if not flow_rate is None:
            print(
                f"[{self.username.upper()}]: Set oxygen flow rate to {flow_rate} {self.flow_rate_unit}."
            )
