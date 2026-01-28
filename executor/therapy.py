class Therapy:

    def __init__(self, patient_id : int, oxygen: int, fluids : str, beta_blocking : int, alert : bool):
        
        self.patient_id = patient_id
        self.oxygen = oxygen
        self.fluids = fluids
        self.beta_blocking = beta_blocking
        self.alert = alert

    #
    # Getters
    #

    def get_patient_id(self) -> int:
        return self.patient_id
    
    def get_oxygen(self) -> int:
        return self.oxygen
    
    def get_fluids(self) -> str:
        return self.fluids
    
    def get_beta_blocking(self) -> int:
        return self.beta_blocking
    
    def get_alert(self) -> bool:
        return self.alert
        