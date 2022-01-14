from vars import active_pairs, SP_TRIGGER_LIST, SP_MINIMUM_LIST
from utils.ftx_functions import get_current_positions, get_stops_orders
import time
from source_platform.ftx_exchange import exchange, client

def place_sp(position, pair,trigger_price):
    exchange.create_order(pair, 'stop', 'sell', position['contracts'][0],
                          params={'triggerPrice': trigger_price, 'reduceOnly': True})

def delete_old_sp(stop_order):
    for sp in stop_order:
        exchange.cancel_order(int(sp['id']), params={'type': 'stop'})

def sp_cycle(position, pair, n):
    trigger_price = position['entryPrice'][0] * (1 + (SP_MINIMUM_LIST[n] / 100))

    stop_orders = []
    try:
        stop_orders = get_stops_orders(pair)
    except Exception as e:
        print(e)
        pass

    if len(stop_orders):

        num_decimals = str(stop_orders[0]['price'])[::-1].find('.')

        if not round(trigger_price, num_decimals) <= stop_orders[0]['price']:
            delete_old_sp(stop_orders)
            place_sp(position, pair, trigger_price)
            print('Stop profit placed for pair: ' + pair + ' at price: ' + str(trigger_price))

        else:
            print('Stop profit in place for pair: ' + pair)
    else:
        place_sp(position, pair, trigger_price)
        print('Stop profit in placed for pair: ' + pair + 'at price: ' + str(trigger_price))

    placed = True

    return placed

def main():
    while True:
        for pair in active_pairs:
            print('consume_sp_loop: checking pair: ' + pair)

            try:
                position = get_current_positions(pair).reset_index(drop=True)
            except Exception as e:
                print(e)
                pass


            if 'position' in locals() and not position.empty:
                gain_pct = (float(position['unrealizedPnl'][0]) * 100) / float(position['notional'][0])
                placed = False

                for n in range(len(SP_TRIGGER_LIST)):

                    if placed:
                        break
                    else:

                        if n != len(SP_TRIGGER_LIST) - 1:
                            if SP_TRIGGER_LIST[n] < gain_pct < SP_TRIGGER_LIST[n + 1]:
                                placed = sp_cycle(position, pair, n)

                        elif gain_pct > SP_TRIGGER_LIST[n]:
                            placed = sp_cycle(position, pair, n)


            else:
                print('consume_tp_loop: No position for pair: ' + pair)
                stop_orders = []

                try:
                    stop_orders = get_stops_orders(pair)
                except Exception as e:
                    print(e)
                    pass

                if len(stop_orders):
                    delete_old_sp(stop_orders)

        time.sleep(10)


if __name__ == "__main__":
    main()