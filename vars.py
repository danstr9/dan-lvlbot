######################## GLOBAL VARIABLES #########################
BINANCE = True # Variable to indicate which exchange to use: True for BINANCE, False for FTX
SHITCOIN = 'xrp'
MULTI_TF = True
TF_LIST = ['12h','4h','1h','15m','5m','1m']
TF = '5m'
LEVELS_PER_TF = 2 # Number of levels per Time Frame to include in the list of DCAs
DAYS_BACK = 10 # Number of days to look back in time for initial candles data
TRADE_ON = True
###################################################################

# Balance variables
MAX_BAL_PER_COIN = 10 # Maximum percentage of balance to use per asset/coin
LVRG = 20

# Take Profit variables
TPGRID_MIN_DIST = 0.2 # Percentage to use for the closest order in the TP grid
TPGRID_MAX_DIST = 0.8  # Percentage to use for the farthest order in the TP grid
TP_ORDERS = 6 # Number of orders for the TP grid
ASSYMMETRIC_TP = False # False for equal sized orders, False for descending size TP orders 
MIN_LEVEL_DISTANCE = 0.8 # Variable to indicate what % will be the minimum valid distance between levels found
