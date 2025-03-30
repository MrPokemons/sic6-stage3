import json
import os


def load_config():
    with open(os.getenv("ENV_FILE"), "r") as f:
        config = json.load(f)
    return config
