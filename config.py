"""
Loads and validates all configuration from environment variables (.env file).
Nothing here is hardcoded — edit your .env file to change behavior.
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()


def _get(key, default=None, required=False):
    val = os.getenv(key, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def _get_list(key, default=""):
    raw = _get(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


def _get_json(key, default="{}"):
    raw = _get(key, default)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in {key}: {e}")


# ---------------- Telegram ----------------
TELEGRAM_API_ID = int(_get("TELEGRAM_API_ID", required=True))
TELEGRAM_API_HASH = _get("TELEGRAM_API_HASH", required=True)
TELEGRAM_PHONE = _get("TELEGRAM_PHONE", required=True)
TELEGRAM_SESSION_NAME = _get("TELEGRAM_SESSION_NAME", "forex_signal_session")
TELEGRAM_CHANNELS = _get_list("TELEGRAM_CHANNELS")
CHANNEL_SYMBOL_MAP = _get_json("CHANNEL_SYMBOL_MAP")

# ---------------- MetaApi ----------------
METAAPI_TOKEN = _get("METAAPI_TOKEN", required=True)
METAAPI_ACCOUNT_ID = _get("METAAPI_ACCOUNT_ID", required=True)

# ---------------- Trading ----------------
LOT_SIZE_PER_TP = float(_get("LOT_SIZE_PER_TP", "0.05"))
ALLOWED_SYMBOLS = _get_list("ALLOWED_SYMBOLS")  # empty list = allow all

# ---------------- Risk management ----------------
MAX_DAILY_DRAWDOWN_USD = float(_get("MAX_DAILY_DRAWDOWN_USD", "2500"))
MAX_TOTAL_DRAWDOWN_USD = float(_get("MAX_TOTAL_DRAWDOWN_USD", "4000"))
DRAWDOWN_RESET_TIMEZONE = _get("DRAWDOWN_RESET_TIMEZONE", "UTC")

# ---------------- Database ----------------
MONGODB_URI = _get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = _get("MONGODB_DB_NAME", "forex_signal_bot")

# ---------------- Misc ----------------
LOG_LEVEL = _get("LOG_LEVEL", "INFO")
