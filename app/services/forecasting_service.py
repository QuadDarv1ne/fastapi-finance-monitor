"""
Time Series Forecasting Service for Finance Monitor

This module provides ML-based forecasting capabilities for financial assets
using ARIMA, Exponential Smoothing, Linear Regression, and baseline methods.
Includes grid search for ARIMA parameters and TimeSeriesSplit cross-validation.
"""

import itertools
import logging
import warnings
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


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
            result = adfuller(series.dropna(), autolag="AIC", result_object=False)
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

    # ------------------------------------------------------------------
    # Baseline forecasting methods
    # ------------------------------------------------------------------

    @staticmethod
    def naive_forecast(series: pd.Series, steps: int) -> np.ndarray:
        """
        Naive forecast: 'tomorrow = yesterday'.

        Args:
            series: Historical time series
            steps: Number of forecast steps

        Returns:
            Array of forecasted values
        """
        last_value = series.iloc[-1]
        return np.full(steps, last_value)

    @staticmethod
    def rolling_mean_forecast(series: pd.Series, window: int, steps: int) -> np.ndarray:
        """
        Rolling mean forecast: predict using average of last `window` values.

        Args:
            series: Historical time series
            window: Number of recent values to average
            steps: Number of forecast steps

        Returns:
            Array of forecasted values
        """
        if len(series) < window:
            window = len(series)
        mean_value = series.iloc[-window:].mean()
        return np.full(steps, mean_value)

    @staticmethod
    def weighted_moving_average_forecast(
        series: pd.Series, weights: np.ndarray, steps: int
    ) -> np.ndarray:
        """
        Weighted moving average forecast.

        Newer observations have higher weights. Weights must sum to 1.

        Args:
            series: Historical time series
            weights: Array of weights (newest first)
            steps: Number of forecast steps

        Returns:
            Array of forecasted values
        """
        n = len(weights)
        if len(series) < n:
            n = len(series)
            weights = weights[:n]

        recent = series.iloc[-n:].values
        weighted_avg = np.dot(weights, recent) / weights.sum()
        return np.full(steps, weighted_avg)

    # ------------------------------------------------------------------
    # Advanced forecasting methods
    # ------------------------------------------------------------------

    def triple_exponential_smoothing(
        self,
        series: pd.Series,
        seasonal_periods: int = 24,
        trend: str = "add",
        seasonal: str = "add",
        steps: int = 30,
    ) -> tuple:
        """
        Triple exponential smoothing (Holt-Winters) with trend and seasonality.

        Args:
            series: Time series data
            seasonal_periods: Number of periods in a season
            trend: Type of trend ('add' or 'mul')
            seasonal: Type of seasonality ('add' or 'mul')
            steps: Number of forecast steps

        Returns:
            Tuple of (fitted_model, forecast_series)
        """
        try:
            model = ExponentialSmoothing(
                np.asarray(series),
                seasonal_periods=seasonal_periods,
                trend=trend,
                seasonal=seasonal,
            )
            fitted_model = model.fit()
            forecast = pd.Series(fitted_model.forecast(steps))
            return fitted_model, forecast
        except Exception as e:
            logger.error(f"Error in triple exponential smoothing: {e}")
            raise

    def grid_search_arima(
        self,
        series: pd.Series,
        p_range: range = range(0, 5),
        d_range: range = range(0, 3),
        q_range: range = range(0, 5),
    ) -> dict[str, Any]:
        """
        Grid search for best ARIMA parameters by RMSE.

        Args:
            series: Time series data
            p_range: Range of AR orders
            d_range: Range of differencing orders
            q_range: Range of MA orders

        Returns:
            Dictionary with best params and all results
        """
        try:
            pdq = list(itertools.product(p_range, d_range, q_range))
            best_params = (0, 0, 0)
            best_rmse = np.inf
            all_results = []

            for params in pdq:
                try:
                    model = ARIMA(series, order=params)
                    result = model.fit()
                    predictions = result.predict(dynamic=False)

                    # Calculate in-sample RMSE
                    actual = series.values
                    predicted = np.array(predictions)
                    min_len = min(len(actual), len(predicted))
                    rmse_val = float(np.sqrt(np.mean((actual[:min_len] - predicted[:min_len]) ** 2)))

                    all_results.append({"order": list(params), "rmse": round(rmse_val, 4)})

                    if rmse_val < best_rmse:
                        best_rmse = rmse_val
                        best_params = params
                except Exception:
                    continue

            return {
                "best_order": list(best_params),
                "best_rmse": round(best_rmse, 4),
                "total_tried": len(pdq),
                "total_successful": len(all_results),
                "top_5": sorted(all_results, key=lambda x: x["rmse"])[:5],
            }

        except Exception as e:
            logger.error(f"Error in ARIMA grid search: {e}")
            raise

    def timeseries_cross_validate(
        self,
        series: pd.Series,
        n_splits: int = 4,
        model_type: str = "exponential",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Cross-validation for time series using TimeSeriesSplit.

        Args:
            series: Time series data
            n_splits: Number of CV splits
            model_type: Model type to use for CV
            **kwargs: Additional model parameters

        Returns:
            Dictionary with CV results
        """
        try:
            errors = []
            tscv = TimeSeriesSplit(n_splits=n_splits)

            for train_idx, test_idx in tscv.split(series):
                train = series.iloc[train_idx]
                test = series.iloc[test_idx]

                try:
                    if model_type == "exponential":
                        seasonal_periods = kwargs.get("seasonal_periods", 24)
                        model = ExponentialSmoothing(
                            np.asarray(train),
                            seasonal_periods=seasonal_periods,
                            trend="add",
                            seasonal="add",
                        ).fit()
                        forecast = pd.Series(model.forecast(len(test)))
                    elif model_type == "arima":
                        order = kwargs.get("order", (1, 1, 1))
                        model = ARIMA(train, order=order).fit()
                        forecast = model.forecast(steps=len(test))
                    elif model_type == "naive":
                        forecast = pd.Series(
                            np.full(len(test), train.iloc[-1])
                        )
                    elif model_type == "rolling_mean":
                        window = kwargs.get("window", 10)
                        mean_val = train.iloc[-window:].mean()
                        forecast = pd.Series(np.full(len(test), mean_val))
                    else:
                        raise ValueError(f"Unknown model type for CV: {model_type}")

                    actual = test.values
                    predicted = forecast.values[: len(actual)]
                    min_len = min(len(actual), len(predicted))
                    rmse_val = float(np.sqrt(np.mean((actual[:min_len] - predicted[:min_len]) ** 2)))
                    errors.append(rmse_val)

                except Exception as e:
                    logger.warning(f"CV fold failed: {e}")
                    continue

            if not errors:
                raise ValueError("All CV folds failed")

            return {
                "model_type": model_type,
                "n_splits": n_splits,
                "folds_completed": len(errors),
                "rmse_per_fold": [round(e, 4) for e in errors],
                "mean_rmse": round(float(np.mean(errors)), 4),
                "std_rmse": round(float(np.std(errors)), 4),
            }

        except Exception as e:
            logger.error(f"Error in time series cross-validation: {e}")
            raise

    def train_linear_regression_enhanced(
        self, df: pd.DataFrame
    ) -> tuple:
        """
        Train enhanced Linear Regression using OHLC features.

        Uses High, Low, Open, Adj Close columns when available.

        Args:
            df: DataFrame with OHLC columns

        Returns:
            Tuple of (model, scaler, feature_cols)
        """
        try:
            # Prefer OHLC features
            ohlc_cols = [c for c in ["High", "Low", "Open", "Adj Close"] if c in df.columns]
            if len(ohlc_cols) >= 2:
                feature_cols = ohlc_cols
            else:
                # Fall back to lag-based features
                feature_cols = [
                    col
                    for col in df.columns
                    if col.startswith(("lag_", "sma_", "std_", "return_", "ema_"))
                ]

            if not feature_cols:
                raise ValueError("No feature columns found")

            X = df[feature_cols].dropna()
            y = df.loc[X.index, "Close"]

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = LinearRegression()
            model.fit(X_scaled, y)

            return model, scaler, feature_cols

        except Exception as e:
            logger.error(f"Error training enhanced Linear Regression: {e}")
            raise

    def compare_all_baselines(
        self, series: pd.Series, forecast_horizon: int = 30
    ) -> dict[str, Any]:
        """
        Compare all baseline and ML forecasting methods.

        Args:
            series: Historical time series
            forecast_horizon: Number of days to forecast

        Returns:
            Dictionary with comparison results
        """
        try:
            # Split data
            split_point = int(len(series) * 0.8)
            train = series.iloc[:split_point]
            test = series.iloc[split_point:]

            if len(test) < forecast_horizon:
                forecast_horizon = len(test)

            actual = test.values[:forecast_horizon]
            results = {}

            # Naive
            naive_pred = self.naive_forecast(train, forecast_horizon)
            results["naive"] = self._calc_rmse_mape(actual, naive_pred)

            # Rolling mean
            for window in [5, 10, 20]:
                rm_pred = self.rolling_mean_forecast(train, window, forecast_horizon)
                results[f"rolling_mean_{window}"] = self._calc_rmse_mape(actual, rm_pred)

            # Weighted moving average
            weights = np.array([0.001, 0.004, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.26, 0.4])
            wma_pred = self.weighted_moving_average_forecast(train, weights, forecast_horizon)
            results["weighted_ma"] = self._calc_rmse_mape(actual, wma_pred)

            # Triple exponential smoothing
            try:
                _, hw_forecast = self.triple_exponential_smoothing(
                    train, seasonal_periods=24, steps=forecast_horizon
                )
                results["holt_winters"] = self._calc_rmse_mape(actual, hw_forecast.values)
            except Exception as e:
                results["holt_winters"] = {"error": str(e)}

            # ARIMA
            try:
                model = ARIMA(train, order=(1, 1, 1)).fit()
                arima_forecast = model.get_forecast(steps=forecast_horizon)
                results["arima_1_1_1"] = self._calc_rmse_mape(
                    actual, arima_forecast.predicted_mean.values
                )
            except Exception as e:
                results["arima_1_1_1"] = {"error": str(e)}

            # Find best model
            valid = {k: v for k, v in results.items() if "rmse" in v}
            best_model = min(valid.items(), key=lambda x: x[1]["rmse"])[0] if valid else "none"

            return {
                "forecast_horizon": forecast_horizon,
                "train_size": len(train),
                "test_size": forecast_horizon,
                "results": results,
                "best_model": best_model,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error comparing baselines: {e}")
            raise

    @staticmethod
    def _calc_rmse_mape(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
        """Calculate RMSE and MAPE for a pair of arrays."""
        min_len = min(len(actual), len(predicted))
        a = actual[:min_len]
        p = predicted[:min_len]
        rmse_val = float(np.sqrt(np.mean((a - p) ** 2)))
        safe_a = np.maximum(np.abs(a), 1e-8)
        mape_val = float(np.mean(np.abs((a - p) / safe_a)) * 100)
        return {"rmse": round(rmse_val, 4), "mape": round(mape_val, 2)}


# Singleton instance
_forecasting_service_instance = None


def get_forecasting_service() -> ForecastingService:
    """Get or create ForecastingService singleton instance"""
    global _forecasting_service_instance
    if _forecasting_service_instance is None:
        _forecasting_service_instance = ForecastingService()
    return _forecasting_service_instance