"""
Backtesting service for evaluating forecasting models
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.services.forecasting_service import ForecastingService

logger = logging.getLogger(__name__)


class BacktestingService:
    """Service for backtesting forecasting models on historical data"""

    def __init__(self):
        self.forecasting_service = ForecastingService()

    def calculate_metrics(self, y_true, y_pred):
        """Calculate forecasting accuracy metrics"""
        try:
            y_true = np.array(y_true)
            y_pred = np.array(y_pred)

            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            mae = float(mean_absolute_error(y_true, y_pred))
            r2 = float(r2_score(y_true, y_pred))

            safe_true = np.maximum(np.abs(y_true), 1e-8)
            mape = float(np.mean(np.abs((y_true - y_pred) / safe_true)) * 100)

            smape = float(
                np.mean(2 * np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred) + 1e-8))
                * 100
            )

            return {
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "mape": round(mape, 2),
                "smape": round(smape, 2),
                "r2_score": round(r2, 4),
                "direction_accuracy": self._calculate_direction_accuracy(y_true, y_pred),
            }
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "rmse": 0.0,
                "mae": 0.0,
                "mape": 0.0,
                "smape": 0.0,
                "r2_score": 0.0,
                "direction_accuracy": 0.0,
            }

    def _calculate_direction_accuracy(self, y_true, y_pred):
        """Calculate how often model correctly predicted price direction"""
        try:
            if len(y_true) < 2 or len(y_pred) < 2:
                return 0.0
            actual_direction = np.diff(y_true) > 0
            predicted_direction = np.diff(y_pred) > 0
            return float(np.mean(actual_direction == predicted_direction))
        except Exception as e:
            logger.error(f"Error calculating direction accuracy: {e}")
            return 0.0

    def run_backtest(
        self, symbol, model_type="arima", train_ratio=0.8, forecast_horizon=30, **kwargs
    ):
        """Run backtest on historical data"""
        try:
            from app.database import SessionLocal
            from app.services.database_service import DatabaseService

            db = SessionLocal()
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(symbol, days=365)

            if history.empty or len(history) < 100:
                raise ValueError(f"Insufficient data for backtesting {symbol}")

            split_point = int(len(history) * train_ratio)
            train_data = history.iloc[:split_point]
            test_data = history.iloc[split_point:]

            if len(test_data) < forecast_horizon:
                raise ValueError(f"Test data too short for {forecast_horizon}-day forecast")

            train_features = self.forecasting_service.prepare_features(train_data)

            if len(train_features) < 50:
                raise ValueError("Insufficient training data after feature engineering")

            if model_type == "arima":
                order = kwargs.get("order", (1, 1, 1))
                model, forecast = self.forecasting_service.train_arima_model(
                    train_features["Close"], order
                )
                predicted = forecast.predicted_mean.values[:forecast_horizon]

            elif model_type == "exponential":
                seasonal_periods = kwargs.get("seasonal_periods", 14)
                model, predicted = self.forecasting_service.train_exponential_smoothing(
                    train_features["Close"], seasonal_periods
                )
                predicted = predicted.values[:forecast_horizon]

            elif model_type == "linear":
                model, X_test = self.forecasting_service.train_linear_regression(train_features)
                predicted = []
                last_features = X_test.iloc[-1:].values
                current_price = train_features["Close"].iloc[-1]

                for _ in range(forecast_horizon):
                    pred = model.predict(last_features)[0]
                    predicted.append(pred)
                    last_features[0, 0] = current_price
                    current_price = pred
                predicted = np.array(predicted)
            else:
                raise ValueError(f"Unknown model type: {model_type}")

            actual = test_data["Close"].values[:forecast_horizon]
            metrics = self.calculate_metrics(actual, predicted)

            last_train_date = train_features.index[-1]
            forecast_dates = pd.date_range(
                start=last_train_date + pd.Timedelta(days=1), periods=forecast_horizon, freq="D"
            )

            return {
                "symbol": symbol,
                "model_type": model_type,
                "train_period": {
                    "start": train_data.index[0].strftime("%Y-%m-%d"),
                    "end": train_data.index[-1].strftime("%Y-%m-%d"),
                    "length": len(train_data),
                },
                "test_period": {
                    "start": test_data.index[0].strftime("%Y-%m-%d"),
                    "end": test_data.index[-1].strftime("%Y-%m-%d"),
                    "length": len(test_data),
                },
                "forecast_horizon": forecast_horizon,
                "metrics": metrics,
                "predictions": {
                    "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                    "predicted": predicted.tolist(),
                    "actual": actual.tolist(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error running backtest for {symbol}: {e}")
            raise

    def compare_models(self, symbol, forecast_horizon=30):
        """Compare different models on the same data"""
        try:
            results = {}
            for model_type in ["arima", "exponential", "linear"]:
                try:
                    result = self.run_backtest(
                        symbol=symbol, model_type=model_type, forecast_horizon=forecast_horizon
                    )
                    results[model_type] = {
                        "rmse": result["metrics"]["rmse"],
                        "mape": result["metrics"]["mape"],
                        "r2_score": result["metrics"]["r2_score"],
                        "direction_accuracy": result["metrics"]["direction_accuracy"],
                    }
                except Exception as e:
                    logger.warning(f"Model {model_type} failed for {symbol}: {e}")
                    results[model_type] = {"error": str(e)}

            valid_models = {k: v for k, v in results.items() if "error" not in v}
            best_model = (
                min(valid_models.items(), key=lambda x: x[1]["rmse"])[0] if valid_models else "none"
            )

            return {
                "symbol": symbol,
                "forecast_horizon": forecast_horizon,
                "results": results,
                "best_model": best_model,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error comparing models for {symbol}: {e}")
            raise


_backtesting_service_instance = None


def get_backtesting_service():
    """Get or create BacktestingService singleton instance"""
    global _backtesting_service_instance
    if _backtesting_service_instance is None:
        _backtesting_service_instance = BacktestingService()
    return _backtesting_service_instance
