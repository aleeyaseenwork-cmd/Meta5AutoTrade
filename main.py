"""
Entry point. Run with:   python main.py

Flow:
  1. Connect to MT5 via MetaApi
  2. Start listening to Telegram channels
  3. On each valid signal -> risk check -> place trades -> log to MongoDB
"""
import asyncio
from mt5_executor import MT5Executor
from telegram_listener import SignalListener
from logger_setup import get_logger

log = get_logger("main")


async def main():
    executor = MT5Executor()
    await executor.connect()

    async def handle_signal(signal, symbol, signal_id):
        await executor.execute_signal(signal, symbol, signal_id)

    listener = SignalListener(on_signal_callback=handle_signal)
    await listener.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped manually.")
    except Exception as e:
        log.exception("Fatal error, bot crashed: %s", e)
