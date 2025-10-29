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