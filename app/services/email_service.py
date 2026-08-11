"""Email notification service using SMTP with aiosmtplib

This module provides email notification capabilities for the finance monitor
application. It supports sending various types of notifications including
price alerts, portfolio updates, and system notifications.

Key Features:
- SMTP email sending with TLS/SSL support
- HTML and plain text email templates
- Template-based notifications (price alerts, portfolio updates, etc.)
- Connection pooling and session reuse
- Retry logic for transient failures
- Async email sending with aiosmtplib

Usage:
    email_service = EmailService()
    await email_service.connect()
    await email_service.send_price_alert(to_email, alert_data)
    await email_service.close()
"""

import asyncio
import html
import logging
import os
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration settings"""

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
    APP_NAME = os.getenv("APP_NAME", "FastAPI Finance Monitor")


class EmailService:
    """Service for sending email notifications via SMTP"""

    _instance: "EmailService | None" = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        self.config = EmailConfig()
        self.enabled = bool(self.config.SMTP_USERNAME and self.config.SMTP_PASSWORD)
        self._connection: aiosmtplib.SMTP | None = None
        self._connected = False

        if not self.enabled:
            logger.warning(
                "Email service disabled: SMTP credentials not configured. "
                "Set SMTP_USERNAME and SMTP_PASSWORD environment variables."
            )

    @classmethod
    async def get_instance(cls) -> "EmailService":
        """Get singleton instance of EmailService"""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def connect(self) -> bool:
        """Connect to SMTP server"""
        if not self.enabled:
            logger.warning("Cannot connect: Email service is disabled")
            return False

        if self._connected and self._connection is not None:
            return True

        try:
            # Connect without implicit TLS first - STARTTLS is handled explicitly below.
            # Note: use_tls=True in aiosmtplib means implicit TLS (SMTPS, port 465),
            # which is incompatible with the default port 587 + STARTTLS setup.
            connection = aiosmtplib.SMTP(
                hostname=self.config.SMTP_HOST,
                port=self.config.SMTP_PORT,
                use_tls=False,
            )
            await connection.connect()
            if self.config.SMTP_USE_TLS:
                await connection.starttls()
            await connection.login(self.config.SMTP_USERNAME, self.config.SMTP_PASSWORD)
            self._connection = connection
            self._connected = True
            logger.info(
                f"Email service connected to {self.config.SMTP_HOST}:{self.config.SMTP_PORT}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            self._connected = False
            return False

    async def close(self) -> None:
        """Close SMTP connection"""
        if self._connection is not None:
            try:
                await self._connection.quit()
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {e}")
            finally:
                self._connection = None
                self._connected = False

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> bool:
        """Send an email with retry logic

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body (HTML or plain text)
            is_html: Whether the body is HTML

        Returns:
            True if email sent successfully
        """
        if not self.enabled:
            logger.warning("Cannot send email: Email service is disabled")
            return False

        if not self._connected:
            connected = await self.connect()
            if not connected:
                logger.error("Cannot send email: Not connected to SMTP server")
                return False

        message = MIMEMultipart("alternative")
        message["From"] = self.config.FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject

        content_type = "html" if is_html else "plain"
        mime_type = MIMEText(body, content_type, "utf-8")
        message.attach(mime_type)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self._connected or self._connection is None:
                    connected = await self.connect()
                    if not connected:
                        logger.error("Cannot send email: Not connected to SMTP server")
                        return False
                await self._connection.send_message(message)  # type: ignore[union-attr]
                logger.info(f"Email sent successfully to {to_email}: {subject}")
                return True
            except Exception as e:
                logger.warning(
                    f"Failed to send email to {to_email} (attempt {attempt + 1}/{max_retries}): {e}"
                )
                # The connection may be dead - drop it so the next attempt reconnects
                self._connected = False
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    await self.close()
                else:
                    logger.error(f"All {max_retries} attempts failed to send email to {to_email}")
                    return False

        return False

    def _build_price_alert_html(self, alert_data: dict[str, Any]) -> str:
        """Build HTML body for price alert notification"""
        symbol = html.escape(str(alert_data.get("symbol", "Unknown")))
        current_price = alert_data.get("current_price", 0)
        target_price = alert_data.get("target_price", 0)
        alert_type = html.escape(str(alert_data.get("alert_type", "above")))
        change_percent = alert_data.get("change_percent", 0)
        change_icon = "▲" if change_percent >= 0 else "▼"
        change_color = "#10b981" if change_percent >= 0 else "#ef4444"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 10px; color: white;">
                <h2 style="margin: 0;">🔔 Price Alert Triggered</h2>
            </div>
            <div style="padding: 20px; background: #f9f9f9; border-radius: 10px; margin-top: 15px;">
                <h3 style="color: #333;">{symbol}</h3>
                <p style="font-size: 18px;">
                    Current Price: <strong>${current_price:,.2f}</strong>
                </p>
                <p style="font-size: 16px;">
                    Alert: Price is {alert_type} <strong>${target_price:,.2f}</strong>
                </p>
                <p style="font-size: 16px; color: {change_color};">
                    24h Change: {change_icon} {change_percent:+.2f}%
                </p>
                <p style="color: #888; font-size: 14px;">
                    Triggered at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
            <p style="color: #888; font-size: 12px; text-align: center; margin-top: 20px;">
                Sent by {self.config.APP_NAME}
            </p>
        </body>
        </html>
        """

    def _build_portfolio_update_html(self, portfolio_data: dict[str, Any]) -> str:
        """Build HTML body for portfolio update notification"""
        total_value = portfolio_data.get("total_value", 0)
        total_gain = portfolio_data.get("total_gain", 0)
        total_return = portfolio_data.get("total_return", 0)
        gain_color = "#10b981" if total_gain >= 0 else "#ef4444"

        holdings_html = ""
        holdings = portfolio_data.get("holdings", [])
        for holding in holdings[:5]:
            symbol = html.escape(str(holding.get("symbol", "Unknown")))
            value = holding.get("value", 0)
            change = holding.get("change_percent", 0)
            change_color = "#10b981" if change >= 0 else "#ef4444"
            holdings_html += f"""
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #eee;">{symbol}</td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">
                    ${value:,.2f}
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right; color: {change_color};">
                    {change:+.2f}%
                </td>
            </tr>
            """

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 10px; color: white;">
                <h2 style="margin: 0;">📊 Portfolio Update</h2>
            </div>
            <div style="padding: 20px; background: #f9f9f9; border-radius: 10px; margin-top: 15px;">
                <p style="font-size: 24px;">
                    Total Value: <strong>${total_value:,.2f}</strong>
                </p>
                <p style="font-size: 18px; color: {gain_color};">
                    Total Gain/Loss: {total_gain:+,.2f} ({total_return:+.2f}%)
                </p>
                <table style="width: 100%; margin-top: 15px; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #eee;">
                            <th style="padding: 8px; text-align: left;">Symbol</th>
                            <th style="padding: 8px; text-align: right;">Value</th>
                            <th style="padding: 8px; text-align: right;">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {holdings_html}
                    </tbody>
                </table>
            </div>
            <p style="color: #888; font-size: 12px; text-align: center; margin-top: 20px;">
                Sent by {self.config.APP_NAME}
            </p>
        </body>
        </html>
        """

    async def send_price_alert(self, to_email: str, alert_data: dict[str, Any]) -> bool:
        """Send a price alert email notification

        Args:
            to_email: Recipient email address
            alert_data: Dictionary with alert information (symbol, price, etc.)

        Returns:
            True if email sent successfully
        """
        symbol = alert_data.get("symbol", "Unknown")
        subject = f"🔔 Price Alert: {symbol} ${alert_data.get('current_price', 0):,.2f}"
        body = self._build_price_alert_html(alert_data)
        return await self.send_email(to_email, subject, body, is_html=True)

    async def send_portfolio_update(self, to_email: str, portfolio_data: dict[str, Any]) -> bool:
        """Send a portfolio update email notification

        Args:
            to_email: Recipient email address
            portfolio_data: Dictionary with portfolio information

        Returns:
            True if email sent successfully
        """
        subject = f"📊 Portfolio Update: ${portfolio_data.get('total_value', 0):,.2f}"
        body = self._build_portfolio_update_html(portfolio_data)
        return await self.send_email(to_email, subject, body, is_html=True)

    async def send_welcome_email(self, to_email: str, username: str) -> bool:
        """Send a welcome email to a new user

        Args:
            to_email: Recipient email address
            username: Username of the new user

        Returns:
            True if email sent successfully
        """
        subject = f"Welcome to {self.config.APP_NAME}! 🎉"
        safe_username = html.escape(str(username))
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 10px; color: white;">
                <h2 style="margin: 0;">Welcome, {safe_username}! 🎉</h2>
            </div>
            <div style="padding: 20px; background: #f9f9f9; border-radius: 10px; margin-top: 15px;">
                <p>Thank you for joining <strong>{self.config.APP_NAME}</strong>!</p>
                <p>You can now:</p>
                <ul>
                    <li>📈 Monitor stocks, crypto, and commodities in real-time</li>
                    <li>📊 View technical indicators (RSI, MACD, Bollinger Bands)</li>
                    <li>🔔 Set up price alerts</li>
                    <li>📁 Manage your portfolio</li>
                    <li>🤖 Get ML-powered price forecasts</li>
                </ul>
                <p style="color: #888; font-size: 14px;">
                    Logged in at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
            <p style="color: #888; font-size: 12px; text-align: center; margin-top: 20px;">
                Sent by {self.config.APP_NAME}
            </p>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, body, is_html=True)

    async def send_test_email(self, to_email: str) -> bool:
        """Send a test email to verify configuration

        Args:
            to_email: Recipient email address

        Returns:
            True if email sent successfully
        """
        subject = f"Test Email from {self.config.APP_NAME}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        padding: 20px; border-radius: 10px; color: white;">
                <h2 style="margin: 0;">✅ Email Configuration Test</h2>
            </div>
            <div style="padding: 20px; background: #f9f9f9; border-radius: 10px; margin-top: 15px;">
                <p>If you received this email, your email configuration is working correctly!</p>
                <p style="color: #888; font-size: 14px;">
                    Sent at: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
        </body>
        </html>
        """
        return await self.send_email(to_email, subject, body, is_html=True)
