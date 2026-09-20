"""
Listens to the configured Telegram channels using your PERSONAL Telegram
account (via Telethon), not a bot account — this is required because most
signal channels only allow members to read messages, and a bot can't join
a channel it isn't added to as admin.

First run will ask for a login code sent to your Telegram app (one-time).
After that, a session file is saved so it won't ask again.
"""
from telethon import TelegramClient, events
import config
import signal_parser
import db
from logger_setup import get_logger

log = get_logger("telegram_listener")


class SignalListener:
    def __init__(self, on_signal_callback):
        """
        on_signal_callback: async function(signal: dict, symbol: str, signal_id) -> None
        """
        self.client = TelegramClient(
            f"sessions/{config.TELEGRAM_SESSION_NAME}",
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
        )
        self.on_signal_callback = on_signal_callback

    async def start(self):
        await self.client.start(phone=config.TELEGRAM_PHONE)
        log.info("Telegram client connected as personal account.")

        if not config.TELEGRAM_CHANNELS:
            log.warning("No TELEGRAM_CHANNELS configured — bot will not listen to anything.")
            return

        channel_entities = []
        for username in config.TELEGRAM_CHANNELS:
            try:
                entity = await self.client.get_entity(username)
                channel_entities.append(entity)
                log.info("Subscribed to channel: %s", username)
            except Exception as e:
                log.error("Could not find/join channel '%s': %s", username, e)

        if not channel_entities:
            log.error("No valid channels resolved — check TELEGRAM_CHANNELS in .env")
            return

        @self.client.on(events.NewMessage(chats=channel_entities))
        async def handler(event):
            await self._handle_message(event)

        log.info("Listening for new signals on %d channel(s)...", len(channel_entities))
        await self.client.run_until_disconnected()

    async def _handle_message(self, event):
        text = event.raw_text or ""
        channel_username = event.chat.username if event.chat else "unknown"

        parsed = signal_parser.parse_signal(text)

        if parsed is None:
            db.save_signal(text, channel_username, {}, accepted=False, reason="not a valid signal format")
            return  # silently ignore non-signal messages (disclaimers, chit-chat, etc.)

        symbol = config.CHANNEL_SYMBOL_MAP.get(channel_username)
        if not symbol:
            log.warning("No symbol mapped for channel '%s' — add it to CHANNEL_SYMBOL_MAP in .env", channel_username)
            db.save_signal(text, channel_username, parsed, accepted=False, reason="no symbol mapping")
            return

        log.info("New signal from %s: %s %s entry=%.2f sl=%.2f tps=%s",
                  channel_username, symbol, parsed["direction"], parsed["entry"], parsed["sl"],
                  parsed["take_profits"])

        signal_id = db.save_signal(text, channel_username, parsed, accepted=True)
        await self.on_signal_callback(parsed, symbol, signal_id)
