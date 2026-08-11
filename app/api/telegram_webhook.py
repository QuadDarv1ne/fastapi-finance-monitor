"""Telegram webhook handler for bot connections

This module handles incoming webhook requests from Telegram bots,
allowing users to connect their Telegram accounts to the platform.
"""

import base64
import hashlib
import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Telegram Webhook"])


@router.post("/telegram")
async def telegram_webhook(
    webhook_data: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Handle incoming Telegram webhook updates

    This endpoint receives updates from Telegram bots including:
    - /start commands with connection tokens
    - User messages
    - Callback queries

    The endpoint is authenticated with the X-Telegram-Bot-Api-Secret-Token
    header (set via Telegram setWebhook secret_token parameter).
    """
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    if expected_secret:
        if not x_telegram_bot_api_secret_token or not secrets_compare(
            x_telegram_bot_api_secret_token, expected_secret
        ):
            logger.warning("Telegram webhook rejected: invalid secret token")
            raise HTTPException(status_code=401, detail="Invalid secret token")
    else:
        logger.warning(
            "TELEGRAM_WEBHOOK_SECRET is not set - webhook is unauthenticated. "
            "Set it and pass it via setWebhook(secret_token=...) in production."
        )

    try:
        # Handle message
        if "message" in webhook_data:
            message = webhook_data["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            username = message.get("from", {}).get("username", "User")

            # Handle /start command with connection token
            if text.startswith("/start "):
                token = text.split(" ", 1)[1]
                return await handle_connect_command(chat_id, username, token)

            # Handle /help command
            elif text == "/help":
                return await handle_help_command(chat_id, username)

            # Handle /status command
            elif text == "/status":
                return await handle_status_command(chat_id, username)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return {"ok": False}


def secrets_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hashlib.sha256(a.encode()).digest() == hashlib.sha256(b.encode()).digest()


async def handle_connect_command(chat_id: int, username: str, token: str) -> dict:
    """Handle user connection via /start command"""
    try:
        from app.database import SessionLocal
        from app.models import TelegramConnection, User
        from app.services.telegram_service import get_telegram_service

        # Decode token
        try:
            decoded = base64.urlsafe_b64decode(token).decode()
            user_id_str, token_secret = decoded.split(":", 1)
            user_id = int(user_id_str)
        except Exception as e:
            logger.error(f"Invalid connection token: {e}")
            await send_telegram_message(
                chat_id,
                "❌ <b>Ошибка подключения</b>\n\n"
                "Неверная или устаревшая ссылка.\n"
                "Пожалуйста, получите новую ссылку в личном кабинете.",
            )
            return {"ok": True}

        db = SessionLocal()

        try:
            # Check if user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await send_telegram_message(
                    chat_id, "❌ <b>Ошибка подключения</b>\n\n" "Пользователь не найден."
                )
                return {"ok": True}

            # Validate the token against the stored hash
            stored_hash = user.telegram_connect_token_hash
            if not stored_hash or not secrets_compare(
                hashlib.sha256(token_secret.encode()).hexdigest(), stored_hash
            ):
                logger.warning(f"Telegram connect rejected: token mismatch for user {user_id}")
                await send_telegram_message(
                    chat_id,
                    "❌ <b>Ошибка подключения</b>\n\n"
                    "Неверная или устаревшая ссылка.\n"
                    "Пожалуйста, получите новую ссылку в личном кабинете.",
                )
                return {"ok": True}

            # Invalidate the one-time token after successful validation
            user.telegram_connect_token_hash = None

            # If this chat is already connected to a different user, keep the
            # existing connection but point it at the new user instead.
            existing = (
                db.query(TelegramConnection)
                .filter(TelegramConnection.telegram_id == str(chat_id))
                .first()
            )

            # The user may already have a connection from another chat
            user_connection = (
                db.query(TelegramConnection).filter(TelegramConnection.user_id == user_id).first()
            )

            now = datetime.now(UTC).replace(tzinfo=None)

            if user_connection and user_connection.telegram_id == str(chat_id):
                # Already connected in this chat - just re-activate
                user_connection.is_active = True
                user_connection.telegram_username = username
                user_connection.connected_at = now
            elif existing:
                # Rebind this chat from the old owner to the new user
                if existing.user_id != user_id:
                    for conn in (
                        db.query(TelegramConnection)
                        .filter(
                            TelegramConnection.user_id == existing.user_id,
                            TelegramConnection.id != existing.id,
                        )
                        .all()
                    ):
                        conn.is_active = False
                if user_connection and user_connection.id != existing.id:
                    # The user already has a connection in another chat; user_id
                    # is unique, so remove the old row before rebinding.
                    db.delete(user_connection)
                existing.user_id = user_id
                existing.telegram_username = username
                existing.is_active = True
                existing.connected_at = now
            else:
                if user_connection:
                    # user_id is unique - remove the old row from another chat
                    db.delete(user_connection)
                connection = TelegramConnection(
                    user_id=user_id,
                    telegram_id=str(chat_id),
                    telegram_username=username,
                    is_active=True,
                    connected_at=now,
                )
                db.add(connection)

            db.commit()

            # Send welcome message
            telegram_service = get_telegram_service()
            await telegram_service.send_welcome_message(str(chat_id), username)

            logger.info(f"Telegram connected for user {user_id}: {username}")

        finally:
            db.close()

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error in connect command: {e}")
        await send_telegram_message(
            chat_id,
            "❌ <b>Ошибка подключения</b>\n\n"
            "Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку.",
        )
        return {"ok": True}


async def handle_help_command(chat_id: int, username: str) -> dict:
    """Handle /help command"""
    message = (
        "🤖 <b>Помощь по Telegram боту</b>\n\n"
        "<b>Команды:</b>\n"
        "/start - Подключить Telegram к аккаунту\n"
        "/help - Показать эту справку\n"
        "/status - Показать статус подключения\n\n"
        "<b>Уведомления:</b>\n"
        "• 📈 Ценовые алерты\n"
        "• 📊 Обновления портфеля\n"
        "• ⚠️ Важные события\n\n"
        "<i>FastAPI Finance Monitor</i>"
    )

    await send_telegram_message(chat_id, message)
    return {"ok": True}


async def handle_status_command(chat_id: int, username: str) -> dict:
    """Handle /status command"""
    try:
        from app.database import SessionLocal
        from app.models import TelegramConnection, User

        db = SessionLocal()
        try:
            connection = (
                db.query(TelegramConnection)
                .filter(
                    TelegramConnection.telegram_id == str(chat_id), TelegramConnection.is_active
                )
                .first()
            )

            if connection:
                user = db.query(User).filter(User.id == connection.user_id).first()
                username_str = f"@{user.username}" if user else f"ID: {connection.user_id}"

                message = (
                    "✅ <b>Подключено</b>\n\n"
                    f"<b>Аккаунт:</b> {username_str}\n"
                    f"<b>Подключено:</b> {connection.connected_at.strftime('%d.%m.%Y %H:%M')}\n"
                )

                if connection.last_notification_at:
                    message += (
                        f"<b>Последнее уведомление:</b> "
                        f"{connection.last_notification_at.strftime('%d.%m.%Y %H:%M')}\n"
                    )
            else:
                message = (
                    "❌ <b>Не подключено</b>\n\n"
                    "Telegram не подключен к аккаунту.\n"
                    "Используйте /start с ссылкой из личного кабинета."
                )
        finally:
            db.close()

        await send_telegram_message(chat_id, message)
        return {"ok": True}

    except Exception as e:
        logger.error(f"Error in status command: {e}")
        return {"ok": True}


async def send_telegram_message(chat_id: int, message: str) -> bool:
    """Send a message to Telegram chat using singleton session"""
    try:
        from app.services.telegram_service import get_telegram_service

        telegram_service = get_telegram_service()
        return await telegram_service.send_message(str(chat_id), message)
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False
