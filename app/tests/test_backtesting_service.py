"""Tests for BacktestingService"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backtesting_service import BacktestingService


@pytest.fixture
def sample_time_series():
    """Create sample time series data for testing"""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    return pd.Series(prices, index=dates, name="Close")


class TestBacktestingService:
    """Test cases for BacktestingService"""

    def test_init(self):
        """Test service initialization"""
        service = BacktestingService()
        assert service.forecasting_service is not None

    def test_calculate_metrics(self):
        """Test metrics calculation"""
        service = BacktestingService()

        y_true = np.array([100, 101, 102, 103, 104])
        y_pred = np.array([100.5, 101.2, 101.8, 103.1, 103.5])

        metrics = service.calculate_metrics(y_true, y_pred)

        assert "rmse" in metrics
        assert "mae" in metrics
        assert "mape" in metrics
        assert "r2_score" in metrics
        assert "direction_accuracy" in metrics
        assert metrics["rmse"] >= 0
        assert 0 <= metrics["direction_accuracy"] <= 1

    def test_calculate_metrics_perfect_prediction(self):
        """Test metrics with perfect prediction"""
        service = BacktestingService()

        y_true = np.array([100, 101, 102, 103, 104])
        y_pred = np.array([100, 101, 102, 103, 104])

        metrics = service.calculate_metrics(y_true, y_pred)

        assert metrics["rmse"] == 0.0
        assert metrics["mae"] == 0.0
        assert metrics["r2_score"] == 1.0
        assert metrics["direction_accuracy"] == 1.0

    def test_direction_accuracy(self):
        """Test direction accuracy calculation"""
        service = BacktestingService()

        # Perfect direction prediction
        y_true = np.array([100, 101, 102, 103, 104])
        y_pred = np.array([99, 100, 101, 102, 103])
        accuracy = service._calculate_direction_accuracy(y_true, y_pred)
        assert accuracy == 1.0

        # Mixed direction prediction - should be around 0.5-0.75
        y_pred_mixed = np.array([100.5, 100.8, 102.5, 102.2, 104.5])
        accuracy_mixed = service._calculate_direction_accuracy(y_true, y_pred_mixed)
        assert 0.0 <= accuracy_mixed <= 1.0

    def test_run_backtest_insufficient_data(self):
        """Test backtest with insufficient data"""
        service = BacktestingService()

        with pytest.raises(ValueError, match="Insufficient data"):
            service.run_backtest("NONEXISTENT", forecast_horizon=30)

    def test_compare_models(self):
        """Test model comparison"""
        service = BacktestingService()

        result = service.compare_models("NONEXISTENT", forecast_horizon=5)

        assert "symbol" in result
        assert "results" in result
        assert "best_model" in result
        assert result["symbol"] == "NONEXISTENT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
