import pandas as pd
from source_platform.ftx_exchange import exchange, client
import vars
from datetime import *
import time
import numpy as np
import utils.ftx_functions as ftx_functions


def place_tp_orders(pair, position):
    tp_dist = (vars.TPGRID_MAX_DIST - vars.TPGRID_MIN_DIST) / vars.TP_ORDERS_NUMBER
    next_tp_pos = float(
        exchange.price_to_precision(pair, position.iloc[0]['entryPrice'] * (1 + vars.TPGRID_MIN_DIST / 100)))
    tp_size = init_size = float(exchange.amount_to_precision(pair, position.iloc[0]['contracts'].sum()))
    sum_tps = 0
    tp_orders = []
    print("init size: {}; tp_size: {}, tp_dist: {}".format(next_tp_pos, tp_size, tp_dist))

    for n in range(vars.TP_ORDERS_NUMBER):
        if n < (vars.TP_ORDERS_NUMBER - 1):
            if vars.ASSYMMETRIC_TP:
                tp_size = float(exchange.amount_to_precision(pair, tp_size / 2))
            else:
                tp_size = float(exchange.amount_to_precision(pair, init_size / vars.TP_ORDERS_NUMBER))
        else:
            tp_size = float(exchange.amount_to_precision(pair, init_size))  # - sum_tps))
        sum_tps += tp_size

        params = {'positionSide': position.iloc[0]['side'].upper(), 'reduceOnly': True}

        if n != 0:
            next_tp_pos = float(exchange.price_to_precision(pair, (next_tp_pos * (1 + tp_dist / 100))))
        o = new_order(pair, 'sell', tp_size, next_tp_pos, params=params)
        if o:
            tp_orders.append(o)

    return tp_orders


def new_order(pair, side, amount, price, params={}):
    try:
        print("Sending order of {} at {}".format(amount, price))
        order = exchange.create_limit_order(symbol=pair, side=side, amount=amount, price=price, params=params)
        # print(order)
        return order
    except Exception as e:
        print(e)
        return False


def check_dca_orders(pair, open_orders):
    dca_orders = [x for x in open_orders if not x['info']['reduceOnly']]
    if vars.MULTI_TF:
        get_closest_unhit_lvls(pair, dca_orders)
    else:
        run_buy_dca_grid(pair, dca_orders, ftx_functions.get_data(pair))


def get_ftx_tf_num_calc(tf=vars.TF, daysback=vars.DAYS_BACK):
    if 'm' in tf:
        tfnum = int(tf.split('m')[0])  # Used for FTX candles
        numcandles = int(daysback * 24 * 60 / tfnum)
    elif 'h' in tf:
        tfnum = int(tf.split('h')[0]) * 60
        numcandles = int(daysback * 24 * 60 / tfnum)
    elif 'd' in tf:
        tfnum = int(tf.split('d')[0]) * 60 * 24
        numcandles = int(daysback * 24 * 60 / tfnum)

    return tfnum, numcandles


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
            temp_dict = client.get_klines(market_name=market, resolution=int(interval * 60), limit=limit,
                                          start_time=start_time, end_time=end_time)
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
    else:  # when all the retries failed
        print("(get_historical_klines_simple) Failed 10 times to get historical kline data.")
        # If you like, terminate the program (or report this to Discord/LINE/whatever)
        # sys.exit(0)

    # convert to data frame
    df = pd.DataFrame.from_dict(temp_dict)
    df.columns = ['Date', 'TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    # change OHLCV data types from 'object' to 'float'
    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype('float64')
    # df['Date JST'] = [datetime.fromtimestamp(i/1000, jst).strftime('%Y-%m-%d %H:%M:%S.%d')[:-3] for i in df['TimeStamp']] # use JST to convert time
    # change df column order to OHLCV
    return df[['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Date']]


def get_closest_unhit_lvls(pair, dca_orders, tflist=vars.TF_LIST):
    buy_lvdf = pd.DataFrame(columns=vars.LEVEL_COLUMNS)
    sell_lvdf = pd.DataFrame(columns=vars.LEVEL_COLUMNS)

    tflist_daysago_mapping = vars.tflist_daysago_mapping

    for tf in tflist:
        daysago = tflist_daysago_mapping[tf]

        # if tf == '1m':
        #     daysago = 1
        # elif tf == '3m':
        #     daysago = 2
        # elif tf == '5m':
        #     daysago = 5
        # elif tf == '15m':
        #     daysago = 10
        # elif tf == '1h':
        #     daysago = 60
        # elif tf == '4h':
        #     daysago = 150
        # elif tf == '12h':
        #     daysago = 365
        # elif tf == '1d':
        #     daysago = 720

        # TODO serve?
        tfn, num = get_ftx_tf_num_calc(tf, daysago)
        print("tf: {}, tfn: {}, num: {}".format(tf, tfn, num))

        candles = ftx_functions.get_data(pair, num, tfn)
        levels = get_levels(candles, num)

        unhit_levels = levels[levels['hit'] == False]
        # unhit_levels = levels
        unhit_levels = unhit_levels.drop(['time'], axis=1)

        # print(levels)
        print("-" * 80)
        buy_levels = unhit_levels[unhit_levels['side'] == 'buy'].sort_values(by='price', ascending=False)
        sell_levels = unhit_levels[unhit_levels['side'] == 'sell'].sort_values(by='price', ascending=True)
        # print("buy_levels: \n{}".format(buy_levels))
        # print("sell_levels: \n{}".format(sell_levels))

        buy_levels = buy_levels_filter(buy_levels)
        sell_levels = sell_levels_filter(sell_levels)

        if not buy_levels.empty:
            print("---- Closest {} {} BUY: {}".format(pair, tf, list(buy_levels.iloc[0:vars.LEVELS_PER_TF]['price'])))

            if len(buy_lvdf):
                if len(buy_lvdf) < vars.MAX_DCA_NUMBER:
                    dca_remaining = vars.MAX_DCA_NUMBER - len(buy_lvdf)
                    dca_to_add = dca_remaining if dca_remaining < vars.LEVELS_PER_TF else vars.LEVELS_PER_TF
                    buy_lvdf = buy_lvdf.append(buy_levels.loc[buy_levels['price'] < buy_lvdf['price'].iloc[-1] * ((100 - vars.MIN_LEVEL_DISTANCE) / 100)][0:dca_to_add], ignore_index=True)
            else:
                buy_lvdf = buy_lvdf.append(buy_levels.iloc[0:vars.LEVELS_PER_TF], ignore_index=True)

            # buy_lvdf = buy_lvdf.append(buy_levels, ignore_index=True)
            buy_lvdf['price'] = buy_lvdf['price'].astype(float)
            buy_lvdf.sort_values(by='price', ascending=False, inplace=True)
            buy_lvdf = buy_lvdf.drop_duplicates()

        if not sell_levels.empty:
            print("---- Closest {} {} SELL: {}".format(pair, tf, list(sell_levels.iloc[0:vars.LEVELS_PER_TF]['price'])))
            sell_lvdf = sell_lvdf.append(sell_levels.iloc[0:vars.LEVELS_PER_TF], ignore_index=True)
            # sell_lvdf = sell_lvdf.append(sell_levels, ignore_index=True)
            sell_lvdf['price'] = sell_lvdf['price'].astype(float)
            sell_lvdf.sort_values(by='price', ascending=True)
            sell_lvdf = sell_lvdf.drop_duplicates()

        # print("-" * 80)
        # print("levels tail: \n{}\nlevels head: {}".format(levels.tail(1), levels.head(1)))
        # print("candles tail: \n{}\ncandles head: {}".format(candles.tail(1), candles.head(1)))

    # buy_lvdf = buy_levels_filter(buy_lvdf)
    # sell_lvdf = sell_levels_filter(sell_lvdf)
    #
    # buy_lvdf = buy_lvdf.iloc[0:vars.MAX_DCA_NUMBER]


    if vars.TRADE_ON:
        print("Final Results: \n *** {} BUY LEVELS *** \n{}".format(pair, buy_lvdf))
        run_buy_dca_grid(pair, dca_orders, candles, buy_lvdf.append(sell_lvdf))
    else:
        print("{} Final Results: \n *** BUY LEVELS *** \n{} \n *** SELL LEVELS *** \n{}".format(pair, buy_lvdf,
                                                                                                sell_lvdf))
        # plot_data(candles, buy_lvdf.append(sell_lvdf))


def buy_levels_filter(levels):
    '''
    Function that filters out levels too close to each other and returns the filtered dataframe
    '''
    levels.reset_index(drop=True, inplace=True)
    levels['price'] = levels['price'].astype(float)
    print(" - - - Before filter: {}".format(levels['price']))
    ld = []
    # for i in levels.index:
    #     if i>0:
    #         if levels.iloc[i]['price'] > (levels.iloc[i-1]['price'] * (1 - MIN_LEVEL_DISTANCE/100)):
    #             ld.append(i)  # Add the row to the list for removal
    last_valid = 0
    for i in levels.index:
        if i > 0:
            if levels.iloc[i]['price'] > (levels.iloc[last_valid]['price'] * (1 - vars.MIN_LEVEL_DISTANCE / 100)):
                ld.append(i)
            else:
                last_valid = i

    levels.drop(ld, inplace=True)
    print(" - - - After filter: {}".format(levels['price']))
    return levels


def sell_levels_filter(levels):
    '''
    Function that filters out levels too close to each other and returns the filtered dataframe
    '''
    levels.reset_index(drop=True, inplace=True)
    levels['price'] = levels['price'].astype(float)
    ld = []
    jump = False
    for i in levels.index:
        if i > 0:
            if not jump:
                if levels.iloc[i]['price'] < (levels.iloc[i - 1]['price'] * (1 + vars.MIN_LEVEL_DISTANCE / 100)):
                    ld.append(i)
                    jump = True
                else:
                    jump = False
            else:
                if i > 2:
                    if levels.iloc[i]['price'] < (levels.iloc[i - 2]['price'] * (1 + vars.MIN_LEVEL_DISTANCE / 100)):
                        ld.append(i)
                        jump = True
                    else:
                        jump = False
    levels.drop(ld, inplace=True)
    return levels


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
            hh.append(last_candles.iloc[c]['High'] > last_candles.iloc[c - 1]['High'])
            lh.append(last_candles.iloc[c]['High'] < last_candles.iloc[c - 1]['High'])
            ll.append(last_candles.iloc[c]['Low'] < last_candles.iloc[c - 1]['Low'])
            hl.append(last_candles.iloc[c]['Low'] > last_candles.iloc[c - 1]['Low'])
            eh.append(last_candles.iloc[c]['High'] == last_candles.iloc[c - 1]['High'])
            el.append(last_candles.iloc[c]['Low'] == last_candles.iloc[c - 1]['Low'])

    last_candles['hh'] = hh
    last_candles['ll'] = ll
    last_candles['lh'] = lh
    last_candles['hl'] = hl
    last_candles['eh'] = eh
    last_candles['el'] = el
    last_candles['green_candle'] = green_candle

    return last_candles


def get_levels(candles, n):
    '''
    Function that returns the levels found in the N candles of whatever SYMBOL is passed, on the TF passed as well.
    param 'candles': The dataframe with all the candles information where to look for levels
    param 'levels': The dataframe to store all the levels found
    param 'n': The number of candles to look for levels into.
    Returns a list of the levels found in the candles.
    '''

    levels = pd.DataFrame(columns=vars.LEVEL_COLUMNS)

    if n < candles.shape[0]:
        n = candles.shape[0]

    print('Processing candles...')
    for i in range(n):
        if i > 5 and i < n:
            level_found = level_finder(candles.iloc[i - 5:i])
            # if datetime.strptime(candles.loc[i]['Date'].split('T')[0], '%Y-%m-%d') > datetime(2021, 11, 27):
            #     1==1
            #     pass
            if level_found != 0:
                levels = levels.append(pd.Series(data=level_found, index=vars.LEVEL_COLUMNS), ignore_index=True)
    print("Done.")
    return check_level_hits(levels, candles)


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
        if u_shape and (
                candles.iloc[4]['Low'] > candles.iloc[1]['High']):  # and not SHORT_ONLY_MODE: # BUY LEVEL FOUND HERE
            return (['buy', candles.iloc[1]['High'], False,
                     datetime.fromtimestamp(candles.iloc[1]['TimeStamp'] / 1000).isoformat()])
        if inv_u_shape and (
                candles.iloc[4]['High'] < candles.iloc[1]['Low']):  # and not LONG_ONLY_MODE: # SELL LEVEL FOUND
            return (['sell', candles.iloc[1]['Low'], False,
                     datetime.fromtimestamp(candles.iloc[1]['TimeStamp'] / 1000).isoformat()])

        return 0


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
        start_time = datetime.fromisoformat(levels.iloc[l]['time']).timestamp() * 1000
        valid_candles = candles[candles['TimeStamp'] > start_time]
        valid_candles.reset_index(inplace=True, drop=True)
        if levels.iloc[l]['side'] == 'buy':
            for i in valid_candles.index:
                # if i > 3 and valid_candles.iloc[i]['Low'] <= levels.iloc[l]['price']:
                if i > 3 and candles.iloc[-1]['Low'] <= levels.iloc[l]['price']:
                    levels.loc[l, 'hit'] = True
                    break
        else:
            for i in valid_candles.index:
                if i > 3 and valid_candles.iloc[i]['High'] >= levels.iloc[l]['price']:
                    levels.loc[l, 'hit'] = True
                    break

    return levels


def run_buy_dca_grid(pair, dca_orders, candles, unhit_levels=pd.DataFrame):
    if unhit_levels.empty:
        LEVELS = get_levels(candles, n=vars.NUM_CANDLES)

        UNHIT_LEVELS = LEVELS[LEVELS['hit'] == False]
        UNHIT_LEVELS.reset_index(inplace=True)
        entry, dca_list = entry_size(pair, UNHIT_LEVELS, long=True)
    else:
        entry, dca_list = entry_size(pair, unhit_levels, long=True)

    if dca_list:
        if dca_orders:
            ftx_functions.remove_orders(dca_orders)

        e_prices = dca_entries(entry, dca_list)

        for i in range(len(dca_list)):
            new_order(pair, 'buy', e_prices[i], dca_list[i], params={'positionSide': 'LONG'})
    else:
        print("No buy levels found. Nothing to do.")


def dca_entries(entry, levels):
    entries = []
    for l in range(len(levels)):
        entries.append(entry * (1.7 ** l))
    return entries


def entry_size(pair, levels, long=True):
    avl_bal, acc_bal = ftx_functions.get_balance()
    max_bpc = avl_bal * vars.MAX_BAL_PER_COIN / 100
    MIN_AMOUNT = calculate_min_amount(pair)

    print("Max allocation per asset: {}".format(max_bpc))
    print("Minimum entry size: {}".format(MIN_AMOUNT))

    buy_levels = levels[levels['side'] == 'buy'].sort_values(by='price', ascending=False)
    sell_levels = levels[levels['side'] == 'sell'].sort_values(by='price', ascending=True)

    if long:
        def_list = list(buy_levels['price'].astype(float))
    else:
        def_list = list(sell_levels['price'].astype(float))

    while len(def_list) > 0:
        min_entry_total_size = calc_max_position(MIN_AMOUNT, vars.DCA_FACTOR_MULT, def_list)

        if min_entry_total_size < max_bpc:  # Check if we cover the whole available balance with the minimum entry size
            entry = find_max_possible_entry(MIN_AMOUNT, max_bpc, vars.DCA_FACTOR_MULT, def_list)
            return entry, def_list
        elif min_entry_total_size == max_bpc:
            return min_entry_total_size, def_list
        else:
            # def_list.pop()
            # if len(def_list) == 0:
                print("Not enough balance, required: {}".format(min_entry_total_size))
                return 0, 0
    return 0, 0


def calculate_min_amount(pair):
    MIN_AMOUNT = exchange.load_markets(pair)[pair]['limits']['amount']['min']
    return float(exchange.amount_to_precision(pair, MIN_AMOUNT))


def find_max_possible_entry(min_amount, bal, factor, price_list):
    '''
    Function to find the maximum possible entry, by testing from the minimum entry size, increasing it sequentially
    until it gets to the value that fits within the maximum allowed balance per asset.
    '''
    max_entry = 0
    sum_positions = 0
    while sum_positions < bal:
        max_entry = max_entry + min_amount
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
