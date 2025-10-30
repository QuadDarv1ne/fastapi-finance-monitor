"""Pydantic models for data validation"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class AssetBase(BaseModel):
    symbol: str
    name: str
    type: str


class ChartDataPoint(BaseModel):
    time: str
    price: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


class AssetData(AssetBase):
    timestamp: str
    current_price: float
    change: Optional[float] = None
    change_percent: float
    volume: Optional[int] = None
    chart_data: List[ChartDataPoint]


class WebSocketMessage(BaseModel):
    type: str
    data: List[AssetData]
    timestamp: str


class AssetResponse(BaseModel):
    assets: List[AssetData]


class HealthCheck(BaseModel):
    status: str
    message: str


# Database models
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlists = relationship("Watchlist", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")


class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    watchlist_items = relationship("WatchlistItem", back_populates="watchlist")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"))
    symbol = Column(String, index=True)
    name = Column(String)
    asset_type = Column(String)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="watchlist_items")


class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    portfolio_items = relationship("PortfolioItem", back_populates="portfolio")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String, index=True)
    name = Column(String)
    quantity = Column(Float)
    purchase_price = Column(Float)
    purchase_date = Column(DateTime)
    asset_type = Column(String)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="portfolio_items")


class AssetHistoricalData(Base):
    __tablename__ = "asset_historical_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)
    asset_type = Column(String)


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, index=True)
    alert_type = Column(String)  # price_above, price_below, etc.
    threshold = Column(Float)
    extra_params = Column(Text, nullable=True)  # JSON string for additional parameters
    notification_types = Column(Text)  # JSON string array
    schedule = Column(Text, nullable=True)  # JSON string for schedule
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="alerts")


class AlertTriggerHistory(Base):
    __tablename__ = "alert_trigger_history"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    triggered_at = Column(DateTime, default=datetime.utcnow)
    triggered_value = Column(Float)
    condition_met = Column(Text)  # JSON string of the condition that was met
    notification_sent = Column(Boolean, default=False)
    
    # Relationships
    alert = relationship("Alert", back_populates="trigger_history")


# Add relationships to User model
User.alerts = relationship("Alert", back_populates="user")
Alert.trigger_history = relationship("AlertTriggerHistory", back_populates="alert")