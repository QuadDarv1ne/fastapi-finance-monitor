"""
Time Series Forecasting Service for Finance Monitor

This module provides ML-based forecasting capabilities for financial assets
using ARIMA, Exponential Smoothing, and Linear Regression models.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)


class ForecastingService:
    """Service for forecasting financial asset prices using time series analysis"""

    def __init__(self):
        """Initialize forecasting service with model cache"""
        self._model_cache: dict[str, dict[str, Any]] = {}

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature engineering for time series forecasting

        Creates lag features, rolling statistics, and returns from historical data.

        Args:
            df: DataFrame with 'Close' column

        Returns:
            DataFrame with additional features
        """
        try:
            df = df.copy()

            # Lag features
            for lag in [1, 2, 3, 5, 7]:
                df[f"lag_{lag}"] = df["Close"].shift(lag)

            # Rolling statistics
            for window in [5, 10, 20]:
                df[f"sma_{window}"] = df["Close"].rolling(window).mean()
                df[f"std_{window}"] = df["Close"].rolling(window).std()

            # Returns
            df["return_pct"] = df["Close"].pct_change()
            df["return_log"] = np.log(df["Close"] / df["Close"].shift(1))

            # EMA features
            df["ema_10"] = df["Close"].ewm(span=10).mean()
            df["ema_50"] = df["Close"].ewm(span=50).mean()

            return df.dropna()
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            raise

    def check_stationarity(self, series: pd.Series) -> dict[str, Any]:
        """
        Check if time series is stationary using Augmented Dickey-Fuller test

        Args:
            series: Time series data

        Returns:
            Dictionary with test results
        """
        try:
            result = adfuller(series.dropna(), autolag="AIC")
            return {
                "test_statistic": float(result[0]),
                "p_value": float(result[1]),
                "lags_used": int(result[2]),
                "observations": int(result[3]),
                "critical_values": {k: float(v) for k, v in result[4].items()},
                "is_stationary": result[1] < 0.05,
            }
        except Exception as e:
            logger.error(f"Error checking stationarity: {e}")
            return {
                "test_statistic": 0.0,
                "p_value": 1.0,
                "lags_used": 0,
                "observations": 0,
                "critical_values": {},
                "is_stationary": False,
            }

    def train_arima_model(self, series: pd.Series, order: tuple = (1, 1, 1)) -> tuple:
        """
        Train ARIMA model

        Args:
            series: Time series data
            order: ARIMA order (p, d, q)

        Returns:
            Tuple of (fitted_model, forecast)
        """
        try:
            model = ARIMA(series, order=order)
            fitted_model = model.fit()
            forecast = fitted_model.get_forecast(steps=30)
            return fitted_model, forecast
        except Exception as e:
            logger.error(f"Error training ARIMA model: {e}")
            raise

    def train_exponential_smoothing(self, series: pd.Series, seasonal_periods: int = 14) -> tuple:
        """
        Train Exponential Smoothing model

        Args:
            series: Time series data
            seasonal_periods: Number of periods in each season

        Returns:
            Tuple of (fitted_model, forecast)
        """
        try:
            model = ExponentialSmoothing(
                series, trend="add", seasonal="add", seasonal_periods=seasonal_periods
            )
            fitted_model = model.fit()
            forecast = fitted_model.forecast(steps=30)
            return fitted_model, forecast
        except Exception as e:
            logger.error(f"Error training Exponential Smoothing: {e}")
            raise

    def train_linear_regression(self, df: pd.DataFrame) -> tuple:
        """
        Train Linear Regression model for forecasting

        Args:
            df: DataFrame with features prepared by prepare_features()

        Returns:
            Tuple of (trained_model, X_test for evaluation)
        """
        try:
            feature_cols = [
                col
                for col in df.columns
                if col.startswith("lag_")
                or col.startswith("sma_")
                or col.startswith("std_")
                or col.startswith("return_")
                or col.startswith("ema_")
            ]

            if not feature_cols:
                raise ValueError("No feature columns found")

            X = df[feature_cols].dropna()
            y = df.loc[X.index, "Close"]

            model = LinearRegression()
            model.fit(X, y)

            return model, X
        except Exception as e:
            logger.error(f"Error training Linear Regression: {e}")
            raise

    def get_forecast(
        self, symbol: str, days_ahead: int = 30, model_type: str = "arima", order: tuple = (1, 1, 1)
    ) -> dict[str, Any]:
        """
        Get price forecast for an asset

        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'BTC-USD')
            days_ahead: Number of days to forecast
            model_type: Model type ('arima', 'exponential', 'linear')
            order: ARIMA order (only for arima model)

        Returns:
            Dictionary with forecast data
        """
        try:
            # Load historical data from database
            from app.database import SessionLocal
            from app.services.database_service import DatabaseService

            db = SessionLocal()
            try:
                db_service = DatabaseService(db)

                # Get historical data
                history = db_service.get_historical_data(symbol, days_ahead + 90)
            finally:
                db.close()

            if history.empty:
                raise ValueError(f"No historical data available for {symbol}")

            # Prepare features
            df = self.prepare_features(history)

            if len(df) < 50:
                raise ValueError(f"Insufficient data for forecasting {symbol}")

            # Train model and get forecast
            if model_type == "arima":
                model, forecast = self.train_arima_model(df["Close"], order)
                forecast_values = forecast.predicted_mean.values[:days_ahead]
                conf_int = forecast.conf_int().values[:days_ahead]

            elif model_type == "exponential":
                model, forecast_values = self.train_exponential_smoothing(df["Close"])
                conf_int = None

            elif model_type == "linear":
                model, X_test = self.train_linear_regression(df)
                # Get last row of features
                last_features = X_test.iloc[-1:].values
                forecast_values = []
                current_price = df["Close"].iloc[-1]

                for _ in range(days_ahead):
                    pred = model.predict(last_features)[0]
                    forecast_values.append(pred)
                    # Update features for next step
                    last_features[0, 0] = current_price  # lag_1
                    current_price = pred

                forecast_values = np.array(forecast_values)
                conf_int = None

            else:
                raise ValueError(f"Unknown model type: {model_type}")

            # Generate timestamps for forecast
            last_date = df.index[-1] if hasattr(df.index, "__getitem__") else datetime.now(UTC)
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), periods=days_ahead, freq="D"
            )

            result = {
                "symbol": symbol,
                "model_type": model_type,
                "forecast_dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "forecast_values": forecast_values.tolist(),
                "current_price": float(df["Close"].iloc[-1]),
                "timestamp": datetime.now(UTC).isoformat(),
                "confidence_intervals": conf_int.tolist() if conf_int is not None else None,
            }

            # Cache the model
            self._model_cache[symbol] = {"model": model, "trained_at": datetime.now(UTC)}

            return result

        except Exception as e:
            logger.error(f"Error getting forecast for {symbol}: {e}")
            raise

    def retrain_model(self, symbol: str) -> bool:
        """
        Force retrain model for a specific symbol

        Args:
            symbol: Asset symbol

        Returns:
            True if retrained successfully
        """
        try:
            # Remove from cache to force retraining
            if symbol in self._model_cache:
                del self._model_cache[symbol]
            return True
        except Exception as e:
            logger.error(f"Error retraining model for {symbol}: {e}")
            return False

    def get_model_accuracy(self, symbol: str) -> dict[str, Any]:
        """
        Get model accuracy metrics for a symbol

        Args:
            symbol: Asset symbol

        Returns:
            Dictionary with accuracy metrics
        """
        try:
            if symbol not in self._model_cache:
                return {
                    "symbol": symbol,
                    "trained_at": None,
                    "accuracy": None,
                    "message": "Model not trained yet",
                }

            model_info = self._model_cache[symbol]
            trained_at = model_info["trained_at"]

            # TODO: Implement proper accuracy calculation with backtesting
            # For now, return basic info
            return {
                "symbol": symbol,
                "trained_at": trained_at.isoformat() if trained_at else None,
                "accuracy": None,
                "message": "Model trained successfully",
            }

        except Exception as e:
            logger.error(f"Error getting model accuracy for {symbol}: {e}")
            return {"symbol": symbol, "trained_at": None, "accuracy": None, "error": str(e)}


# Singleton instance
_forecasting_service_instance = None


def get_forecasting_service() -> ForecastingService:
    """Get or create ForecastingService singleton instance"""
    global _forecasting_service_instance
    if _forecasting_service_instance is None:
        _forecasting_service_instance = ForecastingService()
    return _forecasting_service_instance
