from datetime import *
import config
import ccxt
import time

# For FtxClient ----------------------------------------
import urllib.parse
from typing import Optional, Dict, Any, List
from requests import Request, Session, Response
import hmac
# ---------------

# Special class with FTX functions to get the candle data.
class FtxClient:
    _ENDPOINT = 'https://ftx.com/api/'

    def __init__(self, api_key=None, api_secret=None, subaccount_name=None) -> None:
        self._session = Session()
        self._api_key = api_key
        self._api_secret = api_secret
        self._subaccount_name = subaccount_name

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('GET', path, params=params)

    def _post(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('POST', path, json=params)

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request('DELETE', path, json=params)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        request = Request(method, self._ENDPOINT + path, **kwargs)
        self._sign_request(request)
        response = self._session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request) -> None:
        ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self._api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self._api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self._subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = urllib.parse.quote(self._subaccount_name)

    def _process_response(self, response: Response) -> Any:
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                raise Exception(data['error'])
            return data['result']

    def get_klines(self, market_name: str, resolution: int = 3600, limit: int = 1440,
                    start_time: int = None, end_time: int = None):
        # resolution: window length in seconds: 15, 60, 300, 900, 3600, 14400, 86400
        # limit: max number to fetch, optional, max 5000
        return self._get(f'markets/{market_name}/candles', {'resolution': resolution,
                                                            'limit': limit,
                                                            'start_time': start_time,
                                                            'end_time': end_time})

    def get_trades(self, market_name: str, limit: int = 1440, start_time: int = None, end_time: int = None):
        # resolution: window length in seconds: 15, 60, 300, 900, 3600, 14400, 86400
        # limit: max number to fetch, optional, max 5000
        return self._get(f'markets/{market_name}/trades', {'limit': limit,
                                                            'start_time': start_time,
                                                            'end_time': end_time})

    def get_orderbook(self, market: str, depth: int = None) -> dict:
        return self._get(f'markets/{market}/orderbook', {'depth': depth})

exchange = ccxt.ftx({
    "apiKey": config.FTX_LVL_API_KEY,
    "secret": config.FTX_LVL_API_SECRET,
    'enableRateLimit': True,
    'headers': {'FTX-SUBACCOUNT': config.FTX_LVL_SUBACCOUNT}
})
client = FtxClient(api_key=config.FTX_LVL_API_KEY, api_secret=config.FTX_LVL_API_SECRET)
# print("Exchange: FTX - {}".format(TF))
#
# print("SYMBOL: {}".format(SYMBOL))
# if not MULTI_TF:
#     print("Days back: {} \nNum. Candles: {}".format(DAYS_BACK, NUM_CANDLES))
#
# # Balance variables
# MAX_BAL_PER_COIN = vars.MAX_BAL_PER_COIN  # Maximum percentage of balance to use per asset/coin
# exchange.load_markets(SYMBOL)
#
# MIN_COST = exchange.load_markets(C_SYMBOL)[C_SYMBOL]['limits']['cost']['min']
# MIN_AMOUNT = exchange.load_markets(C_SYMBOL)[C_SYMBOL]['limits']['amount']['min']
# LVRG = vars.LVRG
#
# # Take Profit Grid Options
# TPGRID_MIN_DIST = vars.TPGRID_MIN_DIST  # Percentage to use for the closest order in the TP grid
# TPGRID_MAX_DIST = vars.TPGRID_MAX_DIST  # Percentage to use for the farthest order in the TP grid
# TP_ORDERS = vars.TP_ORDERS  # Number of orders for the TP grid
# DCA_FACTOR_MULT = vars.DCA_FACTOR_MULT
# ASSYMMETRIC_TP = vars.ASSYMMETRIC_TP  # False for equal sized orders, False for descending size TP orders
# MIN_LEVEL_DISTANCE = vars.MIN_LEVEL_DISTANCE