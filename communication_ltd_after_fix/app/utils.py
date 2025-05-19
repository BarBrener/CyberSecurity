import hashlib
import hmac
import os
import re
import json

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def generate_salt(length=16):
    return os.urandom(length).hex()

def hash_password(password: str, salt: str):
    return hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()

def validate_password(password: str) -> bool:
    config = load_config()
    min_length = config.get("min_length", 10)
    require_upper = config.get("require_upper", True)
    require_lower = config.get("require_lower", True)
    require_digit = config.get("require_digit", True)
    require_special = config.get("require_special", True)

    if len(password) < min_length:
        return False

    if require_upper and not re.search(r"[A-Z]", password):
        return False
    if require_lower and not re.search(r"[a-z]", password):
        return False
    if require_digit and not re.search(r"[0-9]", password):
        return False
    if require_special and not re.search(r"[\W_]", password):
        return False

    return True
