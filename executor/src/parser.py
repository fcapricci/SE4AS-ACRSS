from therapy import Therapy

class Parser:

    OXYGEN_ACTUATOR = "oxygen_flow_regulator"
    FLUIDS_ACTUATOR = "drip_valve"
    BETA_BLOCKING_ACTUATOR = "beta_blocking_infusion_pump"
    ALERT_ACTUATOR = "alert"

    @classmethod
    def define_actuators_actions(cls, therapy : Therapy) -> dict[str, float | str | None]:

        # Parse actuators actions from therapy object
        print("[EXECUTOR]: Defining actuators actions based on given therapy...")

        # {"actuatorType":"actionToBeDone"}
        return {
            cls.OXYGEN_ACTUATOR : therapy.get_oxygen(),
            cls.FLUIDS_ACTUATOR : therapy.get_fluids(),
            cls.BETA_BLOCKING_ACTUATOR : therapy.get_beta_blocking(),
            cls.ALERT_ACTUATOR : therapy.get_alert()
        }

