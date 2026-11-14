"""Long-poll Telegram updates and run employee authentication.

Flow (update_authen_v1.0):
  /start → request contact → employee lookup → email OTP → link account

Run (after DATABASE_URL + TELEGRAM_BOT_TOKEN are set):

    python -m app.telegram.bot_listener
"""

from __future__ import annotations

import logging
import sys
import time

from app.auth import messages as msg
from app.config import get_settings
from app.db.connection import check_connection
from app.services.authentication import AuthReply, AuthenticationService
from app.telegram.client import TelegramClient, TelegramClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _send_reply(client: TelegramClient, chat_id: int, reply: AuthReply) -> None:
    try:
        if reply.request_contact:
            client.send_contact_request(chat_id, reply.text, msg.SHARE_PHONE_BUTTON)
        elif reply.remove_keyboard:
            client.send_remove_keyboard(chat_id, reply.text)
        else:
            client.send_message(chat_id, reply.text)
    except TelegramClientError as exc:
        logger.warning("Could not send auth reply: %s", exc)


def handle_update(
    update: dict,
    auth: AuthenticationService,
    client: TelegramClient,
) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = from_user.get("id")
    if chat_id is None or user_id is None:
        return

    chat_type = chat.get("type") or "private"
    username = from_user.get("username")
    telegram_user_id = int(user_id)
    telegram_chat_id = int(chat_id)

    contact = message.get("contact")
    if contact:
        reply = auth.handle_contact(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            chat_type=chat_type,
            username=username,
            contact=contact,
        )
        _send_reply(client, telegram_chat_id, reply)
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    if text.startswith("/start"):
        reply = auth.handle_start(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            chat_type=chat_type,
            username=username,
        )
        _send_reply(client, telegram_chat_id, reply)
        return

    otp_reply = auth.handle_otp_text(
        telegram_user_id=telegram_user_id,
        telegram_chat_id=telegram_chat_id,
        text=text,
        username=username,
    )
    if otp_reply is not None:
        _send_reply(client, telegram_chat_id, otp_reply)


def run() -> None:
    settings = get_settings()
    if not settings.has_telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Fill .env and retry.")
        sys.exit(1)

    ok, msg_db = check_connection()
    if not ok:
        logger.error("Database not ready: %s", msg_db)
        sys.exit(1)

    if not settings.has_smtp:
        logger.error(
            "SMTP is not configured. OTP emails will fail until SMTP_* is set in .env."
        )
    else:
        logger.info(
            "OTP delivery: email via SMTP host=%s from=%s",
            settings.smtp_host,
            settings.smtp_from,
        )

    client = TelegramClient()
    auth = AuthenticationService()
    me = client.get_me()
    logger.info("Listening as @%s (id=%s)", me.get("username"), me.get("id"))

    offset: int | None = None
    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=25)
            for update in updates:
                update_id = update.get("update_id")
                try:
                    handle_update(update, auth, client)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "Failed handling update_id=%s", update_id
                    )
                if update_id is not None:
                    offset = int(update_id) + 1
        except TelegramClientError as exc:
            logger.error("Telegram error: %s — retrying in 5s", exc)
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error — retrying in 5s")
            time.sleep(5)


if __name__ == "__main__":
    run()
