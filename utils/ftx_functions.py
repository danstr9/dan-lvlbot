import pandas as pd
from source_platform.ftx_exchange import exchange, client
import vars
import time
from datetime import *
import numpy as np
from .common_functions import *


def sanitize_candles_df(candles):
    return candles.rename(columns={'Opened': 'Date'})


def get_balance():
    balance = exchange.fetchBalance()
    usdt_balance = balance['USDT']['total'] if 'USDT' in balance else 0
    usd_balance = balance['USD']['total'] if 'USD' in balance else 0
    ACCOUNT_BALANCE = float(usdt_balance + usd_balance)

    free_balance = exchange.fetch_free_balance()
    usdt__free_balance = free_balance['USDT'] if 'USDT' in free_balance else 0
    usd__free_balance = free_balance['USD'] if 'USD' in free_balance else 0
    BAL_AVL = float(usdt__free_balance + usd__free_balance)

    print("Account balance: {} \nAvailable Balance: {}".format(ACCOUNT_BALANCE, BAL_AVL))
    return (BAL_AVL * vars.LVRG, ACCOUNT_BALANCE * vars.LVRG)


def get_data(pair, num=vars.NUM_CANDLES, tfnum=vars.TF_NUM):
    candles = get_ftx_candles(pair, tfnum, limit=num)
    candles = sanitize_candles_df(candles)
    candles = get_trend_data(candles)
    return candles


def get_current_positions(symbol):
    '''
    Function that returns a simple list of current positions
    param 'symbol': the symbol
    returns a DataFrame with the current positions and the main fields (simplified version)
    '''

    try:
        positions = pd.DataFrame(exchange.fetch_positions(symbols=symbol, params={'showAvgPrice': True}))
        positions = positions[(positions['side'] != 'None') & (positions['symbol'] == symbol)]
        positions['entryPrice'] = positions['info'].apply(lambda x: x['recentAverageOpenPrice']).astype(float)
    except Exception as e:
        print(e)
        print("Failed to get current positions.")

    if not positions.empty:
        if positions.iloc[0]['contracts'] != 0:
            return pd.DataFrame(
                positions[['symbol', 'entryPrice', 'contracts', 'side', 'liquidationPrice', 'unrealizedPnl']])
    return pd.DataFrame()


def remove_orders(orders):
    '''
        Function that deletes all the open orders passed as a parameter
        param: 'orders': a DataFrame containing the open orders to remove
        returns True if successful, False otherwise
        '''
    print("\nReduceOnly Orders found:")
    print(orders)
    for order in orders:
        try:
            print("Removing order id {}".format(order['id']))
            exchange.cancel_order(order['id'])
        except Exception as e:
            print(e)
            return False
    return True


def position_covered(position, tp_orders):
    pos = position

    if tp_orders:
        cur_pos = float(pos.iloc[0]['contracts'])
        cur_tp_size = sum([x['remaining'] for x in tp_orders])
        return cur_pos == cur_tp_size
    else:
        return False


def get_open_orders(pair):
    return exchange.fetch_open_orders(symbol=pair)


def check_tp_grid(pair, position, open_orders):
    tp_orders = [x for x in open_orders if x['info']['reduceOnly']]

    # if there is an open position but the amount is no fully covoer by tp_grid we remove
    # all tp_orders and replace them
    if not position.empty and not position_covered(position, tp_orders):
        remove_orders(tp_orders)
        place_tp_orders(pair, position)
    else:
        print("TP orders match position. Nothing to do.")

    return tp_orders
