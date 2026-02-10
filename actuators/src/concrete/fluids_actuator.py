from actuator import Actuator

from os import getenv

ACTUATOR_NAME : str = getenv("FLUIDS_ACTUATOR_NAME")

class FluidsActuator(Actuator):

    def __init__(self, patient_id):
        super().__init__(
            patient_id,
            ACTUATOR_NAME
        )

    def _activate(self, fluid : str) -> None:

        if fluid is None:
            print(
                f"[{self.username.upper()}]: Closed."
            )
            return
        
        print(
            f"[{self.username.upper()}]: Opened. Releasing {fluid}..."
        )