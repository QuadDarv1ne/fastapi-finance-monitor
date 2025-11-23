# 📊 FastAPI Finance Monitor

![img_1](img/img_1.png)

![img_2](img/img_2.png)

![alt text](img/img_3.png)

![alt text](img/img_4.png)

Информационная панель для мониторинга финансовых активов в реальном времени

## ✨ Возможности

- 📈 **Графики в реальном времени** - обновление каждые 30 секунд через WebSocket
- 💹 **Множество типов активов** - акции (Apple, Google, Microsoft, Tesla, Disney, Visa и др.), криптовалюты (Bitcoin, Ethereum, Solana, Cardano и др.), товары (Золото, Нефть, Серебро и др.), валютные пары (EUR/USD, GBP/USD и др.)
- 📊 **Интерактивные графики** - свечные графики для акций, линейные графики для криптовалют (Plotly.js)
- 🎨 **Современный интерфейс** - темная тема, адаптивный дизайн с плавной анимацией
- ⚡ **Асинхронная архитектура** - FastAPI + async/await для высокой производительности
- 🔌 **WebSocket** - мгновенные обновления без перезагрузки страницы
- 🌟 **Списки наблюдения** - персонализированный трекинг активов
- 📈 **Технические индикаторы** - RSI, MACD, Bollinger Bands и другие
- 🔍 **Поиск активов** - поиск и добавление новых активов для отслеживания
- ⏱️ **Множественные интервалы времени** - 1m, 5m, 10m, 30m, 1h, 3h, 6h, 12h, 1d
- 📉 **Управление обновлениями** - автоматическое и ручное обновление данных
- 📁 **Категории активов** - отдельные вкладки для акций, криптовалют, товаров, форекс
- 🌐 **Множественные источники данных** - 12+ провайдеров с автоматическим переключением
- 🔄 **Интеллектуальный fallback** - автоматическая смена источника при сбое
- 🏥 **Мониторинг здоровья** - отслеживание надежности каждого источника данных
- 🎯 **Автоматическая классификация** - определение типа актива (акции, крипта, форекс и т.д.)
- 💾 **Redis кэширование** - улучшенная производительность с интеллектуальным кешем
- 🔐 **Безопасность** - JWT аутентификация, bcrypt хеширование, rate limiting

## 🏗️ Архитектура

```text
fastapi-finance-monitor/
├── app/
│   ├── main.py              # Основное приложение FastAPI (lifespan управление)
│   ├── models.py            # Модели данных Pydantic
│   ├── config.py            # Конфигурационные настройки (SecurityConfig, CacheConfig)
│   ├── database.py          # Подключение к базе данных
│   ├── api/
│   │   ├── routes.py        # REST API эндпоинты (v1)
│   │   ├── enhanced_routes.py # REST API эндпоинты (v2 - multi-source)
│   │   └── websocket.py     # WebSocket для данных в реальном времени
│   ├── services/
│   │   ├── data_fetcher.py  # Получение данных с бирж (Yahoo Finance)
│   │   ├── data_sources_registry.py # Реестр источников данных (12+ провайдеров)
│   │   ├── enhanced_data_fetcher.py # Умный фетчер с fallback и классификацией
│   │   ├── indicators.py    # Технические индикаторы
│   │   ├── watchlist.py     # Управление списками наблюдения
│   │   ├── portfolio_service.py # Управление портфелем
│   │   ├── alert_service.py # Система уведомлений
│   │   ├── auth_service.py  # Аутентификация пользователей
│   │   ├── cache_service.py # LRU кэш (in-memory)
│   │   └── redis_cache_service.py # Redis кэш (distributed)
│   ├── managers/
│   │   ├── connection_manager.py # Управление WebSocket соединениями
│   │   ├── data_manager.py  # Управление потоками данных
│   │   └── subscription_manager.py # Управление подписками
│   ├── middleware/
│   │   ├── exception_handler_middleware.py # Глобальная обработка ошибок
│   │   └── monitoring_middleware.py # Мониторинг производительности
│   ├── tests/
│   │   └── test_*.py        # Модульные и интеграционные тесты (31 файл)
├── requirements.txt         # Зависимости Python
├── Dockerfile               # Docker конфигурация
├── docker-compose.yml       # Docker Compose конфигурация
├── redis.conf               # Конфигурация Redis
├── ENHANCED_DATA_SOURCES.md # Документация по источникам данных
├── HOW_TO_ADD_DATA_SOURCE.md # Руководство по добавлению источников
└── README.md               # Документация
```

## 🚀 Быстрый старт

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/fastapi-finance-monitor.git
cd fastapi-finance-monitor

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### Настройка переменных окружения (опционально)

Создайте файл `.env` для конфигурации API ключей премиум источников:

```bash
# Обязательные настройки
DATABASE_URL=postgresql://user:password@localhost/finance_monitor
SECRET_KEY=your-secret-key-here
REDIS_HOST=localhost
REDIS_PORT=6379

# Опциональные API ключи для премиум источников данных
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
POLYGON_API_KEY=your_polygon_key
FINNHUB_API_KEY=your_finnhub_key
TWELVE_DATA_API_KEY=your_twelve_data_key
IEX_CLOUD_API_KEY=your_iex_cloud_key
COINMARKETCAP_API_KEY=your_coinmarketcap_key
CRYPTOCOMPARE_API_KEY=your_cryptocompare_key

# Без этих ключей приложение использует бесплатные источники:
# - Yahoo Finance (акции, форекс, товары)
# - CoinGecko (криптовалюты)
# - Binance (криптовалюты)
# - Coinbase (криптовалюты)
# - ExchangeRate API (форекс)
```

### Запуск приложения

```bash
# Прямой запуск:
python app/main.py

# Или с помощью uvicorn:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или с помощью Docker:
docker-compose up -d
```

Откройте браузер: <http://localhost:8000>

## 🔧 Используемые технологии

### Бэкенд

- **FastAPI** - Современный асинхронный веб-фреймворк
- **WebSocket** - Коммуникация в реальном времени
- **yfinance** - Данные Yahoo Finance (акции, товары)
- **CoinGecko API** - Данные криптовалют
- **Pandas** - Обработка данных
- **NumPy** - Числовые вычисления
- **SQLAlchemy** - ORM для работы с базой данных
- **PostgreSQL** - Реляционная база данных
- **JWT** - Токен аутентификация
- **Bcrypt** - Хеширование паролей

### Фронтенд

- **Plotly.js** - Интерактивные графики
- **Vanilla JavaScript** - Клиент WebSocket
- **CSS3** - Современный адаптивный дизайн
- **Font Awesome** - Иконки

## 📊 Поддерживаемые активы

### Акции

- **Американские компании**: Apple, Google, Microsoft, Tesla, Amazon, Meta, NVIDIA, Netflix, Disney, Visa, JPMorgan Chase, Walmart, Procter & Gamble, Coca-Cola, Exxon Mobil, Boeing, IBM, Goldman Sachs, Home Depot, Mastercard и другие
- **Европейские компании**: Nestle, Roche, Novartis, SAP, Siemens, BMW, Daimler, Airbus, Sanofi, BNP Paribas, Enel, Eni, UniCredit, ING, ASML, Unilever, Royal Dutch Shell, BP, HSBC, Barclays, Vodafone, AstraZeneca, GlaxoSmithKline и другие
- **Российские компании**: Gazprom, Lukoil, Sberbank, Rosneft, Norilsk Nickel, Novatek, Alrosa, Tatneft, Surgutneftegas, Severstal, NLMK, Magnit, MTS, FEES, RusHydro и другие
- **Китайские компании**: Alibaba, Tencent, Baidu, JD.com, NetEase, China Mobile, China Unicom, PetroChina, Sinopec, Bank of China, Industrial and Commercial Bank of China, China Construction Bank, Ping An Insurance, Kweichow Moutai, BYD, Xiaomi, Meituan и другие

### Криптовалюты

Bitcoin, Ethereum, Solana, Cardano, Polkadot, Litecoin, Chainlink, Bitcoin Cash, Stellar, Uniswap, Dogecoin, Avalanche, Polygon, Cosmos, Monero, TRON, VeChain, Filecoin, Theta, EOS, Tezos, Elrond, Flow, Klaytn, NEAR, Hedera, Algorand, IOTA, Dash, Zcash и другие

### Товары

- **Драгоценные металлы**: Золото, Серебро, Платина, Палладий (фьючерсы и спот)
- **Энергетика**: Нефть, Природный газ
- **Сельхозпродукты**: Хлопок, Кофе, Сахар, Какао, Живой скот, Свинина, Пшеница, Кукуруза, Овес, Рис, Кормовой скот

### Валютные пары

EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY, GBP/NZD, EUR/AUD, EUR/CHF, CAD/JPY, CHF/JPY, USD/MXN, USD/ZAR, USD/RUB, EUR/RUB, GBP/RUB и другие

## 🎯 API Эндпоинты

### REST API v1 (Основные)

- `GET /` - Главная страница информационной панели
- `GET /api/assets` - Получить данные для всех активов в списке наблюдения
- `GET /api/asset/{symbol}` - Получить данные для конкретного актива
- `GET /api/asset/{symbol}/indicators` - Получить технические индикаторы для актива
- `GET /api/search` - Поиск активов
- `POST /api/watchlist/add` - Добавить актив в список наблюдения
- `POST /api/watchlist/remove` - Удалить актив из списка наблюдения
- `GET /api/watchlist` - Получить список наблюдения пользователя
- `GET /api/health` - Проверка состояния

### REST API v2 (Расширенные - Multi-Source)

- `GET /api/v2/asset/{symbol}` - Получить данные с автоматическим выбором источника и fallback
- `GET /api/v2/sources/health` - Статус здоровья всех источников данных
- `GET /api/v2/sources/list` - Список всех доступных источников с приоритетами
- `POST /api/v2/classify` - Классификация актива по символу
- `GET /api/v2/sources/{name}/status` - Детальный статус конкретного источника

### Аутентификация

- `POST /api/users/register` - Регистрация пользователя
- `POST /api/users/login` - Вход пользователя
- `POST /api/users/verify-email` - Подтверждение email пользователя
- `POST /api/users/resend-verification` - Повторная отправка подтверждения email
- `GET /api/users/me` - Получить профиль текущего пользователя
- `PUT /api/users/me` - Обновить профиль текущего пользователя
- `PUT /api/users/me/password` - Изменить пароль текущего пользователя

### Портфель

- `GET /api/portfolio` - Получить все портфели пользователя
- `POST /api/portfolio/create` - Создать новый портфель
- `GET /api/portfolio/{id}` - Получить конкретный портфель
- `POST /api/portfolio/add_item` - Добавить актив в портфель
- `POST /api/portfolio/remove_item` - Удалить актив из портфеля
- `GET /api/portfolio/{id}/performance` - Получить метрики производительности портфеля
- `GET /api/portfolio/{id}/holdings` - Получить детальную информацию о позициях в портфеле

### Уведомления

- `GET /api/alerts` - Получить уведомления пользователя
- `POST /api/alerts/create` - Создать новое уведомление

### WebSocket

- `WS /ws` - Обновления данных в реальном времени

**Пример подключения:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

### Примеры использования API v2

**Получить данные актива с автоматическим fallback:**

```bash
curl http://localhost:8000/api/v2/asset/AAPL
```

**Проверить здоровье источников данных:**

```bash
curl http://localhost:8000/api/v2/sources/health
```

**Классифицировать актив:**

```bash
curl -X POST http://localhost:8000/api/v2/classify \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC-USD"}'
```

## 🌐 Источники данных

### Бесплатные (активны по умолчанию)

1. **Yahoo Finance** - Акции, форекс, товары, индексы
2. **CoinGecko** - Криптовалюты (без ключа)
3. **Binance** - Криптовалюты (публичный API)
4. **Coinbase** - Криптовалюты (публичный API)
5. **ExchangeRate API** - Валютные пары

### Премиум (требуют API ключ)

6. **Alpha Vantage** - Акции, форекс, криптовалюты
7. **Polygon.io** - Акции в реальном времени
8. **Finnhub** - Акции, форекс, криптовалюты
9. **Twelve Data** - Акции, форекс, криптовалюты
10. **IEX Cloud** - Рыночные данные США
11. **CoinMarketCap** - Криптовалюты (детальные данные)
12. **CryptoCompare** - Криптовалюты (агрегированные данные)

**Система автоматически:**

- Выбирает лучший источник для каждого типа актива
- Переключается на резервный источник при сбое
- Отслеживает надежность каждого источника
- Классифицирует активы по типу (EQUITY, CRYPTOCURRENCY, FOREX и т.д.)

Подробнее: [ENHANCED_DATA_SOURCES.md](ENHANCED_DATA_SOURCES.md)

## 🔨 Кастомизация

### Добавление новых активов

Добавьте новые активы в список в [websocket.py](app/api/websocket.py):

```bash
FINANCIAL_INSTRUMENTS = {
    # Существующие активы...
    'NEW_SYMBOL': {'name': 'New Asset Name', 'type': 'stock/crypto/commodity/forex'},
}
```

### Изменение интервала обновления

Измените интервал обновления в [websocket.py](app/api/websocket.py):

```bash
await asyncio.sleep(30)  # 30 секунд -> любое значение
```

### Добавление технических индикаторов

Сервис [indicators.py](app/services/indicators.py) включает RSI, MACD, Bollinger Bands и другие. Вы можете добавить дополнительные индикаторы при необходимости.

## 📈 Примеры использования

### Получение данных через API v1

```bash
curl http://localhost:8000/api/assets
```

### Получение данных через API v2 с fallback

```bash
# Получить данные Apple с автоматическим выбором источника
curl http://localhost:8000/api/v2/asset/AAPL

# Получить данные Bitcoin с fallback на резервные источники
curl http://localhost:8000/api/v2/asset/BTC-USD
```

### Подключение к WebSocket (Python)

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

### Проверка здоровья источников данных

```bash
# Получить статус всех источников
curl http://localhost:8000/api/v2/sources/health

# Получить детальную информацию о конкретном источнике
curl http://localhost:8000/api/v2/sources/yahoo_finance/status
```

## ⚠️ Важные замечания

1. **Ограничения по запросам** - У каждого источника данных есть rate limits:
   - Yahoo Finance: ~2000 запросов/час (бесплатно)
   - CoinGecko: 10-50 запросов/минуту (бесплатно)
   - Alpha Vantage: 5 запросов/минуту, 500/день (бесплатный план)
   - Polygon: 5 запросов/минуту (бесплатный план)
2. **API ключи** - Премиум источники требуют регистрации и API ключей. Приложение работает без них, используя бесплатные источники
3. **Данные в реальном времени** - Бесплатные источники предоставляют данные с задержкой ~15 минут. Для real-time используйте премиум API
4. **Fallback механизм** - При сбое основного источника система автоматически переключается на резервный (до 3 попыток)
5. **Производительность** - Redis кэширование значительно снижает нагрузку на API. Рекомендуется для production
6. **Мониторинг** - Используйте `/api/v2/sources/health` для отслеживания надежности источников данных

## 🚀 Планы развития

- [x] Модульная архитектура проекта
- [x] Технические индикаторы (RSI, MACD, Bollinger Bands, и др.)
- [x] Списки наблюдения и избранное
- [x] Улучшенный интерфейс с темной темой и анимациями
- [x] Множественные интервалы времени
- [x] Расширенный список финансовых инструментов
- [x] Система портфолио и уведомлений
- [x] Аутентификация пользователей (JWT + bcrypt)
- [x] Полная реализация системы портфолио с API эндпоинтами
- [x] Redis кэширование для улучшения производительности
- [x] Множественные источники данных (12+ провайдеров)
- [x] Интеллектуальный fallback при сбое источников
- [x] Автоматическая классификация активов
- [x] Мониторинг здоровья источников данных
- [x] Middleware для обработки ошибок и мониторинга
- [x] Современная архитектура FastAPI (lifespan context manager)
- [ ] Уведомления по электронной почте/Telegram о ценах
- [ ] Исторические данные (просмотр за 1 месяц, 1 год)
- [ ] Сравнение нескольких активов на одном графике
- [ ] Экспорт данных (CSV, Excel)
- [ ] Мобильное приложение
- [ ] Machine Learning для прогнозирования цен
- [ ] Backtesting для торговых стратегий

## 📝 Лицензия

[Этот проект лицензирован под лицензией MIT](LICENCE)

Для получения дополнительной информации ознакомьтесь с файлом `LICENSE`

## 🤝 Участие в разработке

Pull requests приветствуются! Для крупных изменений сначала создайте issue.

## 📧 Контакты

Вопросы и предложения: [создайте issue](https://github.com/yourusername/fastapi-finance-monitor/issues)

---

### Сделано с ❤️ используя FastAPI

---

💼 **Автор:** Дуплей Максим Игоревич

📲 **Telegram №1:** [@quadd4rv1n7](https://t.me/quadd4rv1n7)

📲 **Telegram №2:** [@dupley_maxim_1999](https://t.me/dupley_maxim_1999)

📅 **Дата:** 29.10.2025

▶️ **Версия 1.0**

```textline
※ Предложения по сотрудничеству можете присылать на почту ※
📧 maksimqwe42@mail.ru
```
