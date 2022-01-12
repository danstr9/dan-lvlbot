from vars import active_pairs, SP_TRIGGER_LIST, SP_MINIMUM_LIST
from utils.ftx_functions import get_current_positions, get_open_orders, check_sp
import time
from source_platform.ftx_exchange import exchange, client


def calculate_and_place_sp(position, n, pair):
    trigger_price = position['entryPrice'][0] * (1 + (SP_MINIMUM_LIST[n] / 100))
    exchange.create_order(pair, 'stop', 'sell', position['contracts'][0],
                          params={'triggerPrice': trigger_price, 'reduceOnly': True})


def main():
    while True:
        for pair in active_pairs:
            print('consume_sp_loop: checking pair: ' + pair)

            try:
                position = get_current_positions(pair).reset_index(drop=True)
                # open_orders = get_open_orders(pair)
            except:
                pass


            if 'position' in locals() and not position.empty:
                gain_pct = (float(position['unrealizedPnl'][0]) * 100) / float(position['notional'][0])
                for n in range(len(SP_TRIGGER_LIST)):
                    if n != len(SP_TRIGGER_LIST) - 1:
                        if SP_TRIGGER_LIST[n] < gain_pct < SP_TRIGGER_LIST[n + 1]:
                            calculate_and_place_sp(position, n, pair)
                            break
                    elif gain_pct > SP_TRIGGER_LIST[n]:
                        calculate_and_place_sp(position, n, pair)


            else:
                print('consume_tp_loop: No position for pair: ' + pair)

        time.sleep(15)


if __name__ == "__main__":
    main()