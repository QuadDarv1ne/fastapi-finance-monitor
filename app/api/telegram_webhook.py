"""Telegram webhook handler for bot connections

This module handles incoming webhook requests from Telegram bots,
allowing users to connect their Telegram accounts to the platform.
"""

import base64
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Telegram Webhook"])


@router.post("/telegram")
async def telegram_webhook(webhook_data: dict):
    """Handle incoming Telegram webhook updates
    
    This endpoint receives updates from Telegram bots including:
    - /start commands with connection tokens
    - User messages
    - Callback queries
    """
    try:
        # Log the update for debugging
        logger.info(f"Telegram webhook received: {webhook_data}")
        
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
        return {"ok": False, "error": str(e)}


async def handle_connect_command(chat_id: int, username: str, token: str) -> dict:
    """Handle user connection via /start command"""
    try:
        from app.database import SessionLocal
        from app.models import TelegramConnection, User
        from app.services.telegram_service import get_telegram_service
        
        # Decode token
        try:
            decoded = base64.urlsafe_b64decode(token).decode()
            user_id_str, _ = decoded.split(":", 1)
            user_id = int(user_id_str)
        except Exception as e:
            logger.error(f"Invalid connection token: {e}")
            await send_telegram_message(
                chat_id,
                "❌ <b>Ошибка подключения</b>\n\n"
                "Неверная или устаревшая ссылка.\n"
                "Пожалуйста, получите новую ссылку в личном кабинете."
            )
            return {"ok": True}
        
        db = SessionLocal()
        
        try:
            # Check if user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                await send_telegram_message(
                    chat_id,
                    "❌ <b>Ошибка подключения</b>\n\n"
                    "Пользователь не найден."
                )
                return {"ok": True}
            
            # Check if Telegram is already connected
            existing = db.query(TelegramConnection).filter(
                TelegramConnection.telegram_id == str(chat_id)
            ).first()
            
            if existing and existing.is_active:
                await send_telegram_message(
                    chat_id,
                    "ℹ️ <b>Уже подключено</b>\n\n"
                    f"Ваш Telegram уже подключен к аккаунту @{user.username}."
                )
                return {"ok": True}
            
            # Create or update connection
            if existing:
                existing.is_active = True
                existing.telegram_username = username
                existing.connected_at = datetime.utcnow()
            else:
                connection = TelegramConnection(
                    user_id=user_id,
                    telegram_id=str(chat_id),
                    telegram_username=username,
                    is_active=True,
                    connected_at=datetime.utcnow(),
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
            f"Произошла ошибка: {e!s}\n"
            "Попробуйте еще раз или обратитесь в поддержку."
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
        from app.models import TelegramConnection
        
        db = SessionLocal()
        try:
            connection = db.query(TelegramConnection).filter(
                TelegramConnection.telegram_id == str(chat_id),
                TelegramConnection.is_active == True
            ).first()
            
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
    """Send a message to Telegram chat"""
    try:
        import os
        import aiohttp
        
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.warning("Telegram bot token not configured")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                return response.status == 200 and result.get("ok")
                
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False
