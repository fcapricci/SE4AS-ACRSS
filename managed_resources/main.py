import time
import os
from patient import Patient
from actuators.oxygen_flow_regulator import OxygenFlowRegulator
from actuators.beta_blocking_regulator import BetaBlockingRegulator
from actuators.fluids_regulator import FluidsRegulator

PATIENTS_NUMBER = int(os.getenv("PATIENTS_NUMBER", 1))

patients = []

for pid in range(1, PATIENTS_NUMBER + 1):

    patient = Patient(pid)

    # Creazione attuatori associati
    OxygenFlowRegulator(patient)
    BetaBlockingRegulator(patient)
    FluidsRegulator(patient)

    patients.append(patient)

while True:
    for patient in patients:
        patient.step()
        #patient.publish_sensors(client)

    time.sleep(1)
