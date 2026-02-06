from datetime import datetime
from typing import Dict
from planner import Planner


class PlannerManager:
    """
    Gestisce un'istanza di Planner per ogni paziente.
    Garantisce stato clinico persistente e isolamento per patient_id.
    """

    _planners: Dict[str, Planner] = {}

    @classmethod
    def get_planner(cls, patient_id: str) -> Planner:
        """
        Ritorna il planner associato al paziente.
        Se non esiste, lo crea.
        """
        if patient_id not in cls._planners:
            print(f"[PLANNER_MANAGER] Creating planner for patient {patient_id}")
            cls._planners[patient_id] = Planner()
        return cls._planners[patient_id]

    @classmethod
    def process_symptoms(cls, patient_id: str, patient_state: dict) -> dict:
        """
        Applica la logica clinica al paziente e restituisce
        la terapia serializzabile pronta per MQTT.
        """
        planner = cls.get_planner(patient_id)

        # ---- LOGICA CLINICA ----
        planner.handle_beta_blocking(patient_state)
        planner.stop_fluids(patient_state)
        planner.fluids_escalation(patient_state)
        planner.ox_therapy(patient_state)
        planner.pharmacy_therapy(patient_state)

        therapy = planner.get_serializable_therapy()
        therapy["timestamp"] = datetime.utcnow().isoformat()

        return therapy

