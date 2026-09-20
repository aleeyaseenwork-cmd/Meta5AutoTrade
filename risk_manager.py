"""
Enforces the prop-firm risk rules:

  - MAX_DAILY_DRAWDOWN_USD: if today's loss (from the balance at the start of
    the day) reaches this, new trades are paused until the next day
    (auto-resumes on date change, in DRAWDOWN_RESET_TIMEZONE).

  - MAX_TOTAL_DRAWDOWN_USD: if the account's overall loss reaches this, the
    bot hard-stops completely and will NOT resume automatically — this
    matches "max loss" prop-firm rules, which are account-ending, not
    day-limited. Requires manually clearing risk_state in the DB (or fixing
    the underlying issue) to resume.

Call check_and_update(current_balance, current_equity) before every trade.
"""
from datetime import datetime
import pytz
import config
import db
from logger_setup import get_logger

log = get_logger("risk_manager")


def _today_str():
    tz = pytz.timezone(config.DRAWDOWN_RESET_TIMEZONE)
    return datetime.now(tz).date().isoformat()


def _ensure_daily_baseline(state: dict, current_balance: float) -> dict:
    """Reset the daily starting balance if a new day has begun."""
    today = _today_str()
    if state.get("daily_reset_date") != today:
        log.info("New trading day (%s) — resetting daily drawdown baseline to %.2f", today, current_balance)
        db.update_risk_state({
            "daily_start_balance": current_balance,
            "daily_reset_date": today,
            "trading_paused_until_next_day": False,
        })
        state = db.get_risk_state()
    return state


def is_trading_allowed(current_balance: float, current_equity: float) -> tuple[bool, str]:
    """
    Returns (allowed: bool, reason: str).
    Must be called before every trade attempt.
    """
    state = db.get_risk_state()

    if state.get("hard_stopped"):
        return False, f"Bot hard-stopped: {state.get('hard_stop_reason', 'max drawdown reached')}"

    state = _ensure_daily_baseline(state, current_balance)

    if state.get("trading_paused_until_next_day"):
        return False, "Daily drawdown limit already hit today — resumes automatically tomorrow"

    daily_start = state.get("daily_start_balance", current_balance)
    daily_loss = daily_start - current_equity

    if daily_loss >= config.MAX_DAILY_DRAWDOWN_USD:
        db.update_risk_state({"trading_paused_until_next_day": True})
        log.warning("Daily drawdown limit hit (loss=%.2f >= limit=%.2f). Pausing until next day.",
                    daily_loss, config.MAX_DAILY_DRAWDOWN_USD)
        return False, "Daily drawdown limit just reached — pausing until next day"

    # Total/overall loss vs an implied starting balance is broker-account specific.
    # We treat "total drawdown" as loss from the account's peak balance ever recorded.
    peak_balance = max(state.get("peak_balance", current_balance), current_balance)
    if peak_balance != state.get("peak_balance"):
        db.update_risk_state({"peak_balance": peak_balance})

    total_loss = peak_balance - current_equity
    if total_loss >= config.MAX_TOTAL_DRAWDOWN_USD:
        db.update_risk_state({
            "hard_stopped": True,
            "hard_stop_reason": f"Total drawdown {total_loss:.2f} reached max {config.MAX_TOTAL_DRAWDOWN_USD}",
        })
        log.error("MAX TOTAL DRAWDOWN REACHED (%.2f >= %.2f). Bot hard-stopping.",
                   total_loss, config.MAX_TOTAL_DRAWDOWN_USD)
        return False, "Max total drawdown reached — bot stopped, manual review required"

    return True, "ok"
