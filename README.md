# 📊 FastAPI Finance Monitor

Real-time financial dashboard for monitoring stocks, cryptocurrencies, commodities, and other assets.

## ✨ Features

- 📈 **Real-time charts** - Updates every 30 seconds via WebSocket
- 💹 **Multiple asset types** - Stocks (Apple, Google, Microsoft, Tesla), cryptocurrencies (Bitcoin, Ethereum, Solana), commodities (Gold)
- 📊 **Interactive charts** - Candlestick charts for stocks, line charts for cryptocurrencies (Plotly.js)
- 🎨 **Modern UI** - Dark theme, responsive design with smooth animations
- ⚡ **Asynchronous architecture** - FastAPI + async/await for high performance
- 🔌 **WebSocket** - Instant updates without page refresh
- 🌟 **Watchlists** - Personalized asset tracking
- 📈 **Technical indicators** - RSI, MACD, Bollinger Bands, and more
- 🔍 **Asset search** - Find and add new assets to track

## 🏗️ Architecture

```bash
fastapi-finance-monitor/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── api/
│   │   ├── routes.py        # REST endpoints
│   │   └── websocket.py     # WebSocket for real-time data
│   ├── services/
│   │   ├── data_fetcher.py  # Data fetching from exchanges
│   │   ├── indicators.py    # Technical indicators
│   │   └── watchlist.py     # User watchlist management
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fastapi-finance-monitor.git
cd fastapi-finance-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Run the server
python app/main.py

# Or with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser to: **http://localhost:8000**

## 📦 Project Structure

```
fastapi-finance-monitor/
├── app/
│   ├── main.py              # Main FastAPI application
│   ├── models.py            # Data models
│   ├── api/                 # API endpoints
│   │   ├── routes.py        # REST API routes
│   │   └── websocket.py     # WebSocket endpoints
│   ├── services/            # Business logic
│   │   ├── data_fetcher.py  # Data fetching services
│   │   ├── indicators.py    # Technical indicators
│   │   └── watchlist.py     # Watchlist management
├── requirements.txt         # Python dependencies
└── README.md               # Documentation
```

## 🔧 Technologies Used

### Backend
- **FastAPI** - Modern asynchronous web framework
- **WebSocket** - Real-time communication
- **yfinance** - Yahoo Finance data (stocks, commodities)
- **CoinGecko API** - Cryptocurrency data
- **Pandas** - Data processing
- **NumPy** - Numerical computing

### Frontend
- **Plotly.js** - Interactive charts
- **Vanilla JavaScript** - WebSocket client
- **CSS3** - Modern responsive design
- **Font Awesome** - Icons

## 📊 Tracked Assets

By default, the following assets are monitored:

| Asset | Type | Source |
|-------|------|--------|
| Apple (AAPL) | Stock | Yahoo Finance |
| Google (GOOGL) | Stock | Yahoo Finance |
| Microsoft (MSFT) | Stock | Yahoo Finance |
| Tesla (TSLA) | Stock | Yahoo Finance |
| Gold (GC=F) | Commodity | Yahoo Finance |
| Bitcoin | Cryptocurrency | CoinGecko |
| Ethereum | Cryptocurrency | CoinGecko |
| Solana | Cryptocurrency | CoinGecko |

## 🎯 API Endpoints

### REST API

- `GET /` - Main dashboard page
- `GET /api/assets` - Get data for all assets in watchlist
- `GET /api/asset/{symbol}` - Get data for specific asset
- `GET /api/asset/{symbol}/indicators` - Get technical indicators for asset
- `GET /api/search` - Search for assets
- `POST /api/watchlist/add` - Add asset to watchlist
- `POST /api/watchlist/remove` - Remove asset from watchlist
- `GET /api/watchlist` - Get user's watchlist
- `GET /api/health` - Health check endpoint

### WebSocket

- `WS /ws` - Real-time data updates

Example connection:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## 🔨 Customization

### Add New Assets

Add new assets to the default watchlist in [watchlist.py](app/services/watchlist.py):

```python
default_assets = [
    "AAPL", "GOOGL", "MSFT", "TSLA", "GC=F",
    "bitcoin", "ethereum", "solana"
]
```

### Change Update Interval

Modify the update interval in [websocket.py](app/api/websocket.py):
```python
await asyncio.sleep(30)  # 30 seconds -> any value
```

### Add Technical Indicators

The [indicators.py](app/services/indicators.py) service includes RSI, MACD, Bollinger Bands, and more. You can add additional indicators as needed.

## 📈 Usage Examples

### Get Data via API

```bash
curl http://localhost:8000/api/assets
```

### Connect to WebSocket (Python)

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(data)

asyncio.run(listen())
```

## ⚠️ Important Notes

1. **Rate Limits** - Yahoo Finance and CoinGecko have request limits. Don't reduce update interval below 10 seconds
2. **API Keys** - Current version uses free APIs without keys. For production, use paid APIs with keys
3. **Real-time Data** - Yahoo Finance provides data with ~15 minute delay for some exchanges

## 🚀 Future Enhancements

- [x] Modular project structure
- [x] Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- [x] User watchlists and favorites
- [x] Enhanced UI with dark theme and animations
- [ ] Redis caching for improved performance
- [ ] Email/Telegram price alerts
- [ ] Historical data (1 month, 1 year views)
- [ ] Multi-asset comparison charts
- [ ] Data export (CSV, Excel)
- [ ] User authentication
- [ ] Personalized watchlists
- [ ] Mobile application

## 📝 License

MIT License - free to use and modify

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

## 📧 Contact

For questions and suggestions: [create an issue](https://github.com/yourusername/fastapi-finance-monitor/issues)

---

**Made with ❤️ using FastAPI**