"""Telegram notification service for real-time alerts

This module provides Telegram integration for sending notifications
when price alerts are triggered or other events occur.

Key Features:
- Bot authentication and connection management
- Send notifications to connected users
- Connection status tracking
- Rate limiting for notifications
"""

import logging
import os
from datetime import datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for sending Telegram notifications"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.enabled = bool(self.bot_token)
        
        if not self.enabled:
            logger.warning("Telegram bot token not configured. Notifications disabled.")
        
        # Rate limiting
        self.notification_cooldown = 60  # seconds between notifications to same user
        self.last_notification: dict[str, datetime] = {}

    async def send_message(self, telegram_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to a Telegram user
        
        Args:
            telegram_id: User's Telegram ID
            message: Message text (supports HTML markup)
            parse_mode: Parse mode (HTML or Markdown)
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            logger.warning("Telegram service is disabled")
            return False

        # Rate limiting check
        now = datetime.utcnow()
        if telegram_id in self.last_notification:
            time_since_last = (now - self.last_notification[telegram_id]).total_seconds()
            if time_since_last < self.notification_cooldown:
                logger.warning(f"Rate limit for Telegram user {telegram_id}")
                return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": telegram_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get("ok"):
                        self.last_notification[telegram_id] = now
                        logger.info(f"Telegram message sent to {telegram_id}")
                        return True
                    else:
                        error = result.get("description", "Unknown error")
                        logger.error(f"Telegram API error: {error}")
                        
                        # Handle common errors
                        if "bot was blocked" in error.lower():
                            logger.warning(f"User {telegram_id} blocked the bot")
                            return False
                        if "chat not found" in error.lower():
                            logger.warning(f"Chat {telegram_id} not found")
                            return False
                            
                        return False
        except aiohttp.ClientError as e:
            logger.error(f"Network error sending Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message: {e}")
            return False

    async def send_price_alert(
        self,
        telegram_id: str,
        symbol: str,
        alert_type: str,
        target_price: float,
        current_price: float,
    ) -> bool:
        """Send a price alert notification
        
        Args:
            telegram_id: User's Telegram ID
            symbol: Asset symbol
            alert_type: Type of alert (above/below)
            target_price: Target price that was triggered
            current_price: Current market price
        """
        arrow = "📈" if alert_type == "above" else "📉"
        direction = "выше" if alert_type == "above" else "ниже"
        
        message = (
            f"{arrow} <b>Ценовое уведомление</b>\n\n"
            f"<b>Актив:</b> {symbol}\n"
            f"<b>Условие:</b> цена {direction} ${target_price:,.2f}\n"
            f"<b>Текущая цена:</b> ${current_price:,.2f}\n\n"
            f"<i>FastAPI Finance Monitor</i>"
        )
        
        return await self.send_message(telegram_id, message)

    async def send_welcome_message(self, telegram_id: str, username: str) -> bool:
        """Send welcome message when user connects Telegram
        
        Args:
            telegram_id: User's Telegram ID
            username: User's Telegram username
        """
        message = (
            f"👋 <b>Добро пожаловать, {username}!</b>\n\n"
            f"Вы успешно подключили Telegram уведомления к FastAPI Finance Monitor.\n\n"
            f"Теперь вы будете получать уведомления:\n"
            f"• 📈 О срабатывании ценовых алертов\n"
            f"• ⚠️ Важные события по вашему портфелю\n\n"
            f"Управляйте уведомлениями в личном кабинете."
        )
        
        return await self.send_message(telegram_id, message)

    async def get_bot_info(self) -> dict[str, Any] | None:
        """Get bot information from Telegram API
        
        Returns:
            Bot info dict or None if error
        """
        if not self.enabled:
            return None

        url = f"{self.base_url}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("ok"):
                            return result.get("result")
            return None
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None

    async def send_portfolio_update(
        self,
        telegram_id: str,
        portfolio_name: str,
        total_value: float,
        change_percent: float,
    ) -> bool:
        """Send portfolio performance update
        
        Args:
            telegram_id: User's Telegram ID
            portfolio_name: Portfolio name
            total_value: Total portfolio value
            change_percent: 24h change percentage
        """
        arrow = "📈" if change_percent >= 0 else "📉"
        sign = "+" if change_percent >= 0 else ""
        
        message = (
            f"{arrow} <b>Обновление портфеля</b>\n\n"
            f"<b>{portfolio_name}</b>\n"
            f"Стоимость: ${total_value:,.2f}\n"
            f"Изменение: {sign}{change_percent:.2f}%\n\n"
            f"<i>FastAPI Finance Monitor</i>"
        )
        
        return await self.send_message(telegram_id, message)


# Global telegram service instance
telegram_service = TelegramService()


def get_telegram_service() -> TelegramService:
    """Get telegram service instance"""
    return telegram_service
