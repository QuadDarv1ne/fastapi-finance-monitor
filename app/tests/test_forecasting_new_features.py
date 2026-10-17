"""Tests for new forecasting methods and clustering service"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.clustering_service import ClusteringService
from app.services.forecasting_service import ForecastingService

# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def sample_time_series():
    """Create sample time series data for testing"""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    # Add trend + noise
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5) + np.linspace(0, 10, 200)
    return pd.Series(prices, index=dates, name="Close")


@pytest.fixture
def sample_ohlcv_dataframe():
    """Create sample OHLCV DataFrame for testing"""
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    close = 100 + np.cumsum(np.random.randn(200) * 0.5)
    data = {
        "Open": close + np.random.randn(200) * 0.3,
        "High": close + np.abs(np.random.randn(200)),
        "Low": close - np.abs(np.random.randn(200)),
        "Close": close,
        "Volume": np.random.randint(1000000, 10000000, 200),
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = "Date"
    return df


# ------------------------------------------------------------------ #
# Baseline forecasting tests
# ------------------------------------------------------------------ #


class TestBaselineForecasting:
    """Tests for baseline forecasting methods"""

    def test_naive_forecast(self, sample_time_series):
        """Test naive forecast: all predictions equal last value"""
        service = ForecastingService()
        forecast = service.naive_forecast(sample_time_series, steps=10)

        assert len(forecast) == 10
        assert np.allclose(forecast, sample_time_series.iloc[-1])

    def test_rolling_mean_forecast_default_window(self, sample_time_series):
        """Test rolling mean forecast with default window"""
        service = ForecastingService()
        forecast = service.rolling_mean_forecast(sample_time_series, window=10, steps=5)

        assert len(forecast) == 5
        expected = sample_time_series.iloc[-10:].mean()
        assert np.isclose(forecast[0], expected)

    def test_rolling_mean_forecast_short_series(self, sample_time_series):
        """Test rolling mean with window larger than series"""
        service = ForecastingService()
        short_series = sample_time_series.iloc[:5]
        forecast = service.rolling_mean_forecast(short_series, window=10, steps=3)

        assert len(forecast) == 3
        # Should use all available data
        assert np.isclose(forecast[0], short_series.mean())

    def test_weighted_moving_average_forecast(self, sample_time_series):
        """Test weighted MA forecast"""
        service = ForecastingService()
        weights = np.array([0.1, 0.3, 0.6])
        forecast = service.weighted_moving_average_forecast(
            sample_time_series, weights, steps=5
        )

        assert len(forecast) == 5
        expected = np.dot(sample_time_series.iloc[-3:].values, weights) / weights.sum()
        assert np.isclose(forecast[0], expected)

    def test_weighted_moving_average_short_series(self, sample_time_series):
        """Test WMA when series is shorter than weights"""
        service = ForecastingService()
        weights = np.array([0.1, 0.3, 0.6, 0.9])
        short_series = sample_time_series.iloc[:3]
        forecast = service.weighted_moving_average_forecast(short_series, weights, steps=2)

        assert len(forecast) == 2
        # Should use only first 3 weights
        adjusted_weights = weights[:3]
        expected = np.dot(short_series.values, adjusted_weights) / adjusted_weights.sum()
        assert np.isclose(forecast[0], expected)


# ------------------------------------------------------------------ #
# Advanced forecasting tests
# ------------------------------------------------------------------ #


class TestAdvancedForecasting:
    """Tests for advanced forecasting methods"""

    def test_triple_exponential_smoothing(self, sample_time_series):
        """Test Holt-Winters triple exponential smoothing"""
        service = ForecastingService()
        model, forecast = service.triple_exponential_smoothing(
            sample_time_series, seasonal_periods=10, steps=5
        )

        assert model is not None
        assert len(forecast) == 5

    def test_triple_exponential_smoothing_trend_mul(self, sample_time_series):
        """Test exponential smoothing with multiplicative trend"""
        service = ForecastingService()
        model, forecast = service.triple_exponential_smoothing(
            sample_time_series, trend="mul", steps=5
        )

        assert model is not None
        assert len(forecast) == 5

    def test_grid_search_arima_small(self, sample_time_series):
        """Test ARIMA grid search with small ranges"""
        service = ForecastingService()
        result = service.grid_search_arima(
            sample_time_series,
            p_range=range(0, 3),
            d_range=range(0, 2),
            q_range=range(0, 2),
        )

        assert "best_order" in result
        assert "best_rmse" in result
        assert "total_tried" in result
        assert "total_successful" in result
        assert "top_5" in result
        assert len(result["best_order"]) == 3
        assert result["total_successful"] > 0

    def test_grid_search_arima_empty_result(self):
        """Test grid search with impossible data"""
        service = ForecastingService()
        # Constant series
        constant = pd.Series([100.0] * 50)
        result = service.grid_search_arima(
            constant, p_range=range(0, 2), d_range=range(0, 2), q_range=range(0, 2)
        )
        # Should handle gracefully
        assert result["total_successful"] >= 0

    def test_timeseries_cross_validate_exponential(self, sample_time_series):
        """Test TimeSeriesSplit cross-validation with exponential smoothing"""
        service = ForecastingService()
        result = service.timeseries_cross_validate(
            sample_time_series, n_splits=3, model_type="exponential"
        )

        assert result["model_type"] == "exponential"
        assert result["n_splits"] == 3
        assert result["folds_completed"] > 0
        assert "rmse_per_fold" in result
        assert "mean_rmse" in result
        assert "std_rmse" in result

    def test_timeseries_cross_validate_naive(self, sample_time_series):
        """Test CV with naive method"""
        service = ForecastingService()
        result = service.timeseries_cross_validate(
            sample_time_series, n_splits=3, model_type="naive"
        )

        assert result["folds_completed"] > 0
        assert len(result["rmse_per_fold"]) == result["folds_completed"]

    def test_timeseries_cross_validate_rolling_mean(self, sample_time_series):
        """Test CV with rolling mean method"""
        service = ForecastingService()
        result = service.timeseries_cross_validate(
            sample_time_series,
            n_splits=3,
            model_type="rolling_mean",
            window=10,
        )

        assert result["folds_completed"] > 0

    def test_timeseries_cross_validate_invalid_model(self, sample_time_series):
        """Test CV with invalid model type"""
        service = ForecastingService()
        with pytest.raises(ValueError):
            service.timeseries_cross_validate(
                sample_time_series, n_splits=2, model_type="invalid_model"
            )

    def test_train_linear_regression_enhanced(self, sample_ohlcv_dataframe):
        """Test enhanced linear regression with OHLC features"""
        service = ForecastingService()
        model, scaler, feature_cols = service.train_linear_regression_enhanced(
            sample_ohlcv_dataframe
        )

        assert model is not None
        assert scaler is not None
        assert len(feature_cols) > 0
        # Should use OHLC columns
        assert "Open" in feature_cols or "High" in feature_cols

    def test_train_linear_regression_enhanced_no_ohlc(self, sample_time_series):
        """Test enhanced LR with only Close column (no OHLC)"""
        service = ForecastingService()
        # Prepare features first (adds lag features)
        df_features = service.prepare_features(
            pd.DataFrame({"Close": sample_time_series})
        )

        model, _scaler, feature_cols = service.train_linear_regression_enhanced(
            df_features
        )

        assert model is not None
        assert len(feature_cols) > 0
        # Should fall back to lag features
        assert any("lag" in col for col in feature_cols)


# ------------------------------------------------------------------ #
# Baseline comparison tests
# ------------------------------------------------------------------ #


class TestBaselineComparison:
    """Tests for baseline comparison functionality"""

    def test_compare_all_baselines(self, sample_time_series):
        """Test comparison of all baseline methods"""
        service = ForecastingService()
        result = service.compare_all_baselines(sample_time_series, forecast_horizon=10)

        assert "results" in result
        assert "best_model" in result
        assert "forecast_horizon" in result
        assert "train_size" in result
        assert "test_size" in result

        # Check that all methods are present
        assert "naive" in result["results"]
        assert "weighted_ma" in result["results"]
        assert "holt_winters" in result["results"]
        assert "arima_1_1_1" in result["results"]

    def test_compare_all_baselines_short_series(self):
        """Test comparison with very short series — should handle gracefully"""
        service = ForecastingService()
        short_series = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

        # Method handles short series gracefully (some models may fail, others succeed)
        result = service.compare_all_baselines(short_series, forecast_horizon=3)
        assert "results" in result
        # At least some models should succeed
        valid_results = {k: v for k, v in result["results"].items() if "rmse" in v}
        assert len(valid_results) > 0


# ------------------------------------------------------------------ #
# Clustering service tests
# ------------------------------------------------------------------ #


class TestClusteringService:
    """Tests for market regime clustering"""

    def test_extract_features(self, sample_time_series):
        """Test feature extraction from price windows"""
        service = ClusteringService()
        features, indices = service.extract_features(sample_time_series, window_size=30)

        assert len(features) > 0
        assert len(indices) > 0
        assert "mean" in features.columns
        assert "std" in features.columns
        assert "autocorr_1" in features.columns
        assert "slope" in features.columns
        assert len(indices) == len(features)

    def test_extract_features_insufficient_data(self, sample_time_series):
        """Test feature extraction with insufficient data"""
        service = ClusteringService()
        short_series = sample_time_series.iloc[:20]

        with pytest.raises(ValueError):
            service.extract_features(short_series, window_size=30)

    def test_find_optimal_k(self, sample_time_series):
        """Test optimal k selection"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)

        result = service.find_optimal_k(features, k_range=range(2, 6))

        assert "optimal_k" in result
        assert "silhouette_scores" in result
        assert "optimal_score" in result
        assert result["optimal_k"] in range(2, 6)

    def test_cluster_data(self, sample_time_series):
        """Test clustering with specified k"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)

        result = service.cluster_data(features, k=3)

        assert "labels" in result
        assert "features" in result
        assert "cluster_stats" in result
        assert "n_clusters" in result
        assert result["n_clusters"] == 3
        assert len(result["labels"]) == len(features)

    def test_cluster_data_with_model(self, sample_time_series):
        """Test clustering with pre-fitted model"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)

        from sklearn.cluster import KMeans

        kmeans = KMeans(n_clusters=3, random_state=42)
        kmeans.fit(features.values)  # Fit first
        result = service.cluster_data(features, kmeans_model=kmeans)

        assert result["n_clusters"] == 3

    def test_cluster_data_no_params(self):
        """Test clustering without k or model"""
        service = ClusteringService()
        features, _ = service.extract_features(
            pd.Series(range(100), name="Close"), window_size=20
        )

        with pytest.raises(ValueError):
            service.cluster_data(features)

    def test_reduce_dimensions_pca(self, sample_time_series):
        """Test PCA dimensionality reduction"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)
        features["cluster"] = 0  # Add dummy column

        result = service.reduce_dimensions(features, method="pca")

        assert "pca" in result
        assert "data" in result["pca"]
        assert "explained_variance_ratio" in result["pca"]

    def test_reduce_dimensions_tsne(self, sample_time_series):
        """Test t-SNE dimensionality reduction"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)

        result = service.reduce_dimensions(features, method="tsne")

        assert "tsne" in result
        assert "data" in result["tsne"]

    def test_reduce_dimensions_both(self, sample_time_series):
        """Test both PCA and t-SNE"""
        service = ClusteringService()
        features, _ = service.extract_features(sample_time_series, window_size=30)

        result = service.reduce_dimensions(features, method="both")

        assert "pca" in result
        assert "tsne" in result

    def test_get_market_regimes(self, sample_time_series):
        """Test complete market regime analysis pipeline"""
        service = ClusteringService()
        result = service.get_market_regimes(
            sample_time_series,
            window_size=30,
            k_range=range(2, 5),
        )

        assert "window_size" in result
        assert "n_windows" in result
        assert "optimal_k" in result
        assert "silhouette_score" in result
        assert "silhouette_scores" in result
        assert "cluster_stats" in result
        assert "n_clusters" in result
        assert "dimensions" in result
        assert "timestamp" in result


# ------------------------------------------------------------------ #
# Integration tests
# ------------------------------------------------------------------ #


class TestIntegration:
    """Integration tests combining multiple services"""

    def test_full_forecasting_pipeline(self, sample_time_series):
        """Test complete forecasting pipeline"""
        service = ForecastingService()

        # Step 1: Check stationarity
        stationarity = service.check_stationarity(sample_time_series)
        assert "is_stationary" in stationarity

        # Step 2: Grid search
        grid_result = service.grid_search_arima(
            sample_time_series,
            p_range=range(0, 2),
            d_range=range(0, 2),
            q_range=range(0, 2),
        )
        assert "best_order" in grid_result

        # Step 3: Compare baselines
        baseline_result = service.compare_all_baselines(sample_time_series, 10)
        assert "best_model" in baseline_result

        # Step 4: Cross-validate
        cv_result = service.timeseries_cross_validate(
            sample_time_series, n_splits=2, model_type="naive"
        )
        assert "mean_rmse" in cv_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
