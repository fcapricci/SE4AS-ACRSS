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
INFLUX_TOKEN=acrss-super-token 
DOCKER_INFLUXDB_INIT_PASSWORD=adminadmin 
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=acrss-super-token 
INFLUX_URL=http://influxdb:8086 
INFLUX_ORG=acrss 
INFLUX_BUCKET=acrss 
TELEGRAM_TOKEN=8458510312:AAFgcKYmvDqk6gj8xI55lpcynFmudzdvYTA 
TELEGRAM_CHATID=-5200673556 
MQTT_USER=utente 
MQTT_PASSWORD=password 

# SIMULATION 
PATIENTS_NUMBER=2 
# BROKER 
MQTT_HOSTNAME=mosquitto 
MQTT_PORT=1883 
THERAPIES_TOPICS_PREFIX=acrss/therapies 
ACTIONS_TOPICS_PREFIX=acrss/actions 
# ACTUATORS 
OXYGEN_ACTUATOR_NAME=oxygen_flow_regulator 
OXYGEN_FLOW_RATE_UNIT=L/min 
FLUIDS_ACTUATOR_NAME=drip_valve 
BETA_BLOCKING_ACTUATOR_NAME=beta_blocking_infusion_pump 
BETA_BLOCKING_FLOW_RATE_UNIT=ug/min 
ALERT_ACTUATOR_NAME=alert_server 
PYTHONUNBUFFERED=1
```

### 3. Start the system

From the root directory of the project, run:

```bash
docker compose up --build
```
Docker Compose will build and start all services required for the ACRSS monitoring system.
