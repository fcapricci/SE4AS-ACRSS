from os import getenv

from actuators.actuator import Actuator

from patient import Patient

ACTUATOR_NAME : str = getenv("OXYGEN_ACTUATOR_NAME")
FLOW_RATE_UNIT : str = getenv("OXYGEN_FLOW_RATE_UNIT")


class OxygenActuator(Actuator):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            ACTUATOR_NAME
        )
        self.flow_rate_unit = FLOW_RATE_UNIT

    def _activate(self, flow_rate : float) -> None:

        if flow_rate is not None:
            self.patient.therapy.set_oxygen(
                float(flow_rate)
            )
            print(
                f"[{self.username.upper()}]: Set oxygen flow rate to {flow_rate} {self.flow_rate_unit}."
            )
