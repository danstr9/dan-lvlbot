from vars import active_pairs
from utils.ftx_functions import get_current_positions, get_open_orders
from utils.common_functions import check_dca_orders
import time


def main():
    while True:
        for pair in active_pairs:
            print('consume_dca_loop: checking DCA pair: ' + pair)

            try:
                position = get_current_positions(pair)
                open_orders = get_open_orders(pair)
            except:
                pass

            if 'position' in locals() and 'open_orders' in locals() and position.empty:
                print('consume_dca_loop: no position, placing dca for pair: ' + pair)
                check_dca_orders(pair, open_orders)
            else:
                print('consume_dca_loop: position already found on pair: ' + pair)

        time.sleep(120)


if __name__ == "__main__":
    main()