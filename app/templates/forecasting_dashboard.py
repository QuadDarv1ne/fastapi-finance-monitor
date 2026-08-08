"""
Forecasting dashboard HTML template
"""

FORECASTING_HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ML Forecasting Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }
        .header h1 { color: white; font-size: 2em; margin-bottom: 10px; }
        .header p { color: rgba(255,255,255,0.8); }
        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            justify-content: center;
            align-items: flex-end;
        }
        .control-group { display: flex; flex-direction: column; gap: 5px; }
        .control-group label { color: #9ca3af; font-size: 0.9em; }
        .control-group input, .control-group select {
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid #2a2f4a;
            background: #1a1f3a;
            color: #e0e0e0;
            font-size: 16px;
            min-width: 200px;
        }
        .btn {
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover { background: #5a67d8; transform: translateY(-2px); }
        .btn:disabled { background: #4c5a8c; cursor: not-allowed; transform: none; }
        .btn-success { background: #10b981; }
        .btn-success:hover { background: #059669; }
        .btn-info { background: #3b82f6; }
        .btn-info:hover { background: #2563eb; }
        .btn-compare { background: #ec4899; }
        .btn-compare:hover { background: #db2777; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card {
            background: #1a1f3a;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border: 1px solid #2a2f4a;
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        .metric-item {
            background: rgba(42, 47, 74, 0.5);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .metric-label { font-size: 0.8em; color: #9ca3af; margin-bottom: 5px; }
        .metric-value { font-size: 1.4em; font-weight: bold; }
        .metric-good { color: #10b981; }
        .metric-bad { color: #ef4444; }
        .metric-neutral { color: #f59e0b; }
        .chart-container { height: 400px; margin-top: 15px; }
        .model-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .model-table th, .model-table td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #2a2f4a;
        }
        .model-table th { color: #667eea; }
        .model-table tr:hover { background: rgba(102, 126, 234, 0.1); }
        .best-model { background: rgba(16, 185, 129, 0.2) !important; }
        .loading-overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(10, 14, 39, 0.9);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .spinner {
            width: 50px; height: 50px;
            border: 4px solid #2a2f4a;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            background: #10b981;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transform: translateX(200%);
            transition: transform 0.3s ease;
            z-index: 1000;
        }
        .notification.show { transform: translateX(0); }
        .notification.error { background: #ef4444; }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .status-good { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .status-warning { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .status-bad { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .controls { flex-direction: column; }
            .control-group input, .control-group select { min-width: auto; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-brain"></i> ML Forecasting Dashboard</h1>
        <p>Predictive analytics for financial assets using ARIMA, Exponential Smoothing & Linear Regression</p>
    </div>

    <div class="controls">
        <div class="control-group">
            <label for="symbolInput">Asset Symbol</label>
            <input type="text" id="symbolInput" placeholder="e.g. AAPL, BTC-USD" value="AAPL">
        </div>
        <div class="control-group">
            <label for="modelSelect">Model Type</label>
            <select id="modelSelect">
                <option value="arima">ARIMA</option>
                <option value="exponential">Exponential Smoothing</option>
                <option value="linear">Linear Regression</option>
            </select>
        </div>
        <div class="control-group">
            <label for="horizonInput">Forecast Horizon (days)</label>
            <input type="number" id="horizonInput" value="30" min="7" max="90">
        </div>
        <button class="btn btn-success" id="forecastBtn" onclick="getForecast()">
            <i class="fas fa-chart-line"></i> Get Forecast
        </button>
        <button class="btn btn-info" onclick="runBacktest()">
            <i class="fas fa-history"></i> Run Backtest
        </button>
        <button class="btn btn-compare" onclick="compareModels()">
            <i class="fas fa-balance-scale"></i> Compare All Models
        </button>
    </div>

    <div id="loading" class="loading-overlay" style="display: none;">
        <div style="text-align: center;">
            <div class="spinner"></div>
            <p style="margin-top: 15px; color: #9ca3af;">Processing ML models...</p>
        </div>
    </div>

    <div id="notification" class="notification"></div>

    <!-- Forecast Results -->
    <div class="grid" id="forecastSection" style="display: none;">
        <div class="card">
            <h3><i class="fas fa-chart-area"></i> Price Forecast</h3>
            <div id="forecastChart" class="chart-container"></div>
        </div>
        <div class="card">
            <h3><i class="fas fa-tachometer-alt"></i> Forecast Metrics</h3>
            <div id="forecastMetrics" class="metrics-grid"></div>
            <div id="forecastStatus" style="margin-top: 15px;"></div>
        </div>
    </div>

    <!-- Backtest Results -->
    <div class="grid" id="backtestSection" style="display: none;">
        <div class="card">
            <h3><i class="fas fa-history"></i> Backtest Results</h3>
            <div id="backtestChart" class="chart-container"></div>
        </div>
        <div class="card">
            <h3><i class="fas fa-chart-bar"></i> Backtest Metrics</h3>
            <div id="backtestMetrics" class="metrics-grid"></div>
        </div>
    </div>

    <!-- Model Comparison -->
    <div class="card" id="comparisonSection" style="display: none;">
        <h3><i class="fas fa-balance-scale"></i> Model Comparison</h3>
        <table class="model-table" id="comparisonTable">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>RMSE</th>
                    <th>MAPE</th>
                    <th>SMAPE</th>
                    <th>R² Score</th>
                    <th>Direction Accuracy</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="comparisonBody"></tbody>
        </table>
    </div>

    <script>
        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = 'notification ' + type;
            notification.classList.add('show');
            setTimeout(() => notification.classList.remove('show'), 4000);
        }

        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'flex' : 'none';
            document.getElementById('forecastBtn').disabled = show;
        }

        function getForecast() {
            const symbol = document.getElementById('symbolInput').value.trim();
            if (!symbol) {
                showNotification('Please enter a symbol', 'error');
                return;
            }
            showLoading(true);
            fetch('/api/forecast', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({symbol: symbol})
            })
            .then(res => res.json())
            .then(data => {
                showLoading(false);
                if (data.error) {
                    showNotification(data.error, 'error');
                    return;
                }
                displayForecast(data);
            })
            .catch(err => {
                showLoading(false);
                showNotification('Error: ' + err.message, 'error');
            });
        }

        function displayForecast(data) {
            document.getElementById('forecastSection').style.display = 'grid';

            // Chart
            const trace1 = {
                x: data.recent_data.dates,
                y: data.recent_data.prices,
                name: 'Historical',
                type: 'scatter',
                line: {color: '#667eea'}
            };
            const trace2 = {
                x: data.forecast.dates,
                y: data.forecast.predicted,
                name: 'Predicted',
                type: 'scatter',
                line: {color: '#10b981', dash: 'dash'}
            };
            const trace3 = data.forecast.confidence_interval ? {
                x: [...data.forecast.dates, ...data.forecast.dates.reverse()],
                y: [...data.forecast.confidence_interval.upper, ...data.forecast.confidence_interval.lower.reverse()],
                fill: 'tonexty',
                fillcolor: 'rgba(102, 126, 234, 0.1)',
                line: {color: 'transparent'},
                name: '95% CI',
                type: 'scatter'
            } : null;

            Plotly.newPlot('forecastChart', [trace1, trace2, trace3].filter(Boolean), {
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a',
                font: {color: '#e0e0e0'},
                margin: {t: 20, r: 20, b: 40, l: 50}
            });

            // Metrics
            const metrics = data.metrics;
            document.getElementById('forecastMetrics').innerHTML = `
                <div class="metric-item">
                    <div class="metric-label">RMSE</div>
                    <div class="metric-value ${metrics.rmse < 5 ? 'metric-good' : metrics.rmse < 10 ? 'metric-neutral' : 'metric-bad'}">${metrics.rmse}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">MAPE</div>
                    <div class="metric-value ${metrics.mape < 5 ? 'metric-good' : metrics.mape < 10 ? 'metric-neutral' : 'metric-bad'}">${metrics.mape}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">R² Score</div>
                    <div class="metric-value ${metrics.r2_score > 0.8 ? 'metric-good' : metrics.r2_score > 0.5 ? 'metric-neutral' : 'metric-bad'}">${metrics.r2_score}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Direction</div>
                    <div class="metric-value ${metrics.direction_accuracy > 0.7 ? 'metric-good' : metrics.direction_accuracy > 0.5 ? 'metric-neutral' : 'metric-bad'}">${(metrics.direction_accuracy * 100).toFixed(1)}%</div>
                </div>
            `;

            const trend = data.trend_analysis;
            document.getElementById('forecastStatus').innerHTML = `
                <span class="status-badge ${trend.direction === 'up' ? 'status-good' : trend.direction === 'down' ? 'status-bad' : 'status-warning'}">
                    <i class="fas fa-arrow-${trend.direction === 'up' ? 'up' : trend.direction === 'down' ? 'down' : 'right'}"></i>
                    ${trend.direction.toUpperCase()} TREND
                </span>
                <p style="margin-top: 10px; color: #9ca3af; font-size: 0.9em;">
                    Stationarity: <strong>${trend.stationary ? '&#10004; Stationary' : '&#9888; Non-stationary'}</strong> |
                    Forecast horizon: <strong>${data.forecast_horizon} days</strong>
                </p>
            `;

            showNotification('Forecast generated successfully!');
        }

        function runBacktest() {
            const symbol = document.getElementById('symbolInput').value.trim();
            const model = document.getElementById('modelSelect').value;
            const horizon = parseInt(document.getElementById('horizonInput').value);

            showLoading(true);
            fetch('/api/forecast/backtest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({symbol, model_type: model, forecast_horizon: horizon})
            })
            .then(res => res.json())
            .then(data => {
                showLoading(false);
                if (data.error) {
                    showNotification(data.error, 'error');
                    return;
                }
                displayBacktest(data);
            })
            .catch(err => {
                showLoading(false);
                showNotification('Error: ' + err.message, 'error');
            });
        }

        function displayBacktest(data) {
            document.getElementById('backtestSection').style.display = 'grid';

            const trace1 = {
                x: data.predictions.dates,
                y: data.predictions.actual,
                name: 'Actual',
                type: 'scatter',
                line: {color: '#667eea'}
            };
            const trace2 = {
                x: data.predictions.dates,
                y: data.predictions.predicted,
                name: 'Predicted',
                type: 'scatter',
                line: {color: '#10b981', dash: 'dash'}
            };

            Plotly.newPlot('backtestChart', [trace1, trace2], {
                paper_bgcolor: '#1a1f3a',
                plot_bgcolor: '#1a1f3a',
                font: {color: '#e0e0e0'},
                margin: {t: 20, r: 20, b: 40, l: 50}
            });

            const metrics = data.metrics;
            document.getElementById('backtestMetrics').innerHTML = `
                <div class="metric-item">
                    <div class="metric-label">RMSE</div>
                    <div class="metric-value ${metrics.rmse < 5 ? 'metric-good' : 'metric-neutral'}">${metrics.rmse}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">MAE</div>
                    <div class="metric-value metric-neutral">${metrics.mae}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">MAPE</div>
                    <div class="metric-value ${metrics.mape < 5 ? 'metric-good' : 'metric-neutral'}">${metrics.mape}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">R² Score</div>
                    <div class="metric-value ${metrics.r2_score > 0.8 ? 'metric-good' : 'metric-neutral'}">${metrics.r2_score}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Direction Accuracy</div>
                    <div class="metric-value ${metrics.direction_accuracy > 0.7 ? 'metric-good' : 'metric-neutral'}">${(metrics.direction_accuracy * 100).toFixed(1)}%</div>
                </div>
            `;

            showNotification('Backtest completed for ' + data.model_type + ' model!');
        }

        function compareModels() {
            const symbol = document.getElementById('symbolInput').value.trim();
            const horizon = parseInt(document.getElementById('horizonInput').value);

            showLoading(true);
            fetch('/api/forecast/backtest/compare/' + symbol + '?forecast_horizon=' + horizon)
            .then(res => res.json())
            .then(data => {
                showLoading(false);
                if (data.error) {
                    showNotification(data.error, 'error');
                    return;
                }
                displayComparison(data);
            })
            .catch(err => {
                showLoading(false);
                showNotification('Error: ' + err.message, 'error');
            });
        }

        function displayComparison(data) {
            document.getElementById('comparisonSection').style.display = 'block';
            const tbody = document.getElementById('comparisonBody');
            tbody.innerHTML = '';

            for (const [model, metrics] of Object.entries(data.results)) {
                if (metrics.error) continue;
                const isBest = model === data.best_model;
                const row = document.createElement('tr');
                if (isBest) row.className = 'best-model';
                row.innerHTML = `
                    <td><strong>${model.toUpperCase()} ${isBest ? '&#127942;' : ''}</strong></td>
                    <td>${metrics.rmse}</td>
                    <td>${metrics.mape}%</td>
                    <td>${metrics.smape || '-'}</td>
                    <td>${metrics.r2_score}</td>
                    <td>${(metrics.direction_accuracy * 100).toFixed(1)}%</td>
                    <td><span class="status-badge ${isBest ? 'status-good' : 'status-warning'}">${isBest ? 'BEST' : 'OK'}</span></td>
                `;
                tbody.appendChild(row);
            }

            showNotification('Comparison complete! Best model: ' + data.best_model.toUpperCase());
        }

        // Auto-forecast on Enter key
        document.getElementById('symbolInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') getForecast();
        });
    </script>
</body>
</html>
"""
