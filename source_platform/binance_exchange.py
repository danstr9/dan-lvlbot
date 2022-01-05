from datetime import *
import config
import ccxt
import time
from binance_data import DataClient

exchange = ccxt.binanceusdm({
    'enableRateLimit': True,
    "apiKey": config.CCXT_API_KEY,
    "secret": config.CCXT_API_SECRET
})
futures = True
client = DataClient(futures=futures)
