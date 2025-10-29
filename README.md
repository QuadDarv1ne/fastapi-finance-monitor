# 📊 FastAPI Finance Monitor

Real-time financial dashboard для мониторинга акций, криптовалют, золота и других активов.

## ✨ Возможности

- 📈 **Real-time графики** - обновление каждые 30 секунд через WebSocket
- 💹 **Множественные активы** - акции (Apple, Google), криптовалюты (Bitcoin, Ethereum), драгоценные металлы (Gold)
- 📊 **Интерактивные графики** - свечные графики для акций, линейные для криптовалют (Plotly.js)
- 🎨 **Современный UI** - темная тема, адаптивный дизайн
- ⚡ **Асинхронность** - FastAPI + async/await для высокой производительности
- 🔌 **WebSocket** - мгновенные обновления без перезагрузки страницы

## Архитектура приложения

```bash
fastapi-finance-monitor/
├── app/
│   ├── main.py              # FastAPI приложение
│   ├── api/
│   │   ├── routes.py        # REST endpoints
│   │   └── websocket.py     # WebSocket для real-time
│   ├── services/
│   │   ├── data_fetcher.py  # Получение данных с бирж
│   │   └── indicators.py    # Технические индикаторы
│   └── models.py            # Pydantic модели
├── frontend/
│   └── dashboard.html       # Графики + UI
├── requirements.txt
└── README.md
```

## 🚀 Быстрый старт

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/fastapi-finance-monitor.git
cd fastapi-finance-monitor

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### Запуск

```bash
# Запустить сервер
python main.py

# Или через uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Откройте браузер: **http://localhost:8000**

## 📦 Структура проекта

```
fastapi-finance-monitor/
├── main.py              # Основное приложение FastAPI
├── requirements.txt     # Зависимости Python
└── README.md           # Документация
```

## 🔧 Используемые технологии

### Backend
- **FastAPI** - современный асинхронный веб-фреймворк
- **WebSocket** - real-time коммуникация
- **yfinance** - данные с Yahoo Finance (акции, золото)
- **CoinGecko API** - данные криптовалют
- **Pandas** - обработка данных

### Frontend
- **Plotly.js** - интерактивные графики
- **Vanilla JavaScript** - WebSocket клиент
- **CSS3** - современный дизайн

## 📊 Отслеживаемые активы

По умолчанию мониторятся:

| Актив | Тип | Источник |
|-------|-----|----------|
| Apple (AAPL) | Акция | Yahoo Finance |
| Google (GOOGL) | Акция | Yahoo Finance |
| Gold (GC=F) | Фьючерс | Yahoo Finance |
| Bitcoin | Криптовалюта | CoinGecko |
| Ethereum | Криптовалюта | CoinGecko |

## 🎯 API Endpoints

### REST API

- `GET /` - Главная страница дашборда
- `GET /api/assets` - Получить данные по всем активам (JSON)

### WebSocket

- `WS /ws` - Real-time обновления данных

Пример подключения:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## 🔨 Кастомизация

### Добавить новые активы

Отредактируйте список `assets` в функции `data_stream_worker()`:

```python
assets = [
    {"type": "stock", "symbol": "TSLA", "name": "Tesla"},  # Добавить Tesla
    {"type": "crypto", "symbol": "solana", "name": "Solana"},  # Добавить Solana
    # ...
]
```

### Изменить интервал обновления

В функции `data_stream_worker()` измените:
```python
await asyncio.sleep(30)  # 30 секунд -> любое значение
```

### Добавить технические индикаторы

Класс `TechnicalIndicators` содержит RSI и MA. Можно добавить MACD, Bollinger Bands и др.

## 📈 Примеры использования

### Получить данные через API

```bash
curl http://localhost:8000/api/assets
```

### Подключиться к WebSocket (Python)

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

## ⚠️ Важные замечания

1. **Rate Limits** - Yahoo Finance и CoinGecko имеют лимиты запросов. Не уменьшайте интервал обновления ниже 10 секунд
2. **API Keys** - Текущая версия использует бесплатные API без ключей. Для production рекомендуется использовать платные API с ключами
3. **Данные в реальном времени** - Yahoo Finance предоставляет данные с задержкой ~15 минут для некоторых бирж

## 🚀 Расширения

### Планы развития:
- [ ] Добавить Redis для кэширования
- [ ] Технические индикаторы (MACD, Bollinger Bands, Stochastic)
- [ ] Алерты по ценам (email/Telegram)
- [ ] Исторические данные (1 месяц, 1 год)
- [ ] Сравнение нескольких активов на одном графике
- [ ] Экспорт данных (CSV, Excel)
- [ ] Авторизация пользователей
- [ ] Персональные watchlist'ы
- [ ] Мобильное приложение

## 📝 Лицензия

MIT License - свободное использование

## 🤝 Контрибьюция

Pull requests приветствуются! Для крупных изменений сначала откройте issue.

## 📧 Контакты

Вопросы и предложения: [создайте issue](https://github.com/yourusername/fastapi-finance-monitor/issues)

---

**Сделано с ❤️ используя FastAPI**