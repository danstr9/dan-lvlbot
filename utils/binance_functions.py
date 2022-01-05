from datetime import *
from source_platform.binance_exchange import exchange, client
import vars
import pandas as pd
import numpy as np


def sanitize_candles_df(candles):
    candles.reset_index(inplace=True)
    candles = candles.drop(
        candles[candles['Opened'] == 'Opened'].index)  # Removing entries containig the titles (error from CSV)
    candles['TimeStamp'] = candles['Opened'].apply(
        iso_to_tstamp)  # lambda x: datetime.fromisoformat(str(x)).timestamp()*1000)
    candles = candles.drop_duplicates().reset_index(drop=True)
    return candles.rename(columns={'Opened': 'Date'})


def iso_to_tstamp(isodate):
    date = str(isodate)
    return datetime.fromisoformat(date).timestamp() * 1000


def get_balance():
    BAL_AVL = exchange.fetch_free_balance()['USDT']
    ACCOUNT_BALANCE = float(exchange.fetchBalance()['info']['assets'][1]['walletBalance'])

    print("Account balance: {} \nAvailable Balance: {}".format(ACCOUNT_BALANCE, BAL_AVL))
    return (BAL_AVL * vars.LVRG, ACCOUNT_BALANCE * vars.LVRG)


def calculate_min_amount():
    # TODO dunno how it works on binance
    # global MIN_AMOUNT
    # min_entry = MIN_AMOUNT
    # if not BINANCE:
    #     return float(exchange.amount_to_precision(C_SYMBOL, MIN_AMOUNT))
    # current_price = float(exchange.fetch_ticker(C_SYMBOL)['close'])
    # if min_entry * current_price >= MIN_COST:
    #     return float(exchange.amount_to_precision(C_SYMBOL, MIN_AMOUNT))
    # else:
    #     while min_entry * current_price < MIN_COST:
    #         min_entry += MIN_AMOUNT
    #     return float(exchange.amount_to_precision(C_SYMBOL, min_entry))
    return 0


def get_data(client, symbol, tf, daysago, num, tfnum):
    # TODO dunno how it works on binance
    # candles = get_binance_candles(client, symbol, tf, daysago)
    # return candles
    return 0


def get_binance_candles(client, market, timeframe, daysago=30, candlesago=0, numcandles=None):
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
    # TODO dunno how it works on binance

    # FOR DEBUGGING PURPOSES UNCOMMENT THE FOLLOWING LINE:
    # data_file = str('~/Documents/MegaCloud/Python/TRD/lvlbot/historical_price_data/' + timeframe + '_data/' + SYMBOL + '/' + SYMBOL + '.csv')
    # data_file = str('./historical_price_data/' + timeframe + '_data/' + SYMBOL + '/' + SYMBOL + '.csv')
    # today = datetime.utcnow().strftime('%m/%d/%Y')
    #
    # if candlesago == 0:
    #     initdate = datetime.utcnow() - timedelta(days=daysago)
    # else:
    #     numcandles = candlesago
    #     if 'm' in timeframe:
    #         t = int(timeframe.split('m')[0])
    #         minsago = candlesago * t
    #     elif 'h' in timeframe:
    #         t = int(timeframe.split('h')[0])
    #         minsago = candlesago * t * 60
    #     initdate = datetime.utcnow() - timedelta(minutes=minsago)
    #
    # start_date = initdate.strftime('%m/%d/%Y')
    # wait_animation.start()
    # try:
    #     store_data = client.kline_data([SYMBOL], timeframe, start_date=start_date, end_date=today)
    # except Exception as e:
    #     print(e)
    # wait_animation.stop()
    # # print("Data file: {}".format(data_file))
    # return pd.read_csv(data_file).iloc[-numcandles:]


def get_current_positions(symbol):
    '''
    Function that returns a simple list of current positions
    param 'symbol': the symbol
    returns a DataFrame with the current positions and the main fields (simplified version)
    '''
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
            return pd.DataFrame(positions[['symbol', 'timestamp', 'entryPrice', 'contracts', 'side', 'liquidationPrice',
                                           'unrealizedPnl']])

    return pd.DataFrame()


def remove_orders(orders, symbol):
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
            exchange.cancel_order(id, symbol=symbol)
        except Exception as e:
            print(e)
            return False
    return True


def position_covered(pos=get_current_positions()):
    # TODO can't test binance
    # global SYMBOL
    # tpord = get_tp_orders()
    # pos = get_current_positions()
    # # if BINANCE:
    # #     SYMBOL=C_SYMBOL
    # if not tpord.empty:
    #     cur_pos = float(pos.iloc[0]['contracts'])
    #     cur_tp_size = float(exchange.amount_to_precision(C_SYMBOL, tpord['remaining'].sum()))
    #     # print("Position: {} - TP orders sum: {}".format(cur_pos, cur_tp_size))
    #     return (cur_pos == cur_tp_size)
    #     # return float(exchange.amount_to_precision(SYMBOL, float(pos.iloc[0]['contracts']))) == float(exchange.amount_to_precision(SYMBOL, tpord['remaining'].sum()))
    # else:
    #     return False

    return 0


def get_orders(symbol):
    # global SYMBOL
    # if BINANCE:
    #     SYMBOL=C_SYMBOL
    oo = pd.DataFrame(exchange.fetch_open_orders(symbol=symbol))

    if not oo.empty:
        oo['reduceOnly'] = oo['side'] == 'sell'
        return oo[['id', 'side', 'reduceOnly', 'remaining', 'price']]
    else:
        return oo

# def add_tp_grid(pos=get_current_positions(SYMBOL)):
#     # global SYMBOL
#     if not get_tp_orders().empty:
#         if not position_covered(pos):
#             remove_orders(get_tp_orders())
#         else:
#             print("TP orders match position. Nothing to do.")
#             return 0
#
#     # if BINANCE:
#     #     SYMBOL=C_SYMBOL
#     tp_dist = (TPGRID_MAX_DIST - TPGRID_MIN_DIST) / (TP_ORDERS)
#     next_tp_pos = float(exchange.price_to_precision(SYMBOL, pos.iloc[0]['entryPrice'] * (1 + TPGRID_MIN_DIST / 100)))
#     tp_size = init_size = float(exchange.amount_to_precision(C_SYMBOL, pos.iloc[0]['contracts'].sum()))
#     sum_tps = 0
#     tp_orders = []
#     print("init size: {}; tp_size: {}, tp_dist: {}".format(next_tp_pos, tp_size, tp_dist))
#
#     for n in range(TP_ORDERS):
#         if n < (TP_ORDERS - 1):
#             if ASSYMMETRIC_TP:
#                 tp_size = float(exchange.amount_to_precision(C_SYMBOL, tp_size / 2))
#             else:
#                 tp_size = float(exchange.amount_to_precision(C_SYMBOL, init_size / TP_ORDERS))
#         else:
#             tp_size = float(exchange.amount_to_precision(C_SYMBOL, init_size))  # - sum_tps))
#         sum_tps += tp_size
#
#         params = {'positionSide': pos.iloc[0]['side'].upper()}
#
#         if n != 0:
#             next_tp_pos = float(exchange.price_to_precision(C_SYMBOL, (next_tp_pos * (1 + tp_dist / 100))))
#         o = new_order(C_SYMBOL, 'sell', tp_size, next_tp_pos, params=params)
#         if o:
#             tp_orders.append(o)
#
#     return tp_orders
