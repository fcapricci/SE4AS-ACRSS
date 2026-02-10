from os import getenv
from threading import Event

from concrete.oxygen_actuator import OxygenActuator
from concrete.fluids_actuator import FluidsActuator
from concrete.beta_blocking_actuator import BetaBlockingActuator
from concrete.alert_actuator import AlertActuator

# Get number of patients being simulated.
PATIENTS_NUMBER : int = int(getenv("PATIENTS_NUMBER"))

# Create a set of actuators for each patient.
print(f"[ACTUATORS]: Creating set of actuators for each of {PATIENTS_NUMBER} patients...")

actuators_by_patient : dict[int, tuple[
    OxygenActuator,
    FluidsActuator,
    BetaBlockingActuator,
    AlertActuator
]] = {}

for patient_id in range(1, PATIENTS_NUMBER + 1):

    print(f"[ACTUATORS]: Creating actuators for patient {patient_id}...")
    actuators_by_patient[patient_id] = [
        OxygenActuator(patient_id),
        FluidsActuator(patient_id),
        BetaBlockingActuator(patient_id),
        AlertActuator(patient_id)
    ]

# Create stop event to use non-blocking connections
# without exiting main thread.
stop_event : Event = Event()

# Connect actuators with MQTT broker.
for patient in actuators_by_patient.keys():

    print(f"[ACTUATORS]: Connecting actuators for patient {patient}...")
    for actuator in actuators_by_patient[patient]:
        actuator.connect()

# Wait indefinitely to keep thread alive.
stop_event.wait()