# 📈 Forecasting API Documentation

## Overview

The Forecasting API provides ML-based price predictions for financial assets using time series analysis.

## Supported Models

- **ARIMA** - AutoRegressive Integrated Moving Average
- **Exponential Smoothing** - Holt-Winters method with trend and seasonality
- **Linear Regression** - ML model with lag features
- **Naive** - Simple baseline (tomorrow = yesterday)
- **Weighted MA** - Weighted moving average
- **Holt-Winters** - Triple exponential smoothing

## API Endpoints

### 1. Get Price Forecast

```http
POST /api/forecast
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "days_ahead": 30,
  "model_type": "arima",
  "order": [1, 1, 1]
}
```

**Parameters:**
- `symbol` (string, required): Asset symbol (e.g., "AAPL", "BTC-USD")
- `days_ahead` (integer, default: 30): Number of days to forecast
- `model_type` (string, default: "arima"): Model type - "arima", "exponential", or "linear"
- `order` (array, default: [1,1,1]): ARIMA order (p,d,q) - only for ARIMA model

**Response:**
```json
{
  "symbol": "AAPL",
  "model_type": "arima",
  "forecast_dates": ["2024-01-15", "2024-01-16", ...],
  "forecast_values": [150.25, 151.30, ...],
  "current_price": 148.50,
  "confidence_intervals": [[148.00, 152.50], ...],
  "timestamp": "2024-01-14T10:30:00"
}
```

### 2. Retrain Forecast Model

```http
POST /api/forecast/retrain
```

**Request Body:**
```json
{
  "symbol": "AAPL"
}
```

**Response:**
```json
{
  "message": "Model retrained successfully for AAPL",
  "symbol": "AAPL"
}
```

### 3. Get Model Accuracy

```http
GET /api/forecast/accuracy/{symbol}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "trained_at": "2024-01-14T10:30:00",
  "accuracy": 0.85,
  "message": "Model trained successfully"
}
```

### 4. Grid Search for ARIMA Parameters

```http
POST /api/forecast/grid-search
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "p_max": 5,
  "d_max": 3,
  "q_max": 5
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "best_order": [2, 1, 1],
  "best_rmse": 3.45,
  "total_tried": 75,
  "total_successful": 73,
  "top_5": [
    {"order": [2, 1, 1], "rmse": 3.45},
    {"order": [1, 1, 2], "rmse": 3.52},
    ...
  ]
}
```

### 5. Time Series Cross-Validation

```http
POST /api/forecast/cross-validate
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "n_splits": 4,
  "model_type": "exponential"
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "model_type": "exponential",
  "n_splits": 4,
  "folds_completed": 4,
  "rmse_per_fold": [3.2, 3.5, 3.1, 3.4],
  "mean_rmse": 3.3,
  "std_rmse": 0.15
}
```

### 6. Compare All Baselines

```http
POST /api/forecast/compare-baselines
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "forecast_horizon": 30
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "forecast_horizon": 30,
  "train_size": 1460,
  "test_size": 365,
  "results": {
    "naive": {"rmse": 5.2, "mape": 2.1},
    "rolling_mean_5": {"rmse": 4.8, "mape": 1.9},
    "rolling_mean_10": {"rmse": 4.5, "mape": 1.8},
    "weighted_ma": {"rmse": 4.3, "mape": 1.7},
    "holt_winters": {"rmse": 3.8, "mape": 1.5},
    "arima_1_1_1": {"rmse": 3.6, "mape": 1.4}
  },
  "best_model": "arima_1_1_1"
}
```

### 7. Check Stationarity

```http
GET /api/forecast/stationarity/{symbol}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "stationarity": {
    "test_statistic": -2.34,
    "p_value": 0.15,
    "lags_used": 5,
    "observations": 1000,
    "critical_values": {
      "1%": -3.43,
      "5%": -2.86,
      "10%": -2.57
    },
    "is_stationary": false
  },
  "recommendation": "Series is non-stationary. Consider differencing (d>=1) or log transform."
}
```

### 8. Market Regime Clustering

```http
POST /api/forecast/clusters
```

**Request Body:**
```json
{
  "symbol": "AAPL",
  "window_size": 30,
  "k_min": 2,
  "k_max": 10
}
```

**Response:**
```json
{
  "symbol": "AAPL",
  "window_size": 30,
  "n_windows": 48,
  "optimal_k": 4,
  "silhouette_score": 0.45,
  "silhouette_scores": {2: 0.42, 3: 0.48, 4: 0.45, ...},
  "cluster_stats": {
    "0": {
      "size": 12,
      "mean_features": {
        "mean": 150.2,
        "std": 2.5,
        "min": 145.0,
        "max": 155.0,
        "range": 10.0,
        "autocorr_1": 0.85,
        "autocorr_5": 0.65,
        "slope": 0.12,
        "volatility": 1.8,
        "skewness": 0.1,
        "kurtosis": 2.9
      }
    },
    ...
  },
  "n_clusters": 4,
  "dimensions": {
    "pca": {
      "data": [[...], ...],
      "explained_variance_ratio": [0.65, 0.20]
    },
    "tsne": {
      "data": [[...], ...]
    }
  }
}
```

## Examples

### cURL Examples

**Get forecast for Apple stock:**
```bash
curl -X POST http://localhost:8000/api/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "days_ahead": 30,
    "model_type": "arima"
  }'
```

**Retrain model:**
```bash
curl -X POST http://localhost:8000/api/forecast/retrain \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

**Get accuracy:**
```bash
curl http://localhost:8000/api/forecast/accuracy/AAPL
```

**Grid search ARIMA:**
```bash
curl -X POST http://localhost:8000/api/forecast/grid-search \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "p_max": 5,
    "d_max": 3,
    "q_max": 5
  }'
```

**Cross-validation:**
```bash
curl -X POST http://localhost:8000/api/forecast/cross-validate \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "n_splits": 4,
    "model_type": "exponential"
  }'
```

**Compare baselines:**
```bash
curl -X POST http://localhost:8000/api/forecast/compare-baselines \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "forecast_horizon": 30
  }'
```

**Check stationarity:**
```bash
curl http://localhost:8000/api/forecast/stationarity/AAPL
```

**Market regime clustering:**
```bash
curl -X POST http://localhost:8000/api/forecast/clusters \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "window_size": 30,
    "k_min": 2,
    "k_max": 8
  }'
```

### Python Example

```python
import requests

# Get forecast
response = requests.post(
    'http://localhost:8000/api/forecast',
    json={
        'symbol': 'AAPL',
        'days_ahead': 30,
        'model_type': 'arima'
    }
)

forecast = response.json()
print(f"Current Price: ${forecast['current_price']}")
print(f"30-Day Forecast: ${forecast['forecast_values'][-1]:.2f}")
```

## Model Selection Guide

| Model | Best For | Speed | Accuracy |
|-------|----------|-------|----------|
| ARIMA | Trending data with seasonality | Medium | High |
| Exponential Smoothing | Data with clear seasonality | Fast | Medium |
| Linear Regression | Quick forecasts with features | Very Fast | Medium |

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid request parameters |
| 404 | No historical data available |
| 500 | Server error |

## Rate Limiting

- Default: 100 requests per minute per IP
- Premium API keys: 1000 requests per minute

## Notes

- Historical data must be at least 50 days old for accurate forecasting
- ARIMA models require more computation time but provide better accuracy
- Forecasts are most reliable for short-term predictions (7-30 days)
- Confidence intervals are provided only for ARIMA models
