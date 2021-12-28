######### Required libraries ##########
# pip install binance-data
# pip install websocket
# pip install pandas
# pip install numpy
# pip install ccxt==1.58.55
# pip install schedule
# pip install animation
# pip install mplfinance

# Importing libraries
from datetime import *
import pandas as pd
import numpy as np
import config
import vars
import ccxt
import time
from binance_data import DataClient
import animation
import mplfinance as mplf

# For FtxClient ----------------------------------------
import urllib.parse
from typing import Optional, Dict, Any, List
from requests import Request, Session, Response
import hmac
# ------------------------------------------------------

######################## GLOBAL VARIABLES #########################
BINANCE = vars.BINANCE # Variable to indicate which exchange to use: True for BINANCE, False for FTX
SHITCOIN = vars.SHITCOIN
MULTI_TF = vars.MULTI_TF
TF_LIST = vars.TF_LIST
TF = vars.TF
DAYS_BACK = vars.DAYS_BACK # Number of days to look back in time for initial candles data
TRADE_ON = vars.TRADE_ON
LEVELS_PER_TF = vars.LEVELS_PER_TF
###################################################################

LEVEL_COLUMNS = ['side','price','hit','time']
LEVELS = pd.DataFrame(columns=LEVEL_COLUMNS)
UNHIT_LEVELS = LEVELS

# Candles calculation
if 'm' in TF:
    TF_NUM = int(TF.split('m')[0]) # Used for FTX candles
    NUM_CANDLES = int(DAYS_BACK * 24 * 60 / TF_NUM)
elif 'h' in TF:
    TF_NUM = int(TF.split('h')[0]) * 60
    NUM_CANDLES = int(DAYS_BACK * 24 * 60 / TF_NUM)

# clock animation (white, default speed)
clock = ['-','\\','|','/']
wait_animation = animation.Wait(clock, speed=8)

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

#### EXCHANGE SPECIFICS
if BINANCE: # BINANCE CONNECTION TO USD-M FUTURES
    exchange = ccxt.binanceusdm({
        'enableRateLimit': True,
        "apiKey": config.CCXT_API_KEY,
        "secret": config.CCXT_API_SECRET
    })
    futures = True
    client = DataClient(futures=futures)
    SYMBOL = SHITCOIN.upper()+'USDT'
    C_SYMBOL = SHITCOIN.upper()+'/USDT'
    print("Exchange: BINANCE - {}".format(TF))
else: # FTX CONNECTION
    SYMBOL = SHITCOIN.upper()+'-PERP'
    C_SYMBOL = SYMBOL
    exchange = ccxt.ftx({
    "apiKey": config.FTX_SAV_API_KEY,
    "secret": config.FTX_SAV_API_SECRET,
    'enableRateLimit': True,
    'headers': {'FTX-SUBACCOUNT': config.FTX_SAV_SUBACCOUNT}
    })
    client = FtxClient(api_key=config.FTX_SAV_API_KEY, api_secret=config.FTX_SAV_API_SECRET)
    print("Exchange: FTX - {}".format(TF))
    
print("SYMBOL: {}".format(SYMBOL))    
if not MULTI_TF:
    print("Days back: {} \nNum. Candles: {}".format(DAYS_BACK, NUM_CANDLES))

# Balance variables
MAX_BAL_PER_COIN = vars.MAX_BAL_PER_COIN # Maximum percentage of balance to use per asset/coin
exchange.load_markets(SYMBOL)

MIN_COST = exchange.load_markets(C_SYMBOL)[C_SYMBOL]['limits']['cost']['min']
MIN_AMOUNT = exchange.load_markets(C_SYMBOL)[C_SYMBOL]['limits']['amount']['min']
LVRG = vars.LVRG


# Take Profit Grid Options
TPGRID_MIN_DIST = vars.TPGRID_MIN_DIST # Percentage to use for the closest order in the TP grid
TPGRID_MAX_DIST = vars.TPGRID_MAX_DIST  # Percentage to use for the farthest order in the TP grid
TP_ORDERS = vars.TP_ORDERS # Number of orders for the TP grid
DCA_FACTOR_MULT = vars.DCA_FACTOR_MULT
ASSYMMETRIC_TP = vars.ASSYMMETRIC_TP # False for equal sized orders, False for descending size TP orders 
MIN_LEVEL_DISTANCE = vars.MIN_LEVEL_DISTANCE

# FUNCTIONS START HERE

def get_ftx_candles(market, interval, limit=5000, start_time=None, end_time=None):
    '''
    Function that returns a dataframe with the candles information
    param 'market': the market to get the candle data from
    param 'interval': the interval of the candle data
    param 'limit': the number of candles to retrieve (maximum 5000)
    param 'start_time': the start time (aka the time of the first candle to get) in timestamp format
    param 'end_time': the end time (aka the time of the last candle to get) in timestamp format, if it results in over the limit number, it won't be used
    returns: a DataFrame with the candles data
    '''
    
    # make sure limtit is below 5000 
    if limit > 5000:
        print(f'Max klines is 5000 per request. Getting 5000 klines instead of {limit}.')
        limit = 5000 

    for _ in range(10): 
        try:
            temp_dict = client.get_klines(market_name=market, resolution=int(interval*60), limit=limit, start_time=start_time, end_time=end_time)
            # print(temp_dict)
        except Exception as e: 
            print(e)
            print("Failed to get historical kline. Retrying....")
            time.sleep(2)
        else: 
            if len(temp_dict) > 0:  
                break  
            else: 
                time.sleep(1)
    else: # when all the retries failed
        print("(get_historical_klines_simple) Failed 10 times to get historical kline data.")
        # If you like, terminate the program (or report this to Discord/LINE/whatever)
        #sys.exit(0)

    # convert to data frame 
    df = pd.DataFrame.from_dict(temp_dict)
    df.columns = ['Date', 'TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    # change OHLCV data types from 'object' to 'float'
    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype('float64')
    # df['Date JST'] = [datetime.fromtimestamp(i/1000, jst).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in df['TimeStamp']] # use JST to convert time
    # change df column order to OHLCV
    return df[['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Date']]

def get_binance_candles(client, market, timeframe=TF, daysago=30, candlesago=0, numcandles=NUM_CANDLES):
    '''
    Function that returns a dataframe with the candles information
    param 'client': the client connection object for binance
    param 'market: the market where the candle data will be retrieved
    param 'interval: the interval selected
    param 'daysago': the number of days ago to look for candles, default is 30 for one month ago data
    param 'candlesago': the number of candles to look back (if used it will have preference over daysago)
    param 'numcandles': the number of candles to return in the dataframe
    returns: a dataframe with the candle data
    '''

    # data_file = str('~/Documents/MegaCloud/Python/TRD/lvlbot/historical_price_data/' + timeframe + '_data/' + SYMBOL + '/' + SYMBOL + '.csv')
    data_file = str('./historical_price_data/' + timeframe + '_data/' + SYMBOL + '/' + SYMBOL + '.csv')
    today = datetime.utcnow().strftime('%m/%d/%Y')

    if candlesago == 0:
        initdate = datetime.utcnow() - timedelta(days=daysago)
    else:
        numcandles = candlesago
        if 'm' in timeframe:
            t = int(timeframe.split('m')[0])
            minsago = candlesago * t
        elif 'h' in timeframe:
            t = int(timeframe.split('h')[0])
            minsago = candlesago * t * 60
        initdate = datetime.utcnow() - timedelta(minutes=minsago)

    start_date = initdate.strftime('%m/%d/%Y')
    wait_animation.start()
    try:
        store_data = client.kline_data([SYMBOL], timeframe, start_date=start_date, end_date=today)
    except Exception as e:
        print(e)
    wait_animation.stop()
    # print("Data file: {}".format(data_file))
    return pd.read_csv(data_file).iloc[-numcandles:]  

def iso_to_tstamp(isodate):
    date = str(isodate)
    return datetime.fromisoformat(date).timestamp()*1000

def sanitize_candles_df(candles):
    if BINANCE:
        candles.reset_index(inplace=True)
        candles = candles.drop(candles[candles['Opened']=='Opened'].index) # Removing entries containig the titles (error from CSV)
        candles['TimeStamp'] = candles['Opened'].apply(iso_to_tstamp) # lambda x: datetime.fromisoformat(str(x)).timestamp()*1000)
        candles = candles.drop_duplicates().reset_index(drop=True)
    return candles.rename(columns={'Opened':'Date'})

def get_ftx_tf_num_calc(tf=TF,daysback=DAYS_BACK):
    if 'm' in tf:
        tfnum = int(tf.split('m')[0]) # Used for FTX candles
        numcandles = int(daysback * 24 * 60 / tfnum)
    elif 'h' in tf:
        tfnum = int(tf.split('h')[0]) * 60
        numcandles = int(daysback * 24 * 60 / tfnum)

    return tfnum, numcandles

def get_trend_data(last_candles):
    '''
    Function that returns a dataframe with the trend data, comparing lows and highs of the last candles passed as parameter
    param 'last_candles': The last_candles data in form of a DataFrame
    return: the last_candles dataframe including the fields of hh, ll, el, eh, lh, hl
    '''
    hh = []
    ll = []
    lh = []
    hl = []
    eh = []
    el = []
    green_candle = []

    for c in last_candles.index:
        green_candle.append(last_candles.iloc[c]['Close'] > last_candles.iloc[c]['Open'])
        if c == 0:
            hh.append(np.nan)
            ll.append(np.nan)
            hl.append(np.nan)
            lh.append(np.nan)
            eh.append(np.nan)
            el.append(np.nan)

        else:
            hh.append(last_candles.iloc[c]['High'] > last_candles.iloc[c-1]['High'])
            lh.append(last_candles.iloc[c]['High'] < last_candles.iloc[c-1]['High'])
            ll.append(last_candles.iloc[c]['Low'] < last_candles.iloc[c-1]['Low'])
            hl.append(last_candles.iloc[c]['Low'] > last_candles.iloc[c-1]['Low'])
            eh.append(last_candles.iloc[c]['High'] == last_candles.iloc[c-1]['High'])
            el.append(last_candles.iloc[c]['Low'] == last_candles.iloc[c-1]['Low'])
    
    last_candles['hh'] = hh
    last_candles['ll'] = ll
    last_candles['lh'] = lh
    last_candles['hl'] = hl
    last_candles['eh'] = eh
    last_candles['el'] = el
    last_candles['green_candle'] = green_candle
    
    return last_candles

def is_u_shape(three_candles):
    '''
    Function that determines if three candles are forming a u-shape and returns True if they are or False if they don't
    param 'three_candles': a dataframe containing three candle data.
    Returns a boolean indicating whether the u-shape is present or not.
    '''
    return (three_candles.iloc[1]['ll'] & three_candles.iloc[2]['hl'])

def is_inverse_u_shape(three_candles):
    '''
    Function that determines if three candles are forming an inverse u-shape and returns True if they are or False if they don't
    param 'three_candles': a dataframe containing three candle data.
    Returns a boolean indicating whether the inverse u-shape is present or not.
    '''
    return (three_candles.iloc[1]['hh'] & three_candles.iloc[2]['lh'])

def level_finder(candles):
    '''
    Function that will make the necessary calls to other functions to determine if a level has been found.
    param 'candles': the last candles data in a dataframe format (it requires at least 5 candles to determine if a level has been found)
    Returns a list with the level details (side, value, hit) if the level was found, or 0 if no level was found
    '''
    if candles.shape[0] < 5 or candles.shape[0] > 5:
        # print("Sorry, number of candles provided to find levels doesn't fit the required amount (5). Passed candles: {}".format(candles.index.size))
        # print(candles)
        return 0

    else:
        
        first_3_candles = candles[0:3]
        # Find U-shape or Inverse-U-shape in the first 3 candles
        u_shape = is_u_shape(first_3_candles)
        inv_u_shape = is_inverse_u_shape(first_3_candles)

        # If any of them is found, compare the corresponding high or low to determine if a level was found
        if u_shape and (candles.iloc[4]['Low'] > candles.iloc[1]['High']): # and not SHORT_ONLY_MODE: # BUY LEVEL FOUND HERE
            return (['buy', candles.iloc[1]['High'], False, datetime.fromtimestamp(candles.iloc[1]['TimeStamp']/1000).isoformat()])
        if inv_u_shape and (candles.iloc[4]['High'] < candles.iloc[1]['Low']): # and not LONG_ONLY_MODE: # SELL LEVEL FOUND
            return (['sell', candles.iloc[1]['Low'], False, datetime.fromtimestamp(candles.iloc[1]['TimeStamp']/1000).isoformat()])
        
        return 0

def check_level_hits(levels, candles):
    '''
    Function that checks if the levels stored in the levels DF passed, are hit or not.
    param 'levels': a DataFrame containing the levels found 
    param 'candles': a DataFrame containing the whole list of candles where the levels were found
    returns the levels DataFrame updated with the levels marked as hit or not.
    '''  
    levels.reset_index(inplace=True, drop=True)
    # print(levels)
    # print(candles)
    for l in levels.index:
        start_time = datetime.fromisoformat(levels.iloc[l]['time']).timestamp()*1000
        valid_candles = candles[candles['TimeStamp'] > start_time]
        valid_candles.reset_index(inplace=True, drop=True)
        if levels.iloc[l]['side'] == 'buy':
            for i in valid_candles.index:
                if i>3 and valid_candles.iloc[i]['Low'] <= levels.iloc[l]['price']:
                    levels.loc[l, 'hit'] = True
                    break
        else:
            for i in valid_candles.index:
                if i>3 and valid_candles.iloc[i]['High'] >= levels.iloc[l]['price']:
                    levels.loc[l, 'hit'] = True
                    break
    
    return levels

def get_levels(candles, n):
    '''
    Function that returns the levels found in the N candles of whatever SYMBOL is passed, on the TF passed as well.
    param 'candles': The dataframe with all the candles information where to look for levels
    param 'levels': The dataframe to store all the levels found
    param 'n': The number of candles to look for levels into.
    Returns a list of the levels found in the candles.
    '''

    levels = pd.DataFrame(columns=LEVEL_COLUMNS)

    if n < candles.shape[0]:
        n = candles.shape[0]

    print('Processing candles...')
    wait_animation.start()
    for i in range(n):
        if i > 5 and i < n:
            level_found = level_finder(candles.iloc[i-5:i])
            if level_found != 0:
                levels = levels.append(pd.Series(data=level_found, index=LEVEL_COLUMNS), ignore_index=True)
    wait_animation.stop()
    print("Done.")
    return check_level_hits(levels, candles)

def dca_buy_list(levels):
    buy_levels = levels[levels['side'] == 'buy'].sort_values(by='price', ascending=False)
    return list(buy_levels['price'].astype(float))

def dca_sell_list(levels):
    sell_levels = levels[levels['side'] == 'sell'].sort_values(by='price', ascending=True)
    return list(sell_levels['price'].astype(float))

def new_order(symbol, side, amount, price, params={}):
    try:
        print("Sending order of {} at {}".format(amount, price))
        order = exchange.create_limit_order(symbol=symbol, side=side, amount=amount, price=price, params=params)
        # print(order)
        return order
    except Exception as e:
        print(e)
        return False

def buy_levels_filter(levels):
    '''
    Function that filters out levels too close to each other and returns the filtered dataframe
    '''
    levels.reset_index(drop=True, inplace=True)
    levels['price']=levels['price'].astype(float)
    print(" - - - Before filter: {}".format(levels['price']))
    ld = []
    for i in levels.index:
        if i>0:
            if levels.iloc[i]['price'] > (levels.iloc[i-1]['price'] * (1 - MIN_LEVEL_DISTANCE/100)):
                ld.append(i)  # Add the row to the list for removal
    # jump = False
    # for i in levels.index:
    #     if i>0:
    #         if not jump:
    #             if levels.iloc[i]['price'] > (levels.iloc[i-1]['price'] * (1 - MIN_LEVEL_DISTANCE/100)):
    #                 ld.append(i)
    #                 jump = True
    #             else:
    #                 jump = False
    #         else:
    #             if i > 2:
    #                 if levels.iloc[i]['price'] > (levels.iloc[i-2]['price'] * (1 - MIN_LEVEL_DISTANCE/100)):
    #                     ld.append(i)
    #                     jump = True
    #                 else:
    #                     jump = False

    levels.drop(ld, inplace=True)
    print(" - - - After filter: {}".format(levels['price']))
    return levels

def sell_levels_filter(levels):
    '''
    Function that filters out levels too close to each other and returns the filtered dataframe
    '''
    levels.reset_index(drop=True, inplace=True)
    levels['price']=levels['price'].astype(float)
    ld = []
    jump = False
    for i in levels.index:
        if i>0:
            if not jump:
                if levels.iloc[i]['price'] < (levels.iloc[i-1]['price'] * (1 + MIN_LEVEL_DISTANCE/100)):
                    ld.append(i)
                    jump = True
                else:
                    jump = False
            else:
                if i > 2:
                    if levels.iloc[i]['price'] < (levels.iloc[i-2]['price'] * (1 + MIN_LEVEL_DISTANCE/100)):
                        ld.append(i)
                        jump = True
                    else:
                        jump = False
    levels.drop(ld, inplace=True)
    return levels

def get_closest_unhit_lvls(tflist=TF_LIST):
    
    global UNHIT_LEVELS
    buy_lvdf = pd.DataFrame(columns=LEVEL_COLUMNS)
    sell_lvdf = pd.DataFrame(columns=LEVEL_COLUMNS)
    for tf in tflist:

        if tf == '1m':
            daysago = 1
        elif tf == '5m':
            daysago = 5
        elif tf == '15m':
            daysago = 10
        elif tf == '1h':
            daysago = 60
        elif tf == '4h':
            daysago = 150
        elif tf == '12h':
            daysago = 365
        elif tf == '1d':
            daysago = 720
        tfn, num = get_ftx_tf_num_calc(tf, daysago)
        print("tf: {}, tfn: {}, num: {}".format(tf, tfn, num))
 
        candles = get_data(client, SYMBOL,tf, daysago=daysago, num=num, tfnum=tfn)
        levels = get_levels(candles, num)
        unhit_levels = levels[levels['hit'] == False]
        unhit_levels = unhit_levels.drop(['time'], axis=1)

        # print(levels)
        print("-"*80)
        buy_levels = unhit_levels[unhit_levels['side'] == 'buy'].sort_values(by='price', ascending=False)
        sell_levels = unhit_levels[unhit_levels['side'] == 'sell'].sort_values(by='price', ascending=True)
        # print("buy_levels: \n{}".format(buy_levels))
        # print("sell_levels: \n{}".format(sell_levels))   
        if not buy_levels.empty:
            print("---- Closest {} BUY: {}".format(tf, list(buy_levels.iloc[0:LEVELS_PER_TF]['price'])))
            buy_lvdf = buy_lvdf.append(buy_levels.iloc[0:LEVELS_PER_TF], ignore_index=True)
            buy_lvdf['price'] = buy_lvdf['price'].astype(float)
            buy_lvdf.sort_values(by='price', ascending=False, inplace=True)
        if not sell_levels.empty:
            print("---- Closest {} SELL: {}".format(tf, list(sell_levels.iloc[0:LEVELS_PER_TF]['price'])))
            sell_lvdf = sell_lvdf.append(sell_levels.iloc[0:LEVELS_PER_TF], ignore_index=True)
            sell_lvdf['price'] = sell_lvdf['price'].astype(float)
            sell_lvdf.sort_values(by='price', ascending=True)
        print("-"*80)
        # print("levels tail: \n{}\nlevels head: {}".format(levels.tail(1), levels.head(1)))
        # print("candles tail: \n{}\ncandles head: {}".format(candles.tail(1), candles.head(1)))
        buy_lvdf = buy_lvdf.drop_duplicates()
        sell_lvdf = sell_lvdf.drop_duplicates()

    buy_lvdf = buy_levels_filter(buy_lvdf)
    sell_lvdf = sell_levels_filter(sell_lvdf)
    if TRADE_ON:
        print("Final Results: \n *** BUY LEVELS *** \n{}".format(buy_lvdf))
        run_buy_dca_grid(candles, buy_lvdf.append(sell_lvdf))
    else:
        print("Final Results: \n *** BUY LEVELS *** \n{} \n *** SELL LEVELS *** \n{}".format(buy_lvdf, sell_lvdf))
        plot_data(candles, buy_lvdf.append(sell_lvdf))

def get_balance():
    if BINANCE:
        BAL_AVL = exchange.fetch_free_balance()['USDT']
        ACCOUNT_BALANCE = float(exchange.fetchBalance()['info']['assets'][1]['walletBalance'])
    else:
        ACCOUNT_BALANCE = float(exchange.fetchBalance()['USDT']['total'] + exchange.fetchBalance()['USD']['total'])
        BAL_AVL = float(exchange.fetch_free_balance()['USDT'] + exchange.fetch_free_balance()['USD'])

    print("Account balance: {} \nAvailable Balance: {}".format(ACCOUNT_BALANCE,BAL_AVL))
    return (BAL_AVL*LVRG, ACCOUNT_BALANCE*LVRG)

def max_dca_grid_size():
    return float(exchange.fetchBalance()['USDT']['total']) * MAX_BAL_PER_COIN / 100

def calculate_min_amount():
    global MIN_AMOUNT, SYMBOL
    min_entry = MIN_AMOUNT
    if BINANCE:
        SYMBOL=C_SYMBOL
    else:
        return float(exchange.amount_to_precision(SYMBOL, MIN_AMOUNT))
    current_price = float(exchange.fetch_ticker(SYMBOL)['close'])
    if min_entry * current_price >= MIN_COST:
        return float(exchange.amount_to_precision(SYMBOL, MIN_AMOUNT))
    else:
        while min_entry * current_price < MIN_COST:
            min_entry += MIN_AMOUNT
        return float(exchange.amount_to_precision(SYMBOL, min_entry))

def find_max_possible_entry(bal, factor, price_list):
    '''
    Function to find the maximum possible entry, by testing from the minimum entry size, increasing it sequentially
    until it gets to the value that fits within the maximum allowed balance per asset.
    '''
    MIN_AMOUNT = calculate_min_amount()
    max_entry = 0
    sum_positions = 0
    while sum_positions < bal:
        max_entry = max_entry + MIN_AMOUNT
        sum_positions = calc_max_position(max_entry, factor, price_list)
    return max_entry
    
def calc_max_position(entry, factor, price_list):
    pos = 0
    for n in range(len(price_list)):
        if n == 0:
            pos = entry * price_list[n]
        else:
            pos = pos + (price_list[n] * (entry * (factor ** n)))
    return pos

def entry_size(levels, long=True):
    avl_bal, acc_bal = get_balance()
    max_bpc = avl_bal * MAX_BAL_PER_COIN / 100
    MIN_AMOUNT = calculate_min_amount()
    print("Max allocation per asset: {}".format(max_bpc))
    print("Minimum entry size: {}".format(MIN_AMOUNT))
    
    buy_levels = levels[levels['side'] == 'buy'].sort_values(by='price', ascending=False)
    sell_levels = levels[levels['side'] == 'sell'].sort_values(by='price', ascending=True)

    if long:
        def_list = list(buy_levels['price'].astype(float))
    else:
        def_list = list(sell_levels['price'].astype(float))

    while len(def_list) > 0:
        min_entry_total_size = calc_max_position(MIN_AMOUNT, DCA_FACTOR_MULT, def_list)
        
        if min_entry_total_size < max_bpc: # Check if we cover the whole available balance with the minimum entry size
            entry = find_max_possible_entry(max_bpc, DCA_FACTOR_MULT, def_list)
            return entry, def_list
        elif min_entry_total_size == max_bpc:
            return min_entry_total_size, def_list
        else:
            def_list.pop()
            if len(def_list) == 0:
                print("Not enough balance.")
                return 0, 0
    return 0, 0

def get_data(client=client, symbol=SYMBOL, tf=TF, daysago=DAYS_BACK, num=NUM_CANDLES, tfnum=TF_NUM):

    if BINANCE:
        candles = get_binance_candles(client, symbol, tf, daysago)    
    else:
        candles = get_ftx_candles(symbol, tfnum, limit=NUM_CANDLES)
    candles = sanitize_candles_df(candles)
    candles = get_trend_data(candles)
    return candles

def plot_data(candles, unhit_levels):
    # Plotting stuff
    candles['Date'] = pd.to_datetime(candles['Date'])
    candles.set_index('Date', drop=True, inplace=True)
    colors = []
    for i in unhit_levels.index:
        if unhit_levels.iloc[i]['side'] == 'buy':
            colors.append('b')
        else:
            colors.append('r')
    mplf.plot(candles,type='candlestick', style='yahoo', title=SYMBOL + " " + str(DAYS_BACK) + " days chart levels on " + TF,
              hlines=dict(hlines=list(unhit_levels['price']), linestyle='-', colors=colors, linewidths=(0.5, 0.5)), volume=True)

def get_report(candles):
    global LEVELS, UNHIT_LEVELS
    LEVELS = get_levels(candles, n=NUM_CANDLES)

    print("TOTAL LEVELS FOUND: {}".format(LEVELS.shape[0]))

    UNHIT_LEVELS = LEVELS[LEVELS['hit']==False]
    UNHIT_LEVELS.reset_index(inplace=True)
    # BUY_LEVELS = UNHIT_LEVELS[UNHIT_LEVELS['side']=='buy']
    # BUY_LEVELS.reset_index(inplace=True)
    # SELL_LEVELS = UNHIT_LEVELS[UNHIT_LEVELS['side']=='sell']
    # SELL_LEVELS.reset_index(inplace=True)
    blist = dca_buy_list(UNHIT_LEVELS)
    slist = dca_sell_list(UNHIT_LEVELS)
    
    print("UNHIT LEVELS: \n{}".format(UNHIT_LEVELS))
    # print("UNHIT BUYS: {}\nUNHIT SELLS: {}".format(UNHIT_LEVELS[UNHIT_LEVELS['side']=='buy'].shape[0], UNHIT_LEVELS[UNHIT_LEVELS['side']=='sell'].shape[0]))
    print("DCA long list: {} \nDCA short list: {}".format(blist, slist))
    if len(blist) != 0:
        entry, buy_list = entry_size(UNHIT_LEVELS)
        print ("Optimum entry size: {} \nDCA levels: {}".format(entry, len(buy_list)))
    else:
        print("No buy/long DCA levels found. Won't calculate any entry")
    

    # plot_data(candles, UNHIT_LEVELS)

def dca_entries(entry, levels):
    entries = []
    for l in range(len(levels)):
        entries.append(entry * (1.7 ** l))
    return entries

def get_current_positions(symbol=SYMBOL):
    '''
    Function that returns a simple list of current positions
    param 'symbol': the symbol
    returns a DataFrame with the current positions and the main fields (simplified version)
    '''
    global SYMBOL
    if BINANCE:
        symbol = C_SYMBOL
        try:
            positions = pd.DataFrame(exchange.fetch_positions(symbols=symbol))
            # time.sleep(1)
        except Exception as e:
            print(e)
            print("Failed to get current positions.")
            return pd.DataFrame()
        if positions.bool:
            if not positions.empty:
                positions = positions[positions['entryPrice'].notnull()]
                positions = positions[positions['symbol'] == symbol]
                positions = positions.astype({'entryPrice': np.float64})
                return pd.DataFrame(positions[['symbol', 'timestamp', 'entryPrice', 'contracts', 'side', 'liquidationPrice', 'unrealizedPnl']])
    else:
        try:
            positions = pd.DataFrame(exchange.fetch_positions(symbols=symbol, params={'showAvgPrice': True}))
        except Exception as e:
            print(e)
            print("Failed to get current positions.")
        if positions.bool:
            if not positions.empty:
                positions = positions[(positions['side']!= 'None') & (positions['symbol'] == symbol)]
                positions['entryPrice'] = positions['info'].apply(lambda x : x['recentAverageOpenPrice']).astype(float)
                return pd.DataFrame(positions[['symbol', 'entryPrice', 'contracts', 'side', 'liquidationPrice', 'unrealizedPnl']])
    return pd.DataFrame()

def get_position_notional():
    return float(get_current_positions()['notional'])

def scheduler():
    if get_current_positions().empty and MULTI_TF:
        if not get_dca_orders().empty:
            if current_dca_grid_size() < (max_dca_grid_size() * 0.95):
                get_closest_unhit_lvls()
            else:
                get_closest_unhit_lvls(['1m','5m','15m'])
        else:
            get_closest_unhit_lvls()
    while True:
        if time.localtime().tm_sec % 5 == 0: # Get things done every 5 seconds
            try:
                check_tp_routine()
            except Exception as e:
                print(e)

        if get_current_positions().empty:
            if time.localtime().tm_sec % 5 == 0 and time.localtime().tm_min % 5 == 0:
                if MULTI_TF:
                    if not get_dca_orders().empty:
                        if current_dca_grid_size() < (max_dca_grid_size() * 0.95):
                            get_closest_unhit_lvls()
                        else:
                            get_closest_unhit_lvls(['1m','5m','15m'])
                    else:
                        get_closest_unhit_lvls()
                else:
                    run_buy_dca_grid(get_data())
        time.sleep(1)

def check_tp_routine():
    pos=get_current_positions()
    if not pos.empty:
        # print("In position. Position details: \n{}".format(pos))
        now = datetime.now()
        cov_pos = position_covered(pos)
        if (not cov_pos):
            add_tp_grid(pos)
        else:
            sz = current_dca_grid_size()
            print("[{}.{}] - {} {} p: {} @ {} DCA sz: {} (n:{}) / pnl: {} liq: {}".format(
                now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%f")[0:3], pos.iloc[0]['symbol'], 
                pos.iloc[0]['side'], pos.iloc[0]['contracts'], pos.iloc[0]['entryPrice'], round(sz,3), 
                round(sz*LVRG,3), round(pos.iloc[0]['unrealizedPnl'],4), pos.iloc[0]['liquidationPrice'])
                )
    else:
        print("[{}] - No position. DCA grid size: {}".format(datetime.now().isoformat().replace('T',' '), round(current_dca_grid_size(),4)))
    return pos
       
def remove_orders(orders):
    '''
    Function that deletes all the open orders passed as a parameter
    param: 'orders': a DataFrame containing the open orders to remove
    returns True if successful, False otherwise
    '''
    print("\nReduceOnly Orders found:")
    print(orders)
    for id in orders['id']:
        try:
            print("Removing order id {}".format(id))
            if BINANCE:
                exchange.cancel_order(id,symbol=C_SYMBOL)
            else:
                exchange.cancel_order(id)
        except Exception as e:
            print(e)
            return False
    return True

def position_covered(pos=get_current_positions()):
    global SYMBOL
    tpord = get_tp_orders()
    pos = get_current_positions()
    if BINANCE:
        SYMBOL=C_SYMBOL
    if not tpord.empty:
        cur_pos = float(pos.iloc[0]['contracts'])
        cur_tp_size = float(exchange.amount_to_precision(SYMBOL, tpord['remaining'].sum()))
        # print("Position: {} - TP orders sum: {}".format(cur_pos, cur_tp_size))
        return (cur_pos == cur_tp_size)
        # return float(exchange.amount_to_precision(SYMBOL, float(pos.iloc[0]['contracts']))) == float(exchange.amount_to_precision(SYMBOL, tpord['remaining'].sum()))
    else:
        return False

def get_orders():
    global SYMBOL
    if BINANCE:
        SYMBOL=C_SYMBOL
    oo = pd.DataFrame(exchange.fetch_open_orders(symbol=SYMBOL))

    if not oo.empty:
        if BINANCE:
            oo['reduceOnly'] = oo['side']=='sell'
        else:
            oo['reduceOnly'] = oo['info'].apply(lambda x: x.get('reduceOnly'))
        return oo[['id','side','reduceOnly','remaining','price']]
    else:
        return oo

def get_tp_orders():
    tpo = get_orders()
    if tpo.empty:
        return tpo
    else:
        return tpo[tpo['reduceOnly']==True]

def get_dca_orders():
    dcas = get_orders()
    if dcas.empty:
        return dcas
    else:
        return dcas[dcas['reduceOnly']==False]

def current_dca_grid_notional(): # Returns the balance used by DCAs considering leverage
    return current_dca_grid_size() * LVRG

def current_dca_grid_size(): # returns the balance used by DCAs without considering leverage
    total = 0.0
    dcas = get_dca_orders()
    for e in dcas.index:
        total += dcas.iloc[e]['remaining'] * dcas.iloc[e]['price'] / LVRG
    # print("Current grid size: {}".format(total))
    return total

def run_buy_dca_grid(candles, unhit_levels=pd.DataFrame):
    global LEVELS, UNHIT_LEVELS, SYMBOL
    if unhit_levels.empty:
        LEVELS = get_levels(candles, n=NUM_CANDLES)

        UNHIT_LEVELS = LEVELS[LEVELS['hit']==False]
        UNHIT_LEVELS.reset_index(inplace=True)
        entry, dca_list = entry_size(UNHIT_LEVELS, long=True)
    else:
        entry, dca_list = entry_size(unhit_levels, long=True)

    if dca_list:

        dca_orders = get_dca_orders()
        if not dca_orders.empty:
            remove_orders(dca_orders)

        e_prices = dca_entries(entry, dca_list)
        if BINANCE:
            SYMBOL=C_SYMBOL
        for i in range(len(dca_list)):
            new_order(SYMBOL, 'buy', e_prices[i], dca_list[i], params={'positionSide': 'LONG'})
        
    else:
        print("No buy levels found. Nothing to do.")

def add_tp_grid(pos = get_current_positions(SYMBOL)):
    global SYMBOL
    if not get_tp_orders().empty:
        if not position_covered(pos):
            remove_orders(get_tp_orders())
        else:
            print("TP orders match position. Nothing to do.")
            return 0

    if BINANCE:
        SYMBOL=C_SYMBOL
    tp_dist = (TPGRID_MAX_DIST - TPGRID_MIN_DIST) / (TP_ORDERS)
    next_tp_pos = float(exchange.price_to_precision(SYMBOL, pos.iloc[0]['entryPrice'] * (1 + TPGRID_MIN_DIST/100)))
    tp_size = init_size = float(exchange.amount_to_precision(SYMBOL, pos.iloc[0]['contracts'].sum()))
    sum_tps = 0
    tp_orders = []
    print("init size: {}; tp_size: {}, tp_dist: {}".format(next_tp_pos, tp_size, tp_dist))

    for n in range(TP_ORDERS):
        if n < (TP_ORDERS-1):
            if ASSYMMETRIC_TP:        
                tp_size = float(exchange.amount_to_precision(SYMBOL, tp_size/2))   
            else:
                tp_size = float(exchange.amount_to_precision(SYMBOL, init_size / TP_ORDERS))
        else:
            tp_size = float(exchange.amount_to_precision(SYMBOL, init_size )) # - sum_tps))
        sum_tps += tp_size

        if BINANCE:
            params = {'positionSide': pos.iloc[0]['side'].upper()}
        else:
            params = {'positionSide': pos.iloc[0]['side'].upper(), 'reduceOnly':True}

        if n!=0:
            next_tp_pos = float(exchange.price_to_precision(SYMBOL, (next_tp_pos * (1 + tp_dist/100))))
        o = new_order(SYMBOL, 'sell', tp_size, next_tp_pos, params=params)
        if o:
            tp_orders.append(o)
        
    
    return tp_orders

# ======= MAIN ROUTINE ======== #
def main():   
    if TRADE_ON:
        scheduler()
    else:
        get_report(get_data())

if __name__ == "__main__":
    
    main()

