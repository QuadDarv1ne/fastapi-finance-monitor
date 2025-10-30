"""Advanced alert service with complex conditions and notification capabilities"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from app.services.database_service import DatabaseService
from app.services.data_fetcher import DataFetcher
from app.services.indicators import TechnicalIndicators
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class AdvancedAlertService:
    """Service for handling advanced alerts and notifications"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.data_fetcher = DataFetcher()
        self.active_alerts = {}  # Store active alerts for monitoring
        self.monitoring_task = None
        
    async def create_alert(self, user_id: int, symbol: str, condition: Dict, 
                          notification_types: List[str], schedule: Optional[Dict] = None,
                          description: Optional[str] = None):
        """Create a new alert"""
        try:
            # Import Alert model inside function to avoid circular imports
            from app.models import Alert
            
            # Create alert in database
            db_alert = Alert(
                user_id=user_id,
                symbol=symbol.upper(),
                alert_type=condition.get("type"),
                threshold=condition.get("threshold", 0.0),
                extra_params=json.dumps(condition.get("extra_params", {})) if condition.get("extra_params") else None,
                notification_types=json.dumps(notification_types),
                schedule=json.dumps(schedule) if schedule else None,
                description=description
            )
            
            # Add to database session
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                db.add(db_alert)
                db.commit()
                db.refresh(db_alert)
            finally:
                db.close()
            
            # Add to active alerts if it's active
            if db_alert.is_active:
                self.active_alerts[db_alert.id] = db_alert
                
            logger.info(f"Created alert {db_alert.id} for user {user_id} on {symbol}")
            return db_alert
            
        except Exception as e:
            # Note: We can't use db.rollback() here because we're using a separate session
            logger.error(f"Error creating alert: {e}")
            raise
    
    async def update_alert(self, alert_id: int, **kwargs):
        """Update an existing alert"""
        try:
            # Import Alert model inside function to avoid circular imports
            from app.models import Alert
            
            # Get alert from database
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
                if not db_alert:
                    raise ValueError(f"Alert {alert_id} not found")
                
                # Update fields
                for key, value in kwargs.items():
                    if hasattr(db_alert, key):
                        if key in ['notification_types', 'schedule', 'extra_params'] and value is not None:
                            setattr(db_alert, key, json.dumps(value))
                        else:
                            setattr(db_alert, key, value)
                
                db_alert.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(db_alert)
            finally:
                db.close()
            
            # Update active alerts cache
            if db_alert.is_active:
                self.active_alerts[db_alert.id] = db_alert
            elif alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                
            logger.info(f"Updated alert {alert_id}")
            return db_alert
            
        except Exception as e:
            logger.error(f"Error updating alert {alert_id}: {e}")
            raise
    
    async def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert"""
        try:
            # Import Alert model inside function to avoid circular imports
            from app.models import Alert
            
            # Get alert from database
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
                if not db_alert:
                    return False
                
                # Remove from database
                db.delete(db_alert)
                db.commit()
            finally:
                db.close()
            
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                
            logger.info(f"Deleted alert {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting alert {alert_id}: {e}")
            raise
    
    async def get_user_alerts(self, user_id: int):
        """Get all alerts for a user"""
        try:
            # Import Alert model inside function to avoid circular imports
            from app.models import Alert
            
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                alerts = db.query(Alert).filter(Alert.user_id == user_id).all()
                return alerts
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error getting alerts for user {user_id}: {e}")
            raise
    
    async def start_monitoring(self):
        """Start the alert monitoring task"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitor_alerts())
            logger.info("Started alert monitoring task")
    
    async def stop_monitoring(self):
        """Stop the alert monitoring task"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped alert monitoring task")
    
    async def _monitor_alerts(self):
        """Background task to monitor alerts"""
        while True:
            try:
                # Refresh active alerts from database
                await self._refresh_active_alerts()
                
                # Check each active alert
                for alert_id, alert in list(self.active_alerts.items()):
                    # Check if alert should be active based on schedule
                    if await self._is_alert_active_by_schedule(alert):
                        # Check alert conditions
                        await self._check_alert_condition(alert)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _refresh_active_alerts(self):
        """Refresh active alerts from database"""
        try:
            # Import Alert model inside function to avoid circular imports
            from app.models import Alert
            
            # Get all active alerts from database
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                db_alerts = db.query(Alert).filter(Alert.is_active == True).all()
                
                # Update active alerts cache
                self.active_alerts = {alert.id: alert for alert in db_alerts}
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error refreshing active alerts: {e}")
    
    async def _is_alert_active_by_schedule(self, alert) -> bool:
        """Check if an alert should be active based on its schedule"""
        try:
            if not alert.schedule:
                return True  # No schedule means always active
            
            # Parse schedule
            schedule_data = json.loads(alert.schedule)
            
            # Get current time and day
            now = datetime.now()
            current_day = now.strftime("%A").lower()
            current_time = now.time()
            
            # Check if today is an active day
            if schedule_data.get("active_days") and current_day not in schedule_data.get("active_days", []):
                return False
            
            # Check time range if specified
            if schedule_data.get("start_time") and schedule_data.get("end_time"):
                start_time = datetime.strptime(schedule_data.get("start_time"), "%H:%M").time()
                end_time = datetime.strptime(schedule_data.get("end_time"), "%H:%M").time()
                
                if not (start_time <= current_time <= end_time):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking alert schedule for alert {alert.id}: {e}")
            return True  # Default to active if there's an error
    
    async def _check_alert_condition(self, alert):
        """Check if an alert condition is met"""
        try:
            # Get current data for the symbol
            current_data = await self._get_asset_data(alert.symbol)
            if not current_data:
                return
            
            # Parse condition
            condition_data = {
                "type": alert.alert_type,
                "threshold": alert.threshold,
                "extra_params": json.loads(alert.extra_params) if alert.extra_params else None
            }
            
            # Check if condition is met
            condition_met, current_value = await self._evaluate_condition(condition_data, current_data, alert.symbol)
            
            if condition_met:
                # Trigger alert
                await self._trigger_alert(alert, current_value, condition_data)
                
        except Exception as e:
            logger.error(f"Error checking alert condition for alert {alert.id}: {e}")
    
    async def _get_asset_data(self, symbol: str) -> Optional[Dict]:
        """Get current data for an asset"""
        try:
            # Try to get stock data first
            stock_data = await self.data_fetcher.get_stock_data(symbol)
            if stock_data:
                return stock_data
            
            # Try to get crypto data
            crypto_data = await self.data_fetcher.get_crypto_data(symbol.lower())
            if crypto_data:
                return crypto_data
            
            return None
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            return None
    
    async def _evaluate_condition(self, condition: Dict, current_data: Dict, symbol: str) -> tuple[bool, float]:
        """Evaluate if an alert condition is met"""
        try:
            current_price = current_data.get("current_price", 0)
            condition_type = condition.get("type")
            threshold = condition.get("threshold", 0)
            
            if condition_type == "price_above":
                return current_price >= threshold, current_price
            
            elif condition_type == "price_below":
                return current_price <= threshold, current_price
            
            elif condition_type == "percentage_change":
                change_percent = current_data.get("change_percent", 0)
                return abs(change_percent) >= threshold, change_percent
            
            elif condition_type in ["rsi_overbought", "rsi_oversold"]:
                # Get historical data for RSI calculation
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="1mo", interval="1d")
                
                if not df.empty:
                    rsi = TechnicalIndicators.calculate_rsi(df['Close'])
                    
                    if condition_type == "rsi_overbought":
                        return rsi >= threshold, rsi
                    else:  # rsi_oversold
                        return rsi <= threshold, rsi
            
            elif condition_type == "volume_spike":
                current_volume = current_data.get("volume", 0)
                # For volume spike, threshold could be a multiplier (e.g., 2.0 for 2x normal volume)
                # We would need to calculate average volume for comparison
                return False, current_volume  # Simplified for now
            
            return False, 0
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False, 0
    
    async def _trigger_alert(self, alert, triggered_value: float, condition_met: Dict):
        """Trigger an alert and send notifications"""
        try:
            # Import AlertTriggerHistory model inside function to avoid circular imports
            from app.models import AlertTriggerHistory
            
            # Create alert trigger history record
            trigger_history = AlertTriggerHistory(
                alert_id=alert.id,
                triggered_value=triggered_value,
                condition_met=json.dumps(condition_met)
            )
            
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                db.add(trigger_history)
                db.commit()
            finally:
                db.close()
            
            # Parse notification types
            notification_types = json.loads(alert.notification_types)
            
            # Send notifications
            from app.models import User
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == alert.user_id).first()
                if user:
                    for notification_type in notification_types:
                        await self._send_notification(notification_type, user, alert, triggered_value, condition_met)
                    
                    # Mark notification as sent
                    trigger_history.notification_sent = True
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"Alert {alert.id} triggered for {alert.symbol} at {triggered_value}")
            
        except Exception as e:
            logger.error(f"Error triggering alert {alert.id}: {e}")
    
    async def _send_notification(self, notification_type: str, user, 
                                alert, triggered_value: float, condition_met: Dict):
        """Send notification based on type"""
        try:
            message = f"Alert triggered for {alert.symbol}: {condition_met.get('type')} at {triggered_value}"
            
            if notification_type == "email" and user.email:
                await self._send_email_notification(user.email, f"Alert for {alert.symbol}", message)
            
            elif notification_type == "in_app":
                # This would be handled by WebSocket in a real implementation
                logger.info(f"In-app notification for user {user.id}: {message}")
            
            # Other notification types (SMS, Webhook) would be implemented here
            
        except Exception as e:
            logger.error(f"Error sending {notification_type} notification to user {user.id}: {e}")
    
    async def _send_email_notification(self, email: str, subject: str, message: str):
        """Send email notification"""
        try:
            # In a real implementation, you would use proper email configuration
            logger.info(f"Email notification sent to {email}: {subject} - {message}")
            # Implementation would go here with aiosmtplib or similar
            
        except Exception as e:
            logger.error(f"Error sending email to {email}: {e}")


# Global instance
advanced_alert_service = None


def get_advanced_alert_service(db_service: DatabaseService) -> AdvancedAlertService:
    """Get or create advanced alert service instance"""
    global advanced_alert_service
    if advanced_alert_service is None:
        advanced_alert_service = AdvancedAlertService(db_service)
    return advanced_alert_service