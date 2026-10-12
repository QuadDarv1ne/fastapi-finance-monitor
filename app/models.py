"""Pydantic models for data validation"""

import re
from typing import Any, Optional

from pydantic import BaseModel, field_validator


class AssetBase(BaseModel):
    symbol: str
    name: str
    type: str


class ChartDataPoint(BaseModel):
    time: str
    price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


class AssetData(AssetBase):
    timestamp: str
    current_price: float
    change: float | None = None
    change_percent: float
    volume: int | None = None
    chart_data: list[ChartDataPoint]


class WebSocketMessage(BaseModel):
    type: str
    data: list[AssetData]
    timestamp: str


class AssetResponse(BaseModel):
    assets: list[AssetData]


class HealthCheck(BaseModel):
    status: str
    message: str


# Request models
class UserRegistrationRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Username must be less than 50 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password must be less than 128 characters")
        return v


class EmailVerificationRequest(BaseModel):
    token: str


class AlertCreateRequest(BaseModel):
    symbol: str
    alert_type: str
    threshold: float
    extra_params: dict[str, Any] | None = None
    notification_types: list[str]
    schedule: dict[str, Any] | None = None
    description: str | None = None


class PortfolioCreateRequest(BaseModel):
    name: str
    items: list[dict[str, Any]] = []


class WatchlistCreateRequest(BaseModel):
    name: str
    symbols: list[str] = []


class AssetAddRequest(BaseModel):
    symbol: str
    name: str
    asset_type: str
    quantity: float = 1.0
    purchase_price: float | None = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v

    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Purchase price cannot be negative")
        return v


class AssetRemoveRequest(BaseModel):
    symbol: str


# Forecasting models
class ForecastRequest(BaseModel):
    symbol: str
    days_ahead: int = 30
    model_type: str = "arima"  # arima, exponential, linear
    order: list[int] = [1, 1, 1]


class ForecastResponse(BaseModel):
    symbol: str
    model_type: str
    forecast_dates: list[str]
    forecast_values: list[float]
    current_price: float
    confidence_intervals: list[list[float]] | None = None
    timestamp: str


class ModelAccuracyResponse(BaseModel):
    symbol: str
    trained_at: str | None = None
    accuracy: float | None = None
    message: str | None = None


# Clustering models
class ClusteringRequest(BaseModel):
    symbol: str
    window_size: int = 30
    k_min: int = 2
    k_max: int = 10


class GridSearchRequest(BaseModel):
    symbol: str
    p_max: int = 5
    d_max: int = 3
    q_max: int = 5


class BaselineComparisonRequest(BaseModel):
    symbol: str
    forecast_horizon: int = 30


class CrossValidationRequest(BaseModel):
    symbol: str
    n_splits: int = 4
    model_type: str = "exponential"


# 2FA Request/Response models
class TwoFactorAuthEnableRequest(BaseModel):
    password: str


class TwoFactorAuthVerifyRequest(BaseModel):
    otp: str


class TwoFactorAuthDisableRequest(BaseModel):
    otp: str


class TwoFactorAuthResponse(BaseModel):
    is_enabled: bool
    secret: str | None = None
    qr_code: str | None = None
    backup_codes: list[str] | None = None
    message: str


class TwoFactorAuthVerifyResponse(BaseModel):
    success: bool
    message: str
    access_token: str | None = None
    token_type: str | None = None


# Database models
from datetime import UTC
from datetime import datetime as _datetime


def _utcnow() -> _datetime:
    """Return current UTC time as naive datetime for DB storage."""
    return _datetime.now(UTC).replace(tzinfo=None)


from typing import Annotated

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

IntPk = Annotated[int, mapped_column(primary_key=True, index=True)]


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Email verification status

    # 2FA fields
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String, nullable=True)  # Encrypted TOTP secret

    # Telegram connect token hash (used to validate /start links)
    telegram_connect_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    watchlists: Mapped[list["Watchlist"]] = relationship(
        "Watchlist", back_populates="user", passive_deletes=True
    )
    portfolios: Mapped[list["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", passive_deletes=True
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="user", passive_deletes=True
    )
    telegram_connection: Mapped[Optional["TelegramConnection"]] = relationship(
        "TelegramConnection", back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="watchlists")
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem", back_populates="watchlist", passive_deletes=True
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    watchlist_id: Mapped[int] = mapped_column(Integer, ForeignKey("watchlists.id"))
    symbol: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    asset_type: Mapped[str] = mapped_column(String)
    added_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    watchlist: Mapped[Watchlist] = relationship("Watchlist", back_populates="watchlist_items")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="portfolios")
    portfolio_items: Mapped[list["PortfolioItem"]] = relationship(
        "PortfolioItem", back_populates="portfolio", passive_deletes=True
    )


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"))
    symbol: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float)
    purchase_price: Mapped[float] = mapped_column(Float)
    purchase_date: Mapped[_datetime] = mapped_column(DateTime)
    asset_type: Mapped[str] = mapped_column(String)

    # Relationships
    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="portfolio_items")


class AssetHistoricalData(Base):
    __tablename__ = "asset_historical_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[_datetime] = mapped_column(DateTime, index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    asset_type: Mapped[str] = mapped_column(String)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    symbol: Mapped[str] = mapped_column(String, index=True)
    alert_type: Mapped[str] = mapped_column(String)  # price_above, price_below, etc.
    threshold: Mapped[float] = mapped_column(Float)
    extra_params: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string for additional parameters
    notification_types: Mapped[str] = mapped_column(Text)  # JSON string array
    schedule: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for schedule
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="alerts")
    trigger_history: Mapped[list["AlertTriggerHistory"]] = relationship(
        "AlertTriggerHistory", back_populates="alert", passive_deletes=True
    )


class AlertTriggerHistory(Base):
    __tablename__ = "alert_trigger_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id"))
    triggered_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)
    triggered_value: Mapped[float] = mapped_column(Float)
    condition_met: Mapped[str] = mapped_column(Text)  # JSON string of the condition that was met
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    alert: Mapped[Alert] = relationship("Alert", back_populates="trigger_history")


class TelegramConnection(Base):
    __tablename__ = "telegram_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)
    last_notification_at: Mapped[_datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="telegram_connection")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    expires_at: Mapped[_datetime] = mapped_column(DateTime, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[_datetime] = mapped_column(DateTime, default=_utcnow)
    revoked_at: Mapped[_datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")
