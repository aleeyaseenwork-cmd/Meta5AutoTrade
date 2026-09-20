# Telegram → MT5 Signal Copier Bot

Reads trade signals from Telegram channels and auto-executes them on MT5
via MetaApi, with prop-firm drawdown protection and MongoDB logging.

## What it does

- Listens to one or more Telegram channels (your personal account, read-only)
- Parses messages in the format: `Entry Price / TP1-4 / Stop Loss (SL)`
- Auto-detects BUY or SELL from the signal levels
- Places one order per TP level (so each TP closes independently)
- Pauses trading for the rest of the day if the daily drawdown limit is hit
  (auto-resumes the next day)
- Hard-stops permanently if the max total drawdown is hit (manual restart needed)
- Logs every signal and every trade to MongoDB + a local log file

## 1. Requirements

- Python 3.10+
- MongoDB running somewhere (local install, or a free MongoDB Atlas cluster)
- A MetaApi account with your MT5 account connected (already done)
- Telegram API credentials (from https://my.telegram.org)

## 2. Install

```bash
pip install -r requirements.txt
cp .env.example .env
```

Now open `.env` and fill in every value — see comments in the file for where
to get each one. Nothing is hardcoded in the code; everything is configured
through `.env`.

## 3. First run (Telegram login)

```bash
python main.py
```

On the very first run, Telethon will ask for the login code sent to your
Telegram app, and your 2FA password if you have one enabled. After that, a
session file is saved in `sessions/` so it won't ask again — don't delete
that folder.

## 4. Adding more signal channels later

Edit `.env`:

```
TELEGRAM_CHANNELS=Education_Cycle01,SecondChannelUsername
CHANNEL_SYMBOL_MAP={"Education_Cycle01": "XAUUSD", "SecondChannelUsername": "EURUSD"}
```

Restart the bot. No code changes needed.

## 5. Adjusting risk settings

All in `.env`:

```
LOT_SIZE_PER_TP=0.05
MAX_DAILY_DRAWDOWN_USD=2500
MAX_TOTAL_DRAWDOWN_USD=4000
```

## 6. Switching from demo to the live prop-firm account later

Just update these two values in `.env` — nothing else changes:

```
METAAPI_ACCOUNT_ID=<the new MetaApi account id for the live account>
```

(Set up the new MT5 account in the MetaApi dashboard the same way the demo
was set up, then paste its account ID here.)

## 7. Running it 24/7

Use a process manager so it restarts if it crashes, for example:

```bash
pip install supervisor
# or simply run inside a `screen` / `tmux` session, or as a systemd service,
# or deploy the folder as a container on your existing server (Coolify etc.)
```

## Project structure

```
config.py            - loads all settings from .env
logger_setup.py       - console + rotating file logging
db.py                 - MongoDB (signals, trades, risk state)
signal_parser.py      - turns raw message text into a trade dict
risk_manager.py       - daily/total drawdown enforcement
mt5_executor.py        - MetaApi connection + order placement
telegram_listener.py   - watches channels, triggers on new signals
main.py                - wires it all together, run this
```

## Notes

- The bot only trades symbols listed in `ALLOWED_SYMBOLS` (safety filter) —
  leave blank in `.env` to allow any symbol.
- Every parsed and skipped signal is saved to MongoDB's `signals` collection
  for a full audit trail, even ones that didn't result in a trade.
- Deposit/API costs are billed by MetaApi directly to whoever owns the
  MetaApi account — this code has no billing logic of its own.
