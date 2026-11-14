"""Thin Telegram Bot API client using httpx."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings


class TelegramClientError(Exception):
    """Raised when a Telegram API call fails."""


@dataclass
class SendResult:
    chat_id: int
    ok: bool
    detail: str


class TelegramClient:
    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        settings = get_settings()
        self.token = (token if token is not None else settings.telegram_bot_token).strip()
        self.timeout = timeout
        if not self.token:
            raise TelegramClientError(
                "TELEGRAM_BOT_TOKEN is empty. Set it in .env or enable DRY_RUN."
            )

    @property
    def _base(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def get_me(self) -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self._base}/getMe")
            data = response.json()
        if not data.get("ok"):
            raise TelegramClientError(f"getMe failed: {data}")
        return data["result"]

    def send_message(
        self,
        chat_id: int,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> SendResult:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self._base}/sendMessage", json=payload)
            data = response.json()
        if data.get("ok"):
            return SendResult(chat_id=chat_id, ok=True, detail="sent")
        description = data.get("description", str(data))
        return SendResult(chat_id=chat_id, ok=False, detail=description)

    def send_contact_request(self, chat_id: int, text: str, button_label: str) -> SendResult:
        # ReplyKeyboardMarkup (not inline). On Desktop/Web the bar may be
        # collapsed — user opens it via the keyboard icon near the input.
        keyboard = {
            "keyboard": [
                [{"text": button_label, "request_contact": True}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
            "is_persistent": True,
            "input_field_placeholder": "Nhan nut chia se so dien thoai",
        }
        return self.send_message(chat_id, text, reply_markup=keyboard)

    def send_remove_keyboard(self, chat_id: int, text: str) -> SendResult:
        return self.send_message(
            chat_id,
            text,
            reply_markup={"remove_keyboard": True},
        )

    def get_updates(self, offset: int | None = None, timeout: int = 25) -> list[dict]:
        params: dict[str, int] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        with httpx.Client(timeout=timeout + 10) as client:
            response = client.get(f"{self._base}/getUpdates", params=params)
            data = response.json()
        if not data.get("ok"):
            raise TelegramClientError(f"getUpdates failed: {data}")
        return data.get("result", [])

    def broadcast(self, text: str, chat_ids: list[int]) -> list[SendResult]:
        return [self.send_message(chat_id, text) for chat_id in chat_ids]
