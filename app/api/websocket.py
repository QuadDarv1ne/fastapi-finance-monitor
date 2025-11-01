"""WebSocket handlers for real-time data streaming

This module implements the WebSocket infrastructure for real-time financial data
streaming. It manages client connections, handles subscriptions, and broadcasts
updates to connected clients.

The WebSocket system features:
- Client authentication and connection management
- Subscription-based data streaming
- Delta updates to minimize bandwidth usage
- Metrics collection for monitoring
- Rate limiting and resource management

Key Components:
    WebSocketManager: Main class for managing WebSocket connections
    data_stream_worker: Background task for fetching and broadcasting data
    TIMEFRAME_MAPPING: Mapping between UI timeframes and data intervals
    FINANCIAL_INSTRUMENTS: Registry of supported financial instruments

Functions:
    websocket_endpoint: Main WebSocket endpoint
    data_stream_worker: Background data streaming task
"""
import asyncio
import json
from datetime import datetime, timedelta
import random
import logging
from typing import Dict, List, Optional
import yfinance as yf
import uuid
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.services.auth_manager import AuthManager
from app.managers.data_manager import DataManager
from app.managers.subscription_manager import SubscriptionManager
from app.managers.connection_manager import ConnectionManager
from app.services.metrics_collector import MetricsCollector
from app.services.delta_manager import DeltaManager

logger = logging.getLogger(__name__)

# Global variables for WebSocket connections and data
connected_clients = set()
data_cache = {}
watchlists = {}
client_info = {}  # Store additional info about clients
client_subscriptions = {}  # Track client subscriptions

# Timeframe mapping for data intervals
TIMEFRAME_MAPPING = {
    '1m': '1m',
    '5m': '5m',
    '10m': '15m',  # Yahoo Finance uses 15m for 10m equivalent
    '30m': '30m',
    '1h': '1h',
    '3h': '1h',    # Yahoo Finance doesn't have 3h, using 1h
    '6h': '1h',    # Yahoo Finance doesn't have 6h, using 1h
    '12h': '1h',   # Yahoo Finance doesn't have 12h, using 1h
    '1d': '1d'
}

