from os import getenv

from actuators.actuator import Actuator

from patient import Patient

ACTUATOR_NAME : str = getenv("FLUIDS_ACTUATOR_NAME")

class FluidsActuator(Actuator):

    def __init__(self, patient : Patient):
        super().__init__(
            patient,
            ACTUATOR_NAME
        )

    def _activate(self, fluid : str) -> None:

        self.patient.therapy.set_fluids(
            str(fluid)
        )
        if fluid is None:
            print(
                f"[{self.username.upper()}]: Closed."
            )
            return
        
        print(
            f"[{self.username.upper()}]: Opened. Releasing {fluid}..."
        )