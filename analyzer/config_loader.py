import configparser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "clinical_rules.ini"

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

CLINICAL_RULES = config