# Expanded list of financial instruments
FINANCIAL_INSTRUMENTS = {
    # Stocks - US Companies
    'AAPL': {'name': 'Apple Inc.', 'type': 'stock'},
    'GOOGL': {'name': 'Alphabet Inc.', 'type': 'stock'},
    'MSFT': {'name': 'Microsoft Corp.', 'type': 'stock'},
    'TSLA': {'name': 'Tesla Inc.', 'type': 'stock'},
    'AMZN': {'name': 'Amazon.com Inc.', 'type': 'stock'},
    'META': {'name': 'Meta Platforms Inc.', 'type': 'stock'},
    'NVDA': {'name': 'NVIDIA Corp.', 'type': 'stock'},
    'NFLX': {'name': 'Netflix Inc.', 'type': 'stock'},
    'DIS': {'name': 'The Walt Disney Co.', 'type': 'stock'},
    'V': {'name': 'Visa Inc.', 'type': 'stock'},
    'JPM': {'name': 'JPMorgan Chase & Co.', 'type': 'stock'},
    'WMT': {'name': 'Walmart Inc.', 'type': 'stock'},
    'PG': {'name': 'Procter & Gamble Co.', 'type': 'stock'},
    'KO': {'name': 'The Coca-Cola Co.', 'type': 'stock'},
    'XOM': {'name': 'Exxon Mobil Corp.', 'type': 'stock'},
    'BA': {'name': 'Boeing Co.', 'type': 'stock'},
    'IBM': {'name': 'International Business Machines Corp.', 'type': 'stock'},
    'GS': {'name': 'Goldman Sachs Group Inc.', 'type': 'stock'},
    'HD': {'name': 'Home Depot Inc.', 'type': 'stock'},
    'MA': {'name': 'Mastercard Inc.', 'type': 'stock'},
    
    # Stocks - European Companies
    'NESN.SW': {'name': 'Nestle SA', 'type': 'stock'},
    'ROG.SW': {'name': 'Roche Holding AG', 'type': 'stock'},
    'NOVN.SW': {'name': 'Novartis AG', 'type': 'stock'},
    'SAP.DE': {'name': 'SAP SE', 'type': 'stock'},
    'SIE.DE': {'name': 'Siemens AG', 'type': 'stock'},
    'BMW.DE': {'name': 'Bayerische Motoren Werke AG', 'type': 'stock'},
    'DAI.DE': {'name': 'Daimler AG', 'type': 'stock'},
    'AIR.PA': {'name': 'Airbus SE', 'type': 'stock'},
    'SAN.PA': {'name': 'Sanofi SA', 'type': 'stock'},
    'BNP.PA': {'name': 'BNP Paribas SA', 'type': 'stock'},
    'ENEL.MI': {'name': 'Enel SpA', 'type': 'stock'},
    'ENI.MI': {'name': 'Eni SpA', 'type': 'stock'},
    'UCG.MI': {'name': 'UniCredit SpA', 'type': 'stock'},
    'INGA.NL': {'name': 'ING Groep NV', 'type': 'stock'},
    'ASML.NL': {'name': 'ASML Holding NV', 'type': 'stock'},
    'UNA.NL': {'name': 'Unilever NV', 'type': 'stock'},
    'RDSA.NL': {'name': 'Royal Dutch Shell PLC', 'type': 'stock'},
    'BP.L': {'name': 'BP PLC', 'type': 'stock'},
    'HSBA.L': {'name': 'HSBC Holdings PLC', 'type': 'stock'},
    'BARC.L': {'name': 'Barclays PLC', 'type': 'stock'},
    'VOD.L': {'name': 'Vodafone Group PLC', 'type': 'stock'},
    'AZN.L': {'name': 'AstraZeneca PLC', 'type': 'stock'},
    'GSK.L': {'name': 'GlaxoSmithKline PLC', 'type': 'stock'},
    
    # Stocks - Russian Companies
    'GAZP.ME': {'name': 'Gazprom PJSC', 'type': 'stock'},
    'LKOH.ME': {'name': 'Lukoil PJSC', 'type': 'stock'},
    'SBER.ME': {'name': 'Sberbank of Russia', 'type': 'stock'},
    'ROSN.ME': {'name': 'Rosneft Oil Co.', 'type': 'stock'},
    'GMKN.ME': {'name': 'GMK Norilsk Nickel', 'type': 'stock'},
    'NVTK.ME': {'name': 'Novatek PJSC', 'type': 'stock'},
    'ALRS.ME': {'name': 'Alrosa Co.', 'type': 'stock'},
    'TATN.ME': {'name': 'Tatneft PJSC', 'type': 'stock'},
    'SNGS.ME': {'name': 'Surgutneftegas PJSC', 'type': 'stock'},
    'CHMF.ME': {'name': 'Severstal PJSC', 'type': 'stock'},
    'NLMK.ME': {'name': 'Novolipetsk Steel', 'type': 'stock'},
    'MGNT.ME': {'name': 'Magnit PJSC', 'type': 'stock'},
    'MTSS.ME': {'name': 'MTS PJSC', 'type': 'stock'},
    'FEES.ME': {'name': 'FEES', 'type': 'stock'},
    'HYDR.ME': {'name': 'RusHydro PJSC', 'type': 'stock'},
    
    # Stocks - Chinese Companies
    'BABA': {'name': 'Alibaba Group Holding Ltd.', 'type': 'stock'},
    'TCEHY': {'name': 'Tencent Holdings Ltd.', 'type': 'stock'},
    'BIDU': {'name': 'Baidu Inc.', 'type': 'stock'},
    'JD': {'name': 'JD.com Inc.', 'type': 'stock'},
    'NTES': {'name': 'NetEase Inc.', 'type': 'stock'},
    '0700.HK': {'name': 'Tencent Holdings Ltd.', 'type': 'stock'},
    '9988.HK': {'name': 'Alibaba Group Holding Ltd.', 'type': 'stock'},
    '3690.HK': {'name': 'Meituan Dianping', 'type': 'stock'},
    '1810.HK': {'name': 'Xiaomi Corp.', 'type': 'stock'},
    '1211.HK': {'name': 'BYD Co. Ltd.', 'type': 'stock'},
    '601398.SS': {'name': 'Industrial and Commercial Bank of China', 'type': 'stock'},
    '601328.SS': {'name': 'Bank of Communications Co. Ltd.', 'type': 'stock'},
    '601988.SS': {'name': 'Bank of China', 'type': 'stock'},
    '601939.SS': {'name': 'China Construction Bank Corp.', 'type': 'stock'},
    '601857.SS': {'name': 'PetroChina Co. Ltd.', 'type': 'stock'},
    '601628.SS': {'name': 'China Life Insurance Co. Ltd.', 'type': 'stock'},
    '601601.SS': {'name': 'China Pacific Insurance Group Co.', 'type': 'stock'},
    '601318.SS': {'name': 'Ping An Insurance Group Co.', 'type': 'stock'},
    '600519.SS': {'name': 'Kweichow Moutai Co. Ltd.', 'type': 'stock'},
    '601088.SS': {'name': 'China Shenhua Energy Co.', 'type': 'stock'},
    '601668.SS': {'name': 'China State Construction Engineering Corp.', 'type': 'stock'},
    '601899.SS': {'name': 'Zijin Mining Group Co.', 'type': 'stock'},
    '601658.SS': {'name': 'Postal Savings Bank of China', 'type': 'stock'},
    '601788.SS': {'name': 'Everbright Securities Co.', 'type': 'stock'},
    '601878.SS': {'name': 'Zhejiang Jetta Co.', 'type': 'stock'},
    '601633.SS': {'name': 'Great Wall Motor Co.', 'type': 'stock'},
    '601012.SS': {'name': 'Longi Green Energy Technology Co.', 'type': 'stock'},
    '601888.SS': {'name': 'China Tourism Group Duty Free Corp.', 'type': 'stock'},
    '601166.SS': {'name': 'Industrial Bank Co. Ltd.', 'type': 'stock'},
    '600036.SS': {'name': 'China Merchants Bank Co. Ltd.', 'type': 'stock'},
    '601288.SS': {'name': 'Agricultural Bank of China', 'type': 'stock'},
    '601998.SS': {'name': 'China CITIC Bank Corp.', 'type': 'stock'},
    '601766.SS': {'name': 'CRRC Corp.', 'type': 'stock'},
    '601919.SS': {'name': 'China COSCO Shipping Corp.', 'type': 'stock'},
    '601800.SS': {'name': 'China Communications Construction Co.', 'type': 'stock'},
    '601390.SS': {'name': 'China Railway Group Ltd.', 'type': 'stock'},
    '601600.SS': {'name': 'Aluminum Corp. of China Ltd.', 'type': 'stock'},
    '601991.SS': {'name': 'Datang International Power Generation Co.', 'type': 'stock'},
    '601117.SS': {'name': 'China Chemical Construction Corp.', 'type': 'stock'},
    '601618.SS': {'name': 'Metallurgical Corp. of China', 'type': 'stock'},
    '601169.SS': {'name': 'Bank of Beijing Co.', 'type': 'stock'},
    '601997.SS': {'name': 'Bank of Guiyang Co.', 'type': 'stock'},
    '601838.SS': {'name': 'Chengdu Bank Co.', 'type': 'stock'},
    '601211.SS': {'name': 'Guotai Junan Securities Co.', 'type': 'stock'},
    '601099.SS': {'name': 'China Pacific Securities Co.', 'type': 'stock'},
    '601375.SS': {'name': 'Central China Securities Co.', 'type': 'stock'},
    '601963.SS': {'name': 'Bank of Chongqing Co.', 'type': 'stock'},
    '601138.SS': {'name': 'Industrial Bank Co.', 'type': 'stock'},
    '601168.SS': {'name': 'Western Mining Co.', 'type': 'stock'},
    '601009.SS': {'name': 'Bank of Nanjing Co.', 'type': 'stock'},
    '601872.SS': {'name': 'China Merchants Energy Shipping Co.', 'type': 'stock'},
    '601608.SS': {'name': 'CITIC Heavy Industries Co.', 'type': 'stock'},
    '601727.SS': {'name': 'Shanghai Electric Group Co.', 'type': 'stock'},
    '601106.SS': {'name': 'China Heavy Duty Truck Group Co.', 'type': 'stock'},
    '601958.SS': {'name': 'Jinduicheng Molybdenum Co.', 'type': 'stock'},
    '601066.SS': {'name': 'China International Capital Corp.', 'type': 'stock'},
    '601607.SS': {'name': 'Shanghai Pharmaceuticals Holding Co.', 'type': 'stock'},
    '601860.SS': {'name': 'Bank of Suzhou Co.', 'type': 'stock'},
    '601577.SS': {'name': 'Changsha Bank Co.', 'type': 'stock'},
    '601366.SS': {'name': 'Liber Securities Co.', 'type': 'stock'},
    '601236.SS': {'name': 'Red Star Macalline Group Corp.', 'type': 'stock'},
    '601077.SS': {'name': 'Bank of Chengdu Co.', 'type': 'stock'},
    '601827.SS': {'name': 'Chongqing Department Store Co.', 'type': 'stock'},
    '601127.SS': {'name': 'Changan Automobile Co.', 'type': 'stock'},
    '601360.SS': {'name': '360 Security Technology Inc.', 'type': 'stock'},
    '601965.SS': {'name': 'China Automotive Engineering Research Co.', 'type': 'stock'},
    '601992.SS': {'name': 'China National Building Material Co.', 'type': 'stock'},
    '601718.SS': {'name': 'FAW Jiefang Group Co.', 'type': 'stock'},
    '601100.SS': {'name': 'Jiangsu Hengli Hydraulic Co.', 'type': 'stock'},
    '601101.SS': {'name': 'Beijing Jingneng Power Co.', 'type': 'stock'},
    '601118.SS': {'name': 'Hainan Rubber Industry Group Co.', 'type': 'stock'},
    '601011.SS': {'name': 'Baotou Huazi Industry Co.', 'type': 'stock'},
    '601952.SS': {'name': 'Sinochem International Corp.', 'type': 'stock'},
    '601038.SS': {'name': 'China First Tractor Co.', 'type': 'stock'},
    '601003.SS': {'name': 'Liuzhou Iron and Steel Co.', 'type': 'stock'},
    '601001.SS': {'name': 'Datong Coal Industry Co.', 'type': 'stock'},
    '601005.SS': {'name': 'Chongqing Iron and Steel Co.', 'type': 'stock'},
    '601007.SS': {'name': 'Jinling Pharmaceutical Co.', 'type': 'stock'},
    '601008.SS': {'name': 'Lianyungang Port Co.', 'type': 'stock'},
    '601010.SS': {'name': 'Wuwei Tongfei Heavy Industry Co.', 'type': 'stock'},
    '601015.SS': {'name': 'Shanxi Kaia Group Co.', 'type': 'stock'},
    '601016.SS': {'name': 'Norinco Guofang Energy Co.', 'type': 'stock'},
    '601018.SS': {'name': 'Ningbo Port Co.', 'type': 'stock'},
    '601019.SS': {'name': 'Shandong Gold Mining Co.', 'type': 'stock'},
    '601021.SS': {'name': 'Spring Airlines Co.', 'type': 'stock'},
    '601028.SS': {'name': 'Jiangsu Yuyue Medical Equipment Co.', 'type': 'stock'},
    '601058.SS': {'name': 'Sailun Group Co.', 'type': 'stock'},
    '601086.SS': {'name': 'Guoqing First Machinery Group Co.', 'type': 'stock'},
    '601098.SS': {'name': 'China South Publishing & Media Group Co.', 'type': 'stock'},
    '601107.SS': {'name': 'Sichuan Chengnan Expressway Co.', 'type': 'stock'},
    '601108.SS': {'name': 'Sichuan Minjiang Hydropower Co.', 'type': 'stock'},
    '601111.SS': {'name': 'Air China Ltd.', 'type': 'stock'},
    '601116.SS': {'name': 'Sichuan Emei Mountain Tourism Group Co.', 'type': 'stock'},
    '601126.SS': {'name': 'Chongqing Changan Automobile Co.', 'type': 'stock'},
    '601128.SS': {'name': 'Changshu Rural Commercial Bank Co.', 'type': 'stock'},
    '601137.SS': {'name': 'Xinjiang Goldwind Science & Technology Co.', 'type': 'stock'},
    '601139.SS': {'name': 'Shenzhen International Holdings Ltd.', 'type': 'stock'},
    '601155.SS': {'name': 'New City Development Co.', 'type': 'stock'},
    '601158.SS': {'name': 'Chongqing Water Group Co.', 'type': 'stock'},
    '601177.SS': {'name': 'Hangzhou Steam Turbine Co.', 'type': 'stock'},
    '601179.SS': {'name': 'China West Construction Co.', 'type': 'stock'},
    '601188.SS': {'name': 'Dragonhead Liquor Co.', 'type': 'stock'},
    '601198.SS': {'name': 'Dongxing Securities Co.', 'type': 'stock'},
    '601199.SS': {'name': 'Jiangsu Union Chemical Co.', 'type': 'stock'},
    '601200.SS': {'name': 'Shanghai International Port Group Co.', 'type': 'stock'},
    '601212.SS': {'name': 'Bank of Gansu Co.', 'type': 'stock'},
    '601216.SS': {'name': 'Inner Mongolia Junzheng Energy & Chemical Group Co.', 'type': 'stock'},
    '601222.SS': {'name': 'Jiangsu Yanghe Brewery Joint-Stock Co.', 'type': 'stock'},
    '601225.SS': {'name': 'Shaanxi Coal Industry Co.', 'type': 'stock'},
    '601229.SS': {'name': 'Bank of Shanghai Co.', 'type': 'stock'},
    '601231.SS': {'name': 'Ningbo Joyson Electronic Corp.', 'type': 'stock'},
    '601233.SS': {'name': 'Tongkun Group Co.', 'type': 'stock'},
    '601238.SS': {'name': 'Guangzhou Automobile Group Co.', 'type': 'stock'},
    '601258.SS': {'name': 'Liaoning Chengda Co.', 'type': 'stock'},
    '601298.SS': {'name': 'China COSCO Shipping Corp.', 'type': 'stock'},
    '601299.SS': {'name': 'CRRC Corp.', 'type': 'stock'},
    '601333.SS': {'name': 'China Railway Group Ltd.', 'type': 'stock'},
    '601336.SS': {'name': 'New China Life Insurance Co.', 'type': 'stock'},
    '601368.SS': {'name': 'Guangxi Wuzhou Zhongheng Group Co.', 'type': 'stock'},
    '601369.SS': {'name': 'Shaanxi Shaangu Power Co.', 'type': 'stock'},
    '601377.SS': {'name': 'Industrial Securities Co.', 'type': 'stock'},
    '601388.SS': {'name': 'Yuyao City Urban Construction Investment Development Co.', 'type': 'stock'},
    '601500.SS': {'name': 'Jiangsu Eastern Shenghong Co.', 'type': 'stock'},
    '601515.SS': {'name': 'Dongfeng Agricultural Machinery Group Co.', 'type': 'stock'},
    '601518.SS': {'name': 'Jilin Expressway Co.', 'type': 'stock'},
    '601519.SS': {'name': 'Shanghai Dajon Culture Development Co.', 'type': 'stock'},
    '601555.SS': {'name': 'Soochow Securities Co.', 'type': 'stock'},
    '601558.SS': {'name': 'Huatai Biding Co.', 'type': 'stock'},
    '601566.SS': {'name': 'Jiuyang Co.', 'type': 'stock'},
    '601567.SS': {'name': 'Shanghai Electric Group Co.', 'type': 'stock'},
    '601588.SS': {'name': 'Beijing North Star Co.', 'type': 'stock'},
    '601595.SS': {'name': 'Shanghai A & H Shares Index Fund', 'type': 'stock'},
    '601598.SS': {'name': 'China COSCO Shipping Corp.', 'type': 'stock'},
    '601599.SS': {'name': 'Lujiazui Finance & Tourism Zone Development Co.', 'type': 'stock'},
    '601606.SS': {'name': 'China Great Wall Securities Co.', 'type': 'stock'},
    '601611.SS': {'name': 'China Nuclear Engineering Corp.', 'type': 'stock'},
    '601615.SS': {'name': 'Mingyang Smart Energy Group Co.', 'type': 'stock'},
    '601669.SS': {'name': 'Power Construction Corp. of China', 'type': 'stock'},
    '601677.SS': {'name': 'Henan Mingtai Aluminum Co.', 'type': 'stock'},
    '601678.SS': {'name': 'Binzhou Bohai Piston Co.', 'type': 'stock'},
    '601688.SS': {'name': 'Huatai Securities Co.', 'type': 'stock'},
    '601689.SS': {'name': 'Tongling Nonferrous Metals Group Co.', 'type': 'stock'},
    '601699.SS': {'name': 'China Coal Energy Co.', 'type': 'stock'},
    '601700.SS': {'name': 'Fengfan Co.', 'type': 'stock'},
    '601717.SS': {'name': 'Zhengzhou Yutong Bus Co.', 'type': 'stock'},
    '601777.SS': {'name': 'Lifan Industry Co.', 'type': 'stock'},
    '601789.SS': {'name': 'Ningbo Construction Co.', 'type': 'stock'},
    '601808.SS': {'name': 'Offshore Oil Engineering Co.', 'type': 'stock'},
    '601816.SS': {'name': 'China Railway Group Ltd.', 'type': 'stock'},
    '601898.SS': {'name': 'China Coal Energy Co.', 'type': 'stock'},
    '601901.SS': {'name': 'Founder Securities Co.', 'type': 'stock'},
    '601918.SS': {'name': 'Xinjiang Yihua Chemical Co.', 'type': 'stock'},
    '601933.SS': {'name': 'Yonghui Superstores Co.', 'type': 'stock'},
    '601989.SS': {'name': 'China Shipbuilding Industry Co.', 'type': 'stock'},
    '603000.SS': {'name': 'People.cn Co.', 'type': 'stock'},
    '603160.SS': {'name': '汇顶科技Co.', 'type': 'stock'},
    '603259.SS': {'name': '药明康德Co.', 'type': 'stock'},
    '603288.SS': {'name': '海天味业Co.', 'type': 'stock'},
    '603369.SS': {'name': '今世缘Co.', 'type': 'stock'},
    '603515.SS': {'name': '欧普照明Co.', 'type': 'stock'},
    '603833.SS': {'name': '欧派家居Co.', 'type': 'stock'},
    '603986.SS': {'name': '兆易创新Co.', 'type': 'stock'},
    '603993.SS': {'name': '洛阳钼业Co.', 'type': 'stock'},
    '688008.SS': {'name': '澜起科技Co.', 'type': 'stock'},
    '688012.SS': {'name': '中微公司Co.', 'type': 'stock'},
    '688111.SS': {'name': '金山办公Co.', 'type': 'stock'},
    '688188.SS': {'name': '柏楚电子Co.', 'type': 'stock'},
    '688396.SS': {'name': '华润微电子Co.', 'type': 'stock'},
    '688981.SS': {'name': '中芯国际Co.', 'type': 'stock'},
    '000001.SZ': {'name': '平安银行Co.', 'type': 'stock'},
    '000002.SZ': {'name': '万科A Co.', 'type': 'stock'},
    '000063.SZ': {'name': '中兴通讯Co.', 'type': 'stock'},
    '000333.SZ': {'name': '美的集团Co.', 'type': 'stock'},
    '000338.SZ': {'name': '潍柴动力Co.', 'type': 'stock'},
    '000425.SZ': {'name': '徐工机械Co.', 'type': 'stock'},
    '000538.SZ': {'name': '云南白药Co.', 'type': 'stock'},
    '000568.SZ': {'name': '泸州老窖Co.', 'type': 'stock'},
    '000625.SZ': {'name': '长安汽车Co.', 'type': 'stock'},
    '000651.SZ': {'name': '格力电器Co.', 'type': 'stock'},
    '000725.SZ': {'name': '京东方A Co.', 'type': 'stock'},
    '000728.SZ': {'name': '国元证券Co.', 'type': 'stock'},
    '000768.SZ': {'name': '中航飞机Co.', 'type': 'stock'},
    '000776.SZ': {'name': '广发证券Co.', 'type': 'stock'},
    '000783.SZ': {'name': '长江证券Co.', 'type': 'stock'},
    '000786.SZ': {'name': '北新建材Co.', 'type': 'stock'},
    '000831.SZ': {'name': '五矿稀土Co.', 'type': 'stock'},
    '000858.SZ': {'name': '五粮液Co.', 'type': 'stock'},
    '000876.SZ': {'name': '新希望Co.', 'type': 'stock'},
    '000895.SZ': {'name': '双汇发展Co.', 'type': 'stock'},
    '000938.SZ': {'name': '紫光股份Co.', 'type': 'stock'},
    '000963.SZ': {'name': '华东医药Co.', 'type': 'stock'},
    '001979.SZ': {'name': '招商蛇口Co.', 'type': 'stock'},
    '002001.SZ': {'name': '新和成Co.', 'type': 'stock'},
    '002007.SZ': {'name': '华兰生物Co.', 'type': 'stock'},
    '002008.SZ': {'name': '大族激光Co.', 'type': 'stock'},
    '002024.SZ': {'name': '苏宁易购Co.', 'type': 'stock'},
    '002027.SZ': {'name': '分众传媒Co.', 'type': 'stock'},
    '002032.SZ': {'name': '苏泊尔Co.', 'type': 'stock'},
    '002044.SZ': {'name': '美年健康Co.', 'type': 'stock'},
    '002050.SZ': {'name': '三花智控Co.', 'type': 'stock'},
    '002120.SZ': {'name': '韵达股份Co.', 'type': 'stock'},
    '002129.SZ': {'name': '中环股份Co.', 'type': 'stock'},
    '002142.SZ': {'name': '宁波银行Co.', 'type': 'stock'},
    '002146.SZ': {'name': '荣盛发展Co.', 'type': 'stock'},
    '002153.SZ': {'name': '石基信息Co.', 'type': 'stock'},
    '002157.SZ': {'name': '正邦科技Co.', 'type': 'stock'},
    '002179.SZ': {'name': '中航光电Co.', 'type': 'stock'},
    '002202.SZ': {'name': '金风科技Co.', 'type': 'stock'},
    '002230.SZ': {'name': '科大讯飞Co.', 'type': 'stock'},
    '002236.SZ': {'name': '大华股份Co.', 'type': 'stock'},
    '002241.SZ': {'name': '歌尔股份Co.', 'type': 'stock'},
    '002258.SZ': {'name': '利尔化学Co.', 'type': 'stock'},
    '002271.SZ': {'name': '东方雨虹Co.', 'type': 'stock'},
    '002304.SZ': {'name': '洋河股份Co.', 'type': 'stock'},
    '002311.SZ': {'name': '海大集团Co.', 'type': 'stock'},
    '002352.SZ': {'name': '顺丰控股Co.', 'type': 'stock'},
    '002353.SZ': {'name': '杰瑞股份Co.', 'type': 'stock'},
    '002371.SZ': {'name': '北方华创Co.', 'type': 'stock'},
    '002410.SZ': {'name': '广联达Co.', 'type': 'stock'},
    '002415.SZ': {'name': '海康威视Co.', 'type': 'stock'},
    '002422.SZ': {'name': '科伦药业Co.', 'type': 'stock'},
    '002456.SZ': {'name': '欧菲光Co.', 'type': 'stock'},
    '002460.SZ': {'name': '赣锋锂业Co.', 'type': 'stock'},
    '002463.SZ': {'name': '沪电股份Co.', 'type': 'stock'},
    '002466.SZ': {'name': '天齐锂业Co.', 'type': 'stock'},
    '002475.SZ': {'name': '立讯精密Co.', 'type': 'stock'},
    '002493.SZ': {'name': '荣盛石化Co.', 'type': 'stock'},
    '002508.SZ': {'name': '老板电器Co.', 'type': 'stock'},
    '002555.SZ': {'name': '三七互娱Co.', 'type': 'stock'},
    '002558.SZ': {'name': '巨人网络Co.', 'type': 'stock'},
    '002594.SZ': {'name': '比亚迪Co.', 'type': 'stock'},
    '002601.SZ': {'name': '龙蟒佰利Co.', 'type': 'stock'},
    '002602.SZ': {'name': '世纪华通Co.', 'type': 'stock'},
    '002607.SZ': {'name': '中公教育Co.', 'type': 'stock'},
    '002624.SZ': {'name': '完美世界Co.', 'type': 'stock'},
    '002673.SZ': {'name': '西部证券Co.', 'type': 'stock'},
    '002714.SZ': {'name': '牧原股份Co.', 'type': 'stock'},
    '002736.SZ': {'name': '国信证券Co.', 'type': 'stock'},
    '002739.SZ': {'name': '万达电影Co.', 'type': 'stock'},
    '002841.SZ': {'name': '视源股份Co.', 'type': 'stock'},
    '002916.SZ': {'name': '深南电路Co.', 'type': 'stock'},
    '002938.SZ': {'name': '鹏鼎控股Co.', 'type': 'stock'},
    '002939.SZ': {'name': '长城证券Co.', 'type': 'stock'},
    '002945.SZ': {'name': '华林证券Co.', 'type': 'stock'},
    '002958.SZ': {'name': '青农商行Co.', 'type': 'stock'},
    '003816.SZ': {'name': '中国广核Co.', 'type': 'stock'},
    '300015.SZ': {'name': '爱尔眼科Co.', 'type': 'stock'},
    '300033.SZ': {'name': '同花顺Co.', 'type': 'stock'},
    '300059.SZ': {'name': '东方财富Co.', 'type': 'stock'},
    '300122.SZ': {'name': '智飞生物Co.', 'type': 'stock'},
    '300124.SZ': {'name': '汇川技术Co.', 'type': 'stock'},
    '300136.SZ': {'name': '信维通信Co.', 'type': 'stock'},
    '300142.SZ': {'name': '沃森生物Co.', 'type': 'stock'},
    '300144.SZ': {'name': '宋城演艺Co.', 'type': 'stock'},
    '300347.SZ': {'name': '泰格医药Co.', 'type': 'stock'},
    '300408.SZ': {'name': '三环集团Co.', 'type': 'stock'},
    '300413.SZ': {'name': '芒果超媒Co.', 'type': 'stock'},
    '300433.SZ': {'name': '蓝思科技Co.', 'type': 'stock'},
    '300450.SZ': {'name': '先导智能Co.', 'type': 'stock'},
    '300498.SZ': {'name': '温氏股份Co.', 'type': 'stock'},
    '300601.SZ': {'name': '康泰生物Co.', 'type': 'stock'},
    '300628.SZ': {'name': '亿联网络Co.', 'type': 'stock'},
    '300750.SZ': {'name': '宁德时代Co.', 'type': 'stock'},
    '300760.SZ': {'name': '迈瑞医疗Co.', 'type': 'stock'},
    '300896.SZ': {'name': '爱美客Co.', 'type': 'stock'},
    '300979.SZ': {'name': '华利集团Co.', 'type': 'stock'},
    '300981.SZ': {'name': '中红医疗Co.', 'type': 'stock'},
    '300999.SZ': {'name': '金龙鱼Co.', 'type': 'stock'},
    
    # Cryptocurrencies
    'bitcoin': {'name': 'Bitcoin', 'type': 'crypto'},
    'ethereum': {'name': 'Ethereum', 'type': 'crypto'},
    'solana': {'name': 'Solana', 'type': 'crypto'},
    'cardano': {'name': 'Cardano', 'type': 'crypto'},
    'polkadot': {'name': 'Polkadot', 'type': 'crypto'},
    'litecoin': {'name': 'Litecoin', 'type': 'crypto'},
    'chainlink': {'name': 'Chainlink', 'type': 'crypto'},
    'bitcoin-cash': {'name': 'Bitcoin Cash', 'type': 'crypto'},
    'stellar': {'name': 'Stellar', 'type': 'crypto'},
    'uniswap': {'name': 'Uniswap', 'type': 'crypto'},
    'dogecoin': {'name': 'Dogecoin', 'type': 'crypto'},
    'avalanche': {'name': 'Avalanche', 'type': 'crypto'},
    'polygon': {'name': 'Polygon', 'type': 'crypto'},
    'cosmos': {'name': 'Cosmos', 'type': 'crypto'},
    'monero': {'name': 'Monero', 'type': 'crypto'},
    'tron': {'name': 'TRON', 'type': 'crypto'},
    'vechain': {'name': 'VeChain', 'type': 'crypto'},
    'filecoin': {'name': 'Filecoin', 'type': 'crypto'},
    'theta': {'name': 'Theta Network', 'type': 'crypto'},
    'eos': {'name': 'EOS', 'type': 'crypto'},
    'tezos': {'name': 'Tezos', 'type': 'crypto'},
    'elrond': {'name': 'Elrond', 'type': 'crypto'},
    'flow': {'name': 'Flow', 'type': 'crypto'},
    'klaytn': {'name': 'Klaytn', 'type': 'crypto'},
    'near': {'name': 'NEAR Protocol', 'type': 'crypto'},
    'hedera': {'name': 'Hedera Hashgraph', 'type': 'crypto'},
    'algorand': {'name': 'Algorand', 'type': 'crypto'},
    'iota': {'name': 'IOTA', 'type': 'crypto'},
    'dash': {'name': 'Dash', 'type': 'crypto'},
    'zcash': {'name': 'Zcash', 'type': 'crypto'},
    
    # Precious Metals
    'GC=F': {'name': 'Gold Futures', 'type': 'commodity'},
    'SI=F': {'name': 'Silver Futures', 'type': 'commodity'},
    'PL=F': {'name': 'Platinum Futures', 'type': 'commodity'},
    'PA=F': {'name': 'Palladium Futures', 'type': 'commodity'},
    'HG=F': {'name': 'Copper Futures', 'type': 'commodity'},
    
    # Additional Precious Metals and Commodities
    'XAUUSD=X': {'name': 'Gold Spot', 'type': 'commodity'},
    'XAGUSD=X': {'name': 'Silver Spot', 'type': 'commodity'},
    'XPTUSD=X': {'name': 'Platinum Spot', 'type': 'commodity'},
    'XPDUSD=X': {'name': 'Palladium Spot', 'type': 'commodity'},
    'CL=F': {'name': 'Crude Oil Futures', 'type': 'commodity'},
    'NG=F': {'name': 'Natural Gas Futures', 'type': 'commodity'},
    'CT=F': {'name': 'Cotton Futures', 'type': 'commodity'},
    'KC=F': {'name': 'Coffee Futures', 'type': 'commodity'},
    'SB=F': {'name': 'Sugar Futures', 'type': 'commodity'},
    'CC=F': {'name': 'Cocoa Futures', 'type': 'commodity'},
    'LE=F': {'name': 'Live Cattle Futures', 'type': 'commodity'},
    'HE=F': {'name': 'Lean Hogs Futures', 'type': 'commodity'},
    'ZW=F': {'name': 'Wheat Futures', 'type': 'commodity'},
    'ZC=F': {'name': 'Corn Futures', 'type': 'commodity'},
    'ZO=F': {'name': 'Oat Futures', 'type': 'commodity'},
    'KE=F': {'name': 'Wheat Futures (Kansas)', 'type': 'commodity'},
    'ZR=F': {'name': 'Rough Rice Futures', 'type': 'commodity'},
    'GF=F': {'name': 'Feeder Cattle Futures', 'type': 'commodity'},
    
    # Forex pairs
    'EURUSD': {'name': 'Euro/US Dollar', 'type': 'forex'},
    'GBPUSD': {'name': 'British Pound/US Dollar', 'type': 'forex'},
    'USDJPY': {'name': 'US Dollar/Japanese Yen', 'type': 'forex'},
    'AUDUSD': {'name': 'Australian Dollar/US Dollar', 'type': 'forex'},
    'USDCAD': {'name': 'US Dollar/Canadian Dollar', 'type': 'forex'},
    'USDCHF': {'name': 'US Dollar/Swiss Franc', 'type': 'forex'},
    'NZDUSD': {'name': 'New Zealand Dollar/US Dollar', 'type': 'forex'},
    'EURGBP': {'name': 'Euro/British Pound', 'type': 'forex'},
    'EURJPY': {'name': 'Euro/Japanese Yen', 'type': 'forex'},
    'GBPJPY': {'name': 'British Pound/Japanese Yen', 'type': 'forex'},
    'AUDJPY': {'name': 'Australian Dollar/Japanese Yen', 'type': 'forex'},
    'NZDJPY': {'name': 'New Zealand Dollar/Japanese Yen', 'type': 'forex'},
    'GBPNZD': {'name': 'British Pound/New Zealand Dollar', 'type': 'forex'},
    'EURAUD': {'name': 'Euro/Australian Dollar', 'type': 'forex'},
    'EURCHF': {'name': 'Euro/Swiss Franc', 'type': 'forex'},
    'CADJPY': {'name': 'Canadian Dollar/Japanese Yen', 'type': 'forex'},
    'CHFJPY': {'name': 'Swiss Franc/Japanese Yen', 'type': 'forex'},
    'USDMXN': {'name': 'US Dollar/Mexican Peso', 'type': 'forex'},
    'USDZAR': {'name': 'US Dollar/South African Rand', 'type': 'forex'},
    'USDRUB': {'name': 'US Dollar/Russian Ruble', 'type': 'forex'},
    'EURRUB': {'name': 'Euro/Russian Ruble', 'type': 'forex'},
    'GBPRUB': {'name': 'British Pound/Russian Ruble', 'type': 'forex'}
}

