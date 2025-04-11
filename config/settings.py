import json
import os
from dotenv import load_dotenv


def load_config() -> dict:
    load_dotenv()
    with open(os.getenv("ENV_FILE"), "r", encoding="utf-8") as f:
        config = json.load(f)
    return config
