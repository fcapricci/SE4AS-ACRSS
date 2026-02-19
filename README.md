# Autonomous Cardio-Respiratory Stabilization System

## Requirements

- Docker
- Docker Compose

---

## Setup and Execution

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-root>
```

### 2. Create the .env file

After cloning the repository, create a .env file in the project root directory with the following content:

```bash
# SIMULATION 
PATIENTS_NUMBER=2 
PATIENT_SIMULATION_TIMESTEP=1

# SYSTEM
PYTHONUNBUFFERED=1

# SENSORS
HEART_RATE_SENSOR_NAME=hr
HEART_RATE_MEASURE_UNIT=bpm

OXYGEN_SATURATION_SENSOR_NAME=spo2
OXYGEN_SATURATION_MEASUREMENT_UNIT=%

RESPIRATORY_RATE_SENSOR_NAME=rr
RESPIRATORY_RATE_MEASUREMENT_UNIT=breaths/min

BLOOD_PRESSURE_SENSOR_NAME=bp
BLOOD_PRESSURE_MEASUREMENT_UNIT=mmHg

# BROKER 
MQTT_HOSTNAME=mosquitto 
MQTT_PORT=1883

MQTT_USER=utente 
MQTT_PASSWORD=password 
MQTT_CLIENT_KEEPALIVE=180

SENSORS_TOPIC_PREFIX=acrss/sensors
THERAPIES_TOPICS_PREFIX=acrss/therapies 
SYMPTOMS_TOPICS_PREFIX=acrss/symptoms
ACTIONS_TOPICS_PREFIX=acrss/actions

# KNOWLEDGE
INFLUX_URL=http://influxdb:8086 
INFLUX_ORG=acrss 
INFLUX_BUCKET=acrss 

DOCKER_INFLUXDB_INIT_PASSWORD=adminadmin 
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=acrss-super-token 

INFLUX_TOKEN=acrss-super-token 

# ACTUATORS
OXYGEN_ACTUATOR_NAME=oxygen_flow_regulator 
OXYGEN_FLOW_RATE_UNIT=L/min

FLUIDS_ACTUATOR_NAME=drip_valve
FLUIDS_ADMINISTRATION_RATE=3

BETA_BLOCKING_ACTUATOR_NAME=beta_blocking_infusion_pump 
BETA_BLOCKING_FLOW_RATE_UNIT=ug/min

ALERT_ACTUATOR_NAME=alert_server
TELEGRAM_TOKEN=8458510312:AAFgcKYmvDqk6gj8xI55lpcynFmudzdvYTA 
TELEGRAM_CHATID=-5200673556
```

### 3. Start the system

From the root directory of the project, run:

```bash
docker compose up --build
```

Docker Compose will build and start all services required for the ACRSS monitoring system.
