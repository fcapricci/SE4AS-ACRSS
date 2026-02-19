class Therapy:

    def __init__(self, oxygen: float, fluids : str | None, beta_blocking : float, alert : str | None):

        self.oxygen = oxygen
        self.fluids = fluids
        self.beta_blocking = beta_blocking
        self.alert = alert

    #
    # Getters
    #
    
    def get_oxygen(self) -> float:
        return self.oxygen
    
    def get_fluids(self) -> str | None:
        return self.fluids
    
    def get_beta_blocking(self) -> float:
        return self.beta_blocking
    
    def get_alert(self) -> str | None:
        return self.alert
    
    #
    # Setters
    #
    
    def set_oxygen(self, oxygen : float) -> None:
        self.oxygen = oxygen

    def set_fluids(self, fluids : str | None) -> None:
        self.fluids = fluids

    def set_beta_blocking(self, beta_blocking : float) -> None:
        self.beta_blocking = beta_blocking

    def set_alert(self, alert : str | None) -> None:
        self.alert = alert