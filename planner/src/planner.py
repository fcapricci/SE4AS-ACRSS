
from datetime import datetime
import copy

class Planner():
    def __init__(self):
        self.therapy = {
            'ox_therapy': 0, 
            'fluids': None, 
            'carvedilolo_beta_blocking': 0,
            'improve_beta_blocking': 0,
            'alert': set(),
            'timestamp': None
        } 
        self.dt_incr = 5 # seconds per day
        self.MAX_NON_INVASIVE_OX_THERAPY = 6
        self.STARTING_BB_DOSE = 1.25
        self.INCR_BB_DOSE = 0.25
        self.ox_active_therapy = None
        self.bb_stopped_therapy = {
                                    'carvedilolo_beta_blocking': 0,
                                    'improve_beta_blocking': 0
                                }
        self.last_bb_incr = None 
        self.beta_blocking_target_dose = 10
    def restart_beta_blocking(self):
            self.therapy['carvedilolo_beta_blocking'] = self.bb_stopped_therapy['carvedilolo_beta_blocking'] 
            self.therapy['improve_beta_blocking'] = self.bb_stopped_therapy['improve_beta_blocking']
            self.bb_stopped_therapy['carvedilolo_beta_blocking'] = 0
            self.bb_stopped_therapy['improve_beta_blocking'] = 0
    def stop_beta_blocking(self):
                self.bb_stopped_therapy['carvedilolo_beta_blocking'] = self.therapy['carvedilolo_beta_blocking']
                self.bb_stopped_therapy['improve_beta_blocking'] = self.therapy['improve_beta_blocking']
                self.therapy['carvedilolo_beta_blocking'] = 0
                self.therapy['improve_beta_blocking'] = 0
                self.therapy['carvedilolo_beta_blocking'] = 0
                self.therapy['improve_beta_blocking'] = 0
    def handle_beta_blocking(self, patient_state):
        status = patient_state.get('status', {})
        if status.get('blood_pressure') == 'SHOCK':
            if self.therapy['carvedilolo_beta_blocking'] != 0 :
                self.stop_beta_blocking()
                #print('ARBITRATION: BETA_BLOCKERS_BLOCKED_SHOCK')
        elif self.bb_stopped_therapy['carvedilolo_beta_blocking'] > 0 :
            self.restart_beta_blocking()
            #print("beta bloccante riattivato")
        if status.get('oxigenation') == 'GRAVE_HYPOXIA':
            if self.therapy['carvedilolo_beta_blocking'] !=0:
                #print('ARBITRATION: BETA_BLOCKERS_BLOCKED_GRAVE_HYPOXIA')
                self.stop_beta_blocking()
        elif self.bb_stopped_therapy['carvedilolo_beta_blocking'] > 0 :
            self.restart_beta_blocking()
            #print("beta bloccante riattivato")
        if status.get('respiration') == 'BRADYPNEA' and self.therapy['carvedilolo_beta_blocking'] != 0:
            self.stop_beta_blocking()
            #print('ARBITRATION: BETA_BLOCKERS_FORBIDDEN_BRADYPNEA')
        elif status.get('respiration') != 'BRADYPNEA' and self.bb_stopped_therapy['carvedilolo_beta_blocking'] != 0:
            self.restart_beta_blocking()
    def fluids_escalation(self,patient_state):
        fluid_val = self.therapy['fluids']
        status = patient_state['status']
        trend = patient_state['trend']
        intensity = patient_state['intensity']
        if fluid_val is not None:
            if status['blood_pressure'] != 'CIRCULARITY_UNSTABILITY' and status['blood_pressure'] != 'MODERATE_HYPOTENSION' and (status['blood_pressure'] != 'SHOCK'):
                #print(f"1 BLOOD_PRESSURE = {status['blood_pressure']} STABILIZATED -> STOP FLUIDS")
                self.therapy['fluids'] = None
            else:
                if status['blood_pressure'] == 'MODERATE_HYPOTENSION' and trend['map'] not in ['STABLE','DETERIORING']:
                    #print(f"3 BLOOD_PRESSURE = {status['blood_pressure']} STABILIZATED -> STOP FLUIDS")
                    self.therapy['fluids'] = None
                elif status['blood_pressure'] == 'SHOCK' and trend['map'] != 'IMPROVING':
                    #print(f"3 BLOOD_PRESSURE IN DECREASING {status['blood_pressure']} STATE -> STOP FLUIDS")
                    self.therapy['fluids'] = None
                """elif trend['map'] == 'DETERIORING' and intensity['map'] not in ['MODERATE_DECREASE', 'STRONG_DECREASE']:
                    print(f"4 BLOOD_PRESSURE = {status['blood_pressure']} STABILIZATED -> STOP FLUIDS")
                    self.therapy['fluids'] = None"""

    def stop_fluids(self, patient_state):
        status = patient_state.get('status', {})

        if status.get('respiration') == 'RESPIRATORY_DISTRESS' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            #print('ARBITRATION: FLUIDS_STOP_RESPIRATORY_DISTRESS')

        if status.get('oxigenation') == 'FAILURE_OXYGEN_THERAPY' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            #print('ARBITRATION: FLUIDS_STOP_OXYGEN_FAILURE')

        if status.get('blood_pressure') == 'DISTRESS_OVERLOAD' and self.therapy['fluids'] is not None:
            self.therapy['fluids'] = None
            #print('ARBITRATION: FLUIDS_FORBIDDEN_OVERLOAD')

    def calculate_dt(self):
        if self.last_bb_incr is None:
            self.last_bb_incr = int(datetime.now().timestamp())

        return int(datetime.now().timestamp()) - int(self.last_bb_incr) > self.dt_incr

    def ox_therapy(self, patient_state):
        pattern_decrease = "_DECREASE"
        pattern_stable = "STABLE_"
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        intensity = patient_state.get('intensity', {})
        ox_modified = False
        # Controllo se il paziente necessita di terapia dell'ossigeno
        if status['oxigenation']== "LIGHT_HYPOXIA" and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            if trend['spo2'] == 'IMPROVING':
                self.therapy['ox_therapy'] += 1
                ox_modified = True
                #print(f"Oxygen improved to {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - IMPROVING)")
            elif trend['spo2'] == 'STABLE' and (pattern_decrease in intensity['spo2']) and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
                self.therapy['ox_therapy'] += 2
                ox_modified = True
                #print(f"Oxygen improved to {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - STABLE)")
            elif trend['spo2'] == 'DETERIORING' and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
                self.therapy['ox_therapy'] += 2
                ox_modified = True
                #print(f"Oxygen improved to {self.therapy['ox_therapy']} L/min (LIGHT_HYPOXIA - DETERIORING)")
        elif status['oxigenation'] == "GRAVE_HYPOXIA" and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            self.therapy['ox_therapy'] = self.MAX_NON_INVASIVE_OX_THERAPY 
            ox_modified = True
            #print(f"OSSIGENO BOOST: {self.therapy['ox_therapy']} L/min (GRAVE_HYPOXIA)")
        elif status['oxigenation'] == "FAILURE_OXYGEN_THERAPY":
            self.therapy['alert'].add('FAILURE_OXYGEN_THERAPY' )
            ox_modified = True
            #print("ALERT: oxygen therapy failure")
        # Controllo se il paziente viene stabilizzato
        elif (pattern_stable in status['oxigenation'] and trend['spo2'] != 'DETERIORING'):
            self.therapy['ox_therapy'] = self.therapy['ox_therapy']-1 if self.therapy['ox_therapy'] > 0 else self.therapy['ox_therapy']  
            #print(f"Ossigeno diminuito a {self.therapy['ox_therapy']} L/min" if self.therapy['ox_therapy'] > 0 else "")
            ox_modified = True
        if status['respiration'] == 'MODERATE_TACHYPNEA' and trend['rr'] in ['STABLE', 'DETERIORING'] and ox_modified == False and self.therapy['ox_therapy'] < self.MAX_NON_INVASIVE_OX_THERAPY :
            if trend['rr'] == 'STABLE':
                self.therapy['ox_therapy'] +=1
                ox_modified = True
            elif trend['rr'] == 'DETERIORING' and pattern_decrease in intensity['rr']:
                 self.therapy['ox_therapy'] +=2
                 ox_modified = True
        elif status['respiration'] == 'RESPIRATORY_DISTRESS':
            self.therapy['alert'].add('RESPIRATORY_DISTRESS')
            #print("ALERT: RESPIRATORY_DISTRESS - fluidi sospesi")
        elif status['respiration'] == 'BRADYPNEA':
            self.therapy['alert'].add('BRADYPNEA')

        if status['heart_rate'] == 'COMPENSED_TACHYCARDIA' and ox_modified == False:
            if trend['hr'] == 'STABLE':
                self.therapy['ox_therapy'] +=1
            elif trend['hr'] == 'DETERIORING' and intensity['hr']== 'STRONG_DECREASE':
                self.therapy['ox_therapy'] +=1
        elif (pattern_stable in status['oxigenation'] and trend['spo2'] != 'DETERIORING') and self.therapy['ox_therapy'] > 0 and ox_modified == False:
            #print(f"Ossigeno diminuito a {self.therapy['ox_therapy']} L/min. COMPENSED_TACHYCARDIA stabilizzata" if self.therapy['ox_therapy'] > 0 else "")

            self.therapy['ox_therapy'] -=1

            

    def pharmacy_therapy(self, patient_state):
        status = patient_state.get('status', {})
        trend = patient_state.get('trend', {})
        intensity = patient_state.get('intensity', {})

        # Gestione beta-bloccanti
        # Gestione decremento bb
        if status['heart_rate'] == 'STABLE_HR' and trend.get('hr') != 'IMPROVING':
            if self.therapy['improve_beta_blocking'] > 0 and self.calculate_dt():
                self.last_bb_incr = int(datetime.now().timestamp())
                self.therapy['improve_beta_blocking'] -= self.INCR_BB_DOSE
                #print(f"Beta-bloccante diminuito a {self.therapy['improve_beta_blocking']}")
            if self.therapy['improve_beta_blocking'] == 0 and self.therapy['carvedilolo_beta_blocking'] == self.STARTING_BB_DOSE:
                if self.calculate_dt():
                    self.last_bb_incr = int(datetime.now().timestamp())
                    self.therapy['carvedilolo_beta_blocking'] -= self.INCR_BB_DOSE
                    #print(f"Beta-bloccante base diminuito a {self.therapy['carvedilolo_beta_blocking']}")
        # Gestione incremento bb
        elif status['heart_rate'] == 'PRIMARY_TACHYCARDIA':
                if trend['hr'] == 'STABLE' and self.therapy['carvedilolo_beta_blocking'] == 0:
                    self.last_bb_incr = int(datetime.now().timestamp())
                    self.therapy['carvedilolo_beta_blocking'] = self.STARTING_BB_DOSE
                    #print(f"Beta-bloccante dose iniziale a {self.therapy['carvedilolo_beta_blocking']} mg (PRIMARY_TACHYCARDIA - STABLE)")
                elif trend['hr'] == 'INCREASING' and intensity['hr'] == 'STRONG_INCREASE' and (self.therapy['carvedilolo_beta_blocking'] + self.therapy['improve_beta_blocking']) <= self.beta_blocking_target_dose:
                    #print("è dentro il ramo che controlla se incrementare o aggiungere la dose base \n diff time verifica:", self.calculate_dt())
                    if self.calculate_dt():
                        self.last_bb_incr = int(datetime.now().timestamp())
                        if self.therapy['carvedilolo_beta_blocking'] == 1.25:
                            self.therapy['improve_beta_blocking'] += self.INCR_BB_DOSE
                            #print(f"Beta-bloccante aumentato a {self.therapy['improve_beta_blocking']} mg (PRIMARY_TACHYCARDIA - DETERIORATING)")
                    else:
                        self.therapy['carvedilolo_beta_blocking'] = self.STARTING_BB_DOSE

        
        # Gestione fluidi e pressione
        if status.get('blood_pressure') == 'MODERATE_HYPOTENSION':
            if trend.get('map') == 'STABLE':
                self.therapy['fluids'] = 'BOLUS'
                #print("Fluidi: BOLUS attivato (MODERATE_HYPOTENSION - STABLE)")
            elif trend.get('map') == 'DETERIORING':
                self.therapy['fluids'] = 'BOLUS'
                self.therapy['alert'].add("MODERATE_HYPOTENSION")
                #print("ALERT: Ipotensione moderata in peggioramento - BOLUS attivato")
        """elif self.therapy['fluids'] == 'BOLUS':
            self.therapy['fluids'] = None"""

        
        if status.get('blood_pressure') == 'SHOCK' and trend.get('map') != 'IMPROVING' and intensity['map'] not in ['MODERATE_INCREASE', 'STRONG_INCREASE']:
            self.therapy['alert'].add("SHOCK")
            #print("ALERT: Shock rilevato")
        if status.get('blood_pressure') == 'DISTRESS_OVERLOAD' and trend.get('spo2') == 'DETERIORING':
            self.therapy['alert'].add("DISTRESS_OVERLOAD")
            #print("ALERT: Sovraccarico + distress - fluidi STOP")
        
        if status.get('blood_pressure') == 'CIRCULARITY_UNSTABILITY':
            if trend.get('map') == 'IMPROVING':
                self.therapy['fluids'] = 'BOLUS'
                #print("Fluidi: BOLUS attivato (CIRCULARITY_UNSTABILITY - IMPROVING)")
            elif trend.get('map') in ['STABLE', 'DETERIORING'] and self.therapy['carvedilolo_beta_blocking'] == 0 and self.therapy['improve_beta_blocking'] == 0:
                self.therapy['carvedilolo_beta_blocking'] = 1.25
                self.therapy['fluids'] = 'BOLUS'
                #print(f"Beta-bloccante impostato a {self.therapy['carvedilolo_beta_blocking']} mg (CIRCULARITY_UNSTABILITY)")
        else:
            """if self.therapy['fluids'] == 'BOLUS':
                self.therapy['fluids'] = None
                print("Fluidi: BOLUS disattivato (CIRCULARITY_UNSTABILITY -> STABILIZED)")"""
            if self.therapy['improve_beta_blocking'] > 0:
                self.therapy['improve_beta_blocking']-=self.INCR_BB_DOSE
                #print("Beta bloccante decreasing scaling: (CIRCULARITY_UNSTABILITY -> STABILIZED)")
            elif self.therapy['carvedilolo_beta_blocking'] >0:
                self.therapy['carvedilolo_beta_blocking']-=self.INCR_BB_DOSE


    def get_serializable_therapy(self):
        therapy = copy.deepcopy(self.therapy)
        therapy['carvedilolo_beta_blocking']+= therapy['improve_beta_blocking']
        therapy.pop('improve_beta_blocking')
        therapy['alert'] = list(therapy['alert'])
        return therapy