# Connection limits
MAX_CLIENTS = 1000
HEARTBEAT_INTERVAL = 30  # seconds
CLIENT_TIMEOUT = 120  # seconds

class WebSocketManager:
    """Manage WebSocket connections and data streaming"""
    
    def __init__(self):
        # Initialize components
        self.metrics = MetricsCollector.get_instance()
        self.data_manager = DataManager(self.metrics)
        self.subscription_manager = SubscriptionManager()
        self.connection_manager = ConnectionManager(self.metrics)
        self.delta_manager = DeltaManager()
        # Shutdown event for graceful shutdown
        self.shutdown_event = asyncio.Event()
    
    async def shutdown(self):
        """Graceful shutdown всех соединений"""
        await self.connection_manager.shutdown()
    
    async def health_check_worker(self):
        """Периодическая проверка здоровья соединений"""
        await self.connection_manager.health_check_worker()
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> Optional[str]:
        """Handle new WebSocket connection"""
        return await self.connection_manager.connect(websocket, client_id)
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        await self.connection_manager.disconnect(websocket)
    
    async def _send_to_clients(self, clients, message):
        """Send message to specific clients"""
        message_str = json.dumps(message)
        disconnected_clients = set()
        
        for client in clients:
            try:
                # Check if client is still alive by sending a small message
                await asyncio.wait_for(client.send_text(message_str), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(f"Client timeout during data send")
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending data to client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.disconnect(client)
    
    async def send_initial_data(self, websocket: WebSocket):
        """Send initial data to newly connected client"""
        try:
            # Get initial data for default instruments
            default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
            assets_data = await self.get_assets_data(default_symbols)
            
            # Send initialization message
            init_message = {
                "type": "init",
                "timestamp": datetime.now().isoformat(),
                "data": assets_data
            }
            await websocket.send_text(json.dumps(init_message))
            
            # Send periodic updates
            update_message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": assets_data
            }
            await websocket.send_text(json.dumps(update_message))
            
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
            error_message = {
                "type": "error",
                "message": "Error initializing connection"
            }
            await websocket.send_text(json.dumps(error_message))
    
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'refresh':
                await self.handle_refresh(websocket)
            elif action == 'add_asset':
                await self.handle_add_asset(websocket, data.get('symbol'))
            elif action == 'remove_asset':
                await self.handle_remove_asset(websocket, data.get('symbol'))
            elif action == 'set_timeframe':
                await self.handle_set_timeframe(websocket, data.get('timeframe', '5m'))
            elif action == 'subscribe':
                await self.handle_subscribe(websocket, data.get('symbols', []))
            elif action == 'unsubscribe':
                await self.handle_unsubscribe(websocket, data.get('symbols', []))
            elif action == 'heartbeat':
                await self.handle_heartbeat(websocket)
            else:
                logger.warning(f"Unknown action received: {action}")
                error_message = {
                    "type": "error",
                    "message": f"Unknown action: {action}"
                }
                await websocket.send_text(json.dumps(error_message))
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON message: {e}")
            error_message = {
                "type": "error",
                "message": "Invalid JSON format"
            }
            await websocket.send_text(json.dumps(error_message))
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            error_message = {
                "type": "error",
                "message": "Error processing request"
            }
            await websocket.send_text(json.dumps(error_message))
    
    async def handle_refresh(self, websocket: WebSocket):
        """Handle refresh action"""
        try:
            # Get client ID
            client_id = self.connection_manager.get_client_id(websocket)
            if not client_id:
                return
            
            # Refresh all data for client's subscriptions or default symbols
            symbols = list(self.subscription_manager.get_client_subscriptions(client_id))
            if not symbols:
                symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
            
            assets_data = await self.get_assets_data(symbols[:15])  # Limit for performance
            update_message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": assets_data
            }
            await self.connection_manager.send_message(websocket, update_message)
        except Exception as e:
            logger.error(f"Error handling refresh: {e}")
    
    async def handle_add_asset(self, websocket: WebSocket, symbol: str):
        """Handle add asset action"""
        if symbol:
            try:
                # Get client ID
                client_id = self.connection_manager.get_client_id(websocket)
                if not client_id:
                    return
                
                # Add to subscription manager
                self.subscription_manager.subscribe(client_id, [symbol.upper()])
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(self.subscription_manager.get_client_subscriptions(client_id))
                }
                await self.connection_manager.send_message(websocket, watchlist_message)
            except Exception as e:
                logger.error(f"Error adding asset {symbol}: {e}")
    
    async def handle_remove_asset(self, websocket: WebSocket, symbol: str):
        """Handle remove asset action"""
        if symbol:
            try:
                # Get client ID
                client_id = self.connection_manager.get_client_id(websocket)
                if not client_id:
                    return
                
                # Remove from subscription manager
                self.subscription_manager.unsubscribe(client_id, [symbol.upper()])
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(self.subscription_manager.get_client_subscriptions(client_id))
                }
                await self.connection_manager.send_message(websocket, watchlist_message)
            except Exception as e:
                logger.error(f"Error removing asset {symbol}: {e}")
    
    async def handle_set_timeframe(self, websocket: WebSocket, timeframe: str):
        """Handle set timeframe action"""
        try:
            # In a real implementation, this would affect data fetching
            # For now, we'll just acknowledge the change
            notification_message = {
                "type": "notification",
                "message": f"Timeframe set to {timeframe}"
            }
            await self.connection_manager.send_message(websocket, notification_message)
        except Exception as e:
            logger.error(f"Error setting timeframe: {e}")
    
    async def handle_subscribe(self, websocket: WebSocket, symbols: List[str]):
        """Handle subscribe action"""
        if symbols:
            try:
                # Get client ID
                client_id = self.connection_manager.get_client_id(websocket)
                if not client_id:
                    return
                
                # Add symbols to subscription manager
                self.subscription_manager.subscribe(client_id, [s.upper() for s in symbols])
                
                notification_message = {
                    "type": "notification",
                    "message": f"Subscribed to {len(symbols)} assets"
                }
                await self.connection_manager.send_message(websocket, notification_message)
            except Exception as e:
                logger.error(f"Error subscribing to assets: {e}")
    
    async def handle_unsubscribe(self, websocket: WebSocket, symbols: List[str]):
        """Handle unsubscribe action"""
        if symbols:
            try:
                # Get client ID
                client_id = self.connection_manager.get_client_id(websocket)
                if not client_id:
                    return
                
                # Remove symbols from subscription manager
                self.subscription_manager.unsubscribe(client_id, [s.upper() for s in symbols])
                
                notification_message = {
                    "type": "notification",
                    "message": f"Unsubscribed from {len(symbols)} assets"
                }
                await self.connection_manager.send_message(websocket, notification_message)
            except Exception as e:
                logger.error(f"Error unsubscribing from assets: {e}")
    
    async def handle_heartbeat(self, websocket: WebSocket):
        """Handle heartbeat action"""
        try:
            # Update last heartbeat time
            self.connection_manager.update_heartbeat(websocket)
                
            # Send heartbeat response
            response = {
                "type": "heartbeat_response",
                "timestamp": datetime.now().isoformat()
            }
            await self.connection_manager.send_message(websocket, response)
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
    
    async def get_assets_data(self, symbols: List[str]) -> List[Dict]:
        """Get data for multiple assets with semaphore for concurrency control"""
        return await self.data_manager.get_assets_data(symbols)
    
    async def get_single_asset_data(self, symbol: str) -> Optional[Dict]:
        """Get data for a single asset"""
        return await self.data_manager.get_asset_data(symbol)
    
    async def data_stream_worker(self):
        """Background worker to stream data to subscribed clients only with performance optimizations"""
        while not self.shutdown_event.is_set():
            try:
                # Get all subscribed symbols
                unique_symbols = self.subscription_manager.get_all_subscribed_symbols()
                if not unique_symbols:
                    # If no subscriptions, send data for default symbols
                    unique_symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F'][:15]
                
                # Early exit if no symbols to process
                if not unique_symbols:
                    await asyncio.sleep(15)  # Wait before next check
                    continue
                
                # Get data for symbols with optimized batch sizes
                batch_size = 50  # Increased from 30 for better performance
                all_assets_data = []
                
                # Process batches concurrently for better performance
                batch_tasks = []
                for i in range(0, len(unique_symbols), batch_size):
                    batch_symbols = unique_symbols[i:i + batch_size]
                    task = self.get_assets_data(batch_symbols)
                    batch_tasks.append(task)
                
                # Gather all batch results concurrently
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error in batch processing: {result}")
                        continue
                    elif result is not None and not isinstance(result, BaseException):
                        all_assets_data.extend(result)
                
                # Early exit if no data
                if not all_assets_data:
                    await asyncio.sleep(15)  # Wait before next check
                    continue
                
                # Send data to subscribed clients with improved efficiency
                # Group symbols by client to reduce iterations
                client_symbols = {}
                for symbol in unique_symbols:
                    client_ids = self.subscription_manager.get_symbol_subscribers(symbol)
                    for client_id in client_ids:
                        if client_id not in client_symbols:
                            client_symbols[client_id] = []
                        client_symbols[client_id].append(symbol)
                
                # Send updates to clients concurrently
                update_tasks = []
                for client_id, symbols in client_symbols.items():
                    # Get symbol data for this client
                    client_data = [d for d in all_assets_data if d['symbol'] in symbols]
                    if client_data:
                        # Apply delta updates
                        updated_data = []
                        for data in client_data:
                            delta = self.delta_manager.get_delta(data['symbol'], data)
                            if delta:  # Only send if there are changes
                                updated_data.append(data)
                        
                        if updated_data:
                            message = {
                                "type": "update",
                                "timestamp": datetime.now().isoformat(),
                                "data": updated_data
                            }
                            # Get websockets for client IDs
                            # Map client IDs to websockets
                            websockets_to_send = []
                            for websocket, client_info in self.connection_manager.active_connections.items():
                                if client_info["id"] == client_id:
                                    websockets_to_send.append(websocket)
                            
                            if websockets_to_send:
                                task = self.connection_manager.broadcast(message, websockets_to_send)
                                update_tasks.append(task)
                
                # Execute all client updates concurrently
                if update_tasks:
                    await asyncio.gather(*update_tasks, return_exceptions=True)
                
                # Wait before next update - adaptive timing based on number of symbols
                update_interval = max(10, 30 - len(unique_symbols) // 5)  # Minimum 10 seconds, more responsive
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in data stream worker: {e}")
                await asyncio.sleep(5)  # Wait before retrying

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """WebSocket с проверкой токена"""
    # Проверяем токен перед подключением, но разрешаем подключение без токена
    client_id = None
    if token:
        client_id = AuthManager.verify_token(token)
        if not client_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    
    # If no token provided, generate a temporary client ID
    if not client_id:
        client_id = f"anonymous_{uuid.uuid4().hex[:8]}"
    
    # Connect to websocket manager with the determined client ID
    connected_client_id = await websocket_manager.connect(websocket, client_id)
    if not connected_client_id:
        return
    
    heartbeat_task = None
    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_worker(websocket))
        
        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=CLIENT_TIMEOUT)
                await websocket_manager.handle_message(websocket, data)
            except asyncio.TimeoutError:
                logger.warning(f"Client {client_id} timed out")
                break
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error receiving message from client {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for client {client_id}: {e}")
    finally:
        # Clean up client resources
        if heartbeat_task:
            heartbeat_task.cancel()
        await websocket_manager.disconnect(websocket)

async def heartbeat_worker(websocket):
    """Send periodic heartbeats to keep connection alive"""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            # Update heartbeat
            websocket_manager.connection_manager.update_heartbeat(websocket)
            # Send heartbeat message
            heartbeat_message = {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }
            await websocket_manager.connection_manager.send_message(websocket, heartbeat_message)
    except Exception as e:
        logger.error(f"Error in heartbeat worker: {e}")

async def data_stream_worker():
    """Background worker to stream data to all connected clients"""
    await websocket_manager.data_stream_worker()