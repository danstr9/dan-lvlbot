from vars import active_pairs
from utils.ftx_functions import get_current_positions, get_open_orders, check_tp_grid
import time


def main():
    while True:
        for pair in active_pairs:
            print('consume_tp_loop: checking TP pair: ' + pair)

            try:
                position = get_current_positions(pair)
                open_orders = get_open_orders(pair)
            except:
                import pdb; pdb.set_trace()


            if not position.empty:
                check_tp_grid(pair, position, open_orders)
            else:
                print('consume_tp_loop: No position for pair: ' + pair)

        time.sleep(5)


if __name__ == "__main__":
    main()