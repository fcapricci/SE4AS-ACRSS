import time
import os

from patient import Patient

from sensors.concrete.heart_rate_sensor import HeartRateSensor
from sensors.concrete.oxygen_saturation_sensor import OxygenSaturationSensor
from sensors.concrete.respiratory_rate_sensor import RespiratoryRateSensor
from sensors.concrete.blood_pressure_sensor import BloodPressureSensor

from actuators.concrete.oxygen_actuator import OxygenActuator
from actuators.concrete.fluids_actuator import FluidsActuator
from actuators.concrete.beta_blocking_actuator import BetaBlockingActuator
from actuators.concrete.alert_actuator import AlertActuator

# Get number of patients being simulated
PATIENTS_NUMBER : int = int(os.getenv("PATIENTS_NUMBER"))

# Get timestep
TIMESTEP : float = float(os.getenv("PATIENT_SIMULATION_TIMESTEP"))

# Initialize patients
patients : list[Patient] = [Patient(patient_id) for patient_id in range(1, PATIENTS_NUMBER + 1)]

# Create a set of sensors for each patient
sensors_by_patient : dict[Patient, tuple[
    HeartRateSensor,
    OxygenSaturationSensor,
    RespiratoryRateSensor,
    BloodPressureSensor
]] = {}

for patient in patients:
    sensors_by_patient[patient] = [
        HeartRateSensor(patient),
        OxygenSaturationSensor(patient),
        RespiratoryRateSensor(patient),
        BloodPressureSensor(patient)
    ]


# Create set of actuators for each patient
actuators_by_patient : dict[Patient, tuple[
    OxygenActuator,
    FluidsActuator,
    BetaBlockingActuator,
    AlertActuator
]] = {}

for patient in patients:
    actuators_by_patient[patient] = [
        OxygenActuator(patient),
        FluidsActuator(patient),
        BetaBlockingActuator(patient),
        AlertActuator(patient)
    ]

# Connect sensors and actuators with MQTT broker
for patient in patients:

    for sensor in sensors_by_patient[patient]:
        sensor.connect()

    for actuator in actuators_by_patient[patient]:
        actuator.connect()

# Start patients simulation
while True:

    # Update states
    for patient in patients:
        patient.update_state()

    # Publish new sensors values
    for patient in patients:
        for sensor in sensors_by_patient[patient]:
            sensor.sense()
            sensor.publish()

    # Wait for next timestep
    time.sleep(TIMESTEP)
