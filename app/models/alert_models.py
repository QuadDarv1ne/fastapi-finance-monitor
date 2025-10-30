"""Pydantic models for alert functionality"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class AlertType(str, Enum):
    """Types of alerts that can be created"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    VOLUME_SPIKE = "volume_spike"
    PERCENTAGE_CHANGE = "percentage_change"
    TECHNICAL_INDICATOR = "technical_indicator"


class NotificationType(str, Enum):
    """Types of notifications that can be sent"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class AlertCondition(BaseModel):
    """Condition that triggers an alert"""
    type: AlertType
    threshold: float
    extra_params: Optional[Dict[str, Any]] = None


class AlertSchedule(BaseModel):
    """Schedule for when alerts should be active"""
    active_days: List[str]  # e.g., ["monday", "tuesday", ...]
    start_time: Optional[str]  # e.g., "09:30"
    end_time: Optional[str]  # e.g., "16:00"
    timezone: str = "UTC"


class AlertCreate(BaseModel):
    """Model for creating a new alert"""
    user_id: int
    symbol: str
    condition: AlertCondition
    notification_types: List[NotificationType]
    schedule: Optional[AlertSchedule] = None
    is_active: bool = True
    description: Optional[str] = None


class AlertUpdate(BaseModel):
    """Model for updating an existing alert"""
    condition: Optional[AlertCondition] = None
    notification_types: Optional[List[NotificationType]] = None
    schedule: Optional[AlertSchedule] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class AlertResponse(BaseModel):
    """Model for alert response"""
    id: int
    user_id: int
    symbol: str
    condition: AlertCondition
    notification_types: List[NotificationType]
    schedule: Optional[AlertSchedule] = None
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AlertTrigger(BaseModel):
    """Model for alert trigger event"""
    alert_id: int
    symbol: str
    triggered_at: datetime
    triggered_value: float
    condition_met: AlertCondition
    notification_sent: bool