# 📈 Forecasting API Documentation

## Overview

The Forecasting API provides ML-based price predictions for financial assets using time series analysis.

## Supported Models

- **ARIMA** - AutoRegressive Integrated Moving Average
- **Exponential Smoothing** - Holt-Winters method with trend and seasonality
- **Linear Regression** - ML model with lag features

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
