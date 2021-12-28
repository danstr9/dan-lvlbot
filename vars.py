######################## GLOBAL VARIABLES #########################
BINANCE = True # Variable to indicate which exchange to use: True for BINANCE, False for FTX
SHITCOIN = 'ftm'
MULTI_TF = True
TF_LIST = ['4h','1h','15m','5m','1m']
TF = '1h'
LEVELS_PER_TF = 3 # Number of levels per Time Frame to include in the list of DCAs
DAYS_BACK = 90 # Number of days to look back in time for initial candles data
TRADE_ON = False
###################################################################

# Balance variables
MAX_BAL_PER_COIN = 10 # Maximum percentage of balance to use per asset/coin
LVRG = 20

# Take Profit variables
TPGRID_MIN_DIST = 0.2 # Percentage to use for the closest order in the TP grid
TPGRID_MAX_DIST = 0.8  # Percentage to use for the farthest order in the TP grid
TP_ORDERS = 6 # Number of orders for the TP grid
DCA_FACTOR_MULT = 1.75 # Factor to multiply each DCA entry in the grid (it will multiply the amount of previous DCA by this factor)
ASSYMMETRIC_TP = False # False for equal sized orders, False for descending size TP orders 
MIN_LEVEL_DISTANCE = 0.8 # Variable to indicate what % will be the minimum valid distance between levels found
