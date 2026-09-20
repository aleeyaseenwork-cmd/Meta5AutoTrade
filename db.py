"""
MongoDB access layer. Three collections:
  - signals: every parsed signal received (audit trail)
  - trades: every order the bot actually placed
  - risk_state: single document tracking daily drawdown / pause state
"""
from datetime import datetime, timezone
from pymongo import MongoClient
import config
from logger_setup import get_logger

log = get_logger("db")

_client = MongoClient(config.MONGODB_URI)
_db = _client[config.MONGODB_DB_NAME]

signals_col = _db["signals"]
trades_col = _db["trades"]
risk_state_col = _db["risk_state"]

RISK_STATE_ID = "singleton"  # only one risk-state document ever exists


def save_signal(raw_text: str, channel: str, parsed: dict, accepted: bool, reason: str = ""):
    doc = {
        "channel": channel,
        "raw_text": raw_text,
        "parsed": parsed,
        "accepted": accepted,
        "reason": reason,
        "received_at": datetime.now(timezone.utc),
    }
    result = signals_col.insert_one(doc)
    return result.inserted_id


def save_trade(signal_id, symbol, order_type, volume, entry, sl, tp, order_result: dict, success: bool):
    doc = {
        "signal_id": signal_id,
        "symbol": symbol,
        "order_type": order_type,
        "volume": volume,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "success": success,
        "broker_response": order_result,
        "placed_at": datetime.now(timezone.utc),
    }
    trades_col.insert_one(doc)


def get_risk_state():
    doc = risk_state_col.find_one({"_id": RISK_STATE_ID})
    if doc is None:
        doc = {
            "_id": RISK_STATE_ID,
            "daily_start_balance": None,
            "daily_reset_date": None,  # ISO date string, in configured timezone
            "trading_paused_until_next_day": False,
            "hard_stopped": False,
            "hard_stop_reason": "",
        }
        risk_state_col.insert_one(doc)
    return doc


def update_risk_state(update: dict):
    risk_state_col.update_one({"_id": RISK_STATE_ID}, {"$set": update}, upsert=True)
