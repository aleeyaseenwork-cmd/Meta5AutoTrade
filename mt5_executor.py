"""
Handles the MetaApi connection and places trades on MT5.

For each signal, one market order is placed PER take-profit level (so a
signal with 4 TPs = 4 separate positions, each LOT_SIZE_PER_TP volume,
same SL, each targeting a different TP). This lets each TP close its own
slice of the trade independently — the standard way to handle multi-TP
signals.
"""
from metaapi_cloud_sdk import MetaApi
import config
import db
import risk_manager
from logger_setup import get_logger

log = get_logger("mt5_executor")


class MT5Executor:
    def __init__(self):
        self.api = MetaApi(config.METAAPI_TOKEN)
        self.account = None
        self.connection = None

    async def connect(self):
        log.info("Connecting to MetaApi account %s ...", config.METAAPI_ACCOUNT_ID)
        self.account = await self.api.metatrader_account_api.get_account(config.METAAPI_ACCOUNT_ID)

        if self.account.state not in ("DEPLOYED",):
            log.info("Account not deployed yet — deploying now...")
            await self.account.deploy()

        log.info("Waiting for account to connect to broker...")
        await self.account.wait_connected()

        self.connection = self.account.get_rpc_connection()
        await self.connection.connect()
        await self.connection.wait_synchronized()
        log.info("MT5 connection established and synchronized.")

    async def get_account_metrics(self) -> dict:
        info = await self.connection.get_account_information()
        return {"balance": info["balance"], "equity": info["equity"]}

    async def execute_signal(self, signal: dict, symbol: str, signal_id):
        """
        signal: output of signal_parser.parse_signal()
        symbol: MT5 symbol to trade, e.g. "XAUUSD"
        """
        if config.ALLOWED_SYMBOLS and symbol not in config.ALLOWED_SYMBOLS:
            log.warning("Symbol %s not in ALLOWED_SYMBOLS — skipping signal.", symbol)
            db.save_trade(signal_id, symbol, signal["direction"], 0, signal["entry"],
                          signal["sl"], None, {"skipped": "symbol not allowed"}, False)
            return

        metrics = await self.get_account_metrics()
        allowed, reason = risk_manager.is_trading_allowed(metrics["balance"], metrics["equity"])
        if not allowed:
            log.warning("Trade blocked by risk manager: %s", reason)
            db.save_trade(signal_id, symbol, signal["direction"], 0, signal["entry"],
                          signal["sl"], None, {"skipped": reason}, False)
            return

        direction = signal["direction"]
        sl = signal["sl"]

        for tp in signal["take_profits"]:
            try:
                if direction == "BUY":
                    result = await self.connection.create_market_buy_order(
                        symbol, config.LOT_SIZE_PER_TP, stop_loss=sl, take_profit=tp
                    )
                else:
                    result = await self.connection.create_market_sell_order(
                        symbol, config.LOT_SIZE_PER_TP, stop_loss=sl, take_profit=tp
                    )
                log.info("Order placed: %s %s vol=%.2f SL=%.2f TP=%.2f -> %s",
                          direction, symbol, config.LOT_SIZE_PER_TP, sl, tp, result)
                db.save_trade(signal_id, symbol, direction, config.LOT_SIZE_PER_TP,
                              signal["entry"], sl, tp, result, True)
            except Exception as e:
                log.error("Order FAILED: %s %s TP=%.2f -> %s", direction, symbol, tp, e)
                db.save_trade(signal_id, symbol, direction, config.LOT_SIZE_PER_TP,
                              signal["entry"], sl, tp, {"error": str(e)}, False)
