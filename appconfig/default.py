import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# log directory
LOG_DIR = "logs"
LOG_FILE = "scheduler.log"
LOG_PATH = os.path.join(BASE_DIR, LOG_DIR, LOG_FILE)
os.makedirs(LOG_DIR, exist_ok=True)
