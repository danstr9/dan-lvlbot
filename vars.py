######################## GLOBAL VARIABLES #########################
BINANCE = False # Variable to indicate which exchange to use: True for BINANCE, False for FTX
active_pairs = ['ATOM-PERP']
MULTI_TF = True
TF_LIST = ['5m', '15m', '1h', '4h']
TF = '1h'
LEVELS_PER_TF = 3 # Number of levels per Time Frame to include in the list of DCAs
DAYS_BACK = 90 # Number of days to look back in time for initial candles data
TRADE_ON = True
###################################################################

# Balance variables
MAX_BAL_PER_COIN = 25 # Maximum percentage of balance to use per asset/coin
LVRG = 20

# Take Profit variables
TPGRID_MIN_DIST = 1 # Percentage to use for the closest order in the TP grid
TPGRID_MAX_DIST = 4  # Percentage to use for the farthest order in the TP grid
TP_ORDERS_NUMBER = 6 # Number of orders for the TP grid
DCA_FACTOR_MULT = 1.75 # Factor to multiply each DCA entry in the grid (it will multiply the amount of previous DCA by this factor)
ASSYMMETRIC_TP = False # False for equal sized orders, False for descending size TP orders 
MIN_LEVEL_DISTANCE = 1.2 # Variable to indicate what % will be the minimum valid distance between levels found
MAX_DCA_NUMBER = 9
SP_TRIGGER_LIST = [1.5, 2.5, 3.2]
SP_MINIMUM_LIST = [0.8, 1.5, 2.5]
LEVEL_COLUMNS = ['side', 'price', 'hit', 'time']

# Candles calculation
if 'm' in TF:
    TF_NUM = int(TF.split('m')[0]) # Used for FTX candles
    NUM_CANDLES = int(DAYS_BACK * 24 * 60 / TF_NUM)
elif 'h' in TF:
    TF_NUM = int(TF.split('h')[0]) * 60
    NUM_CANDLES = int(DAYS_BACK * 24 * 60 / TF_NUM)

tflist_daysago_mapping = {'1m': 1, '3m': 2, '5m': 5, '15m': 10, '1h': 60, '4h': 150, '12h': 365, '1d': 720}