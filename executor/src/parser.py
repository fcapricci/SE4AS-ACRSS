from os import getenv

from models.therapy import Therapy

class Parser:

    OXYGEN_ACTUATOR = getenv("OXYGEN_ACTUATOR_NAME")
    FLUIDS_ACTUATOR = getenv("FLUIDS_ACTUATOR_NAME")
    BETA_BLOCKING_ACTUATOR = getenv("BETA_BLOCKING_ACTUATOR_NAME")
    ALERT_ACTUATOR = getenv("ALERT_ACTUATOR_NAME")

    @classmethod
    def define_actuators_actions(cls, therapy : Therapy) -> dict[str, float | str | None]:

        # {"actuator":"actionToBeDone"}
        return {
            cls.OXYGEN_ACTUATOR : therapy.get_oxygen(),
            cls.FLUIDS_ACTUATOR : therapy.get_fluids(),
            cls.BETA_BLOCKING_ACTUATOR : therapy.get_beta_blocking(),
            cls.ALERT_ACTUATOR : therapy.get_alert()
        }

