"""
Parses signal messages in this format (case-insensitive, flexible spacing):

    Entry Price: 4587
    TP1: 4583
    TP2: 4581
    TP3: 4578
    TP4: 4568
    Stop Loss (SL): 4610

Direction is inferred automatically:
  - If TP1 is BELOW entry and SL is ABOVE entry -> SELL
  - If TP1 is ABOVE entry and SL is BELOW entry -> BUY

Returns None if the message doesn't look like a valid signal (e.g. it's just
the channel's disclaimer text, a chart image caption, chit-chat, etc).
"""
import re
from logger_setup import get_logger

log = get_logger("signal_parser")

ENTRY_RE = re.compile(r"entry\s*price\s*[:\-]?\s*([\d.]+)", re.IGNORECASE)
TP_RE = re.compile(r"tp\s*(\d+)\s*[:\-]?\s*([\d.]+)", re.IGNORECASE)
SL_RE = re.compile(r"stop\s*loss.*?[:\-]?\s*([\d.]+)|(?<!t)sl\s*[:\-]?\s*([\d.]+)", re.IGNORECASE)


def parse_signal(text: str) -> dict | None:
    if not text:
        return None

    entry_match = ENTRY_RE.search(text)
    sl_match = SL_RE.search(text)
    tp_matches = TP_RE.findall(text)

    if not entry_match or not sl_match or not tp_matches:
        return None  # not a signal message, ignore silently

    try:
        entry = float(entry_match.group(1))
        sl = float(sl_match.group(1) or sl_match.group(2))
        tps = sorted(
            [(int(num), float(val)) for num, val in tp_matches],
            key=lambda x: x[0],
        )
        tp_values = [val for _, val in tps]
    except (ValueError, TypeError):
        log.warning("Failed to convert parsed numbers to float. Raw text: %s", text)
        return None

    if not tp_values:
        return None

    # Infer direction from relationship between entry, first TP, and SL
    first_tp = tp_values[0]
    if first_tp < entry and sl > entry:
        direction = "SELL"
    elif first_tp > entry and sl < entry:
        direction = "BUY"
    else:
        log.warning("Could not determine direction (inconsistent levels). Raw text: %s", text)
        return None

    return {
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "take_profits": tp_values,
    }
