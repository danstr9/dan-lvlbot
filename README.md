# dan-lvlbot
## NOTE: THIS CODE IS STILL UNDER DEVELOPMENT.
### This has been mostly tested in Binance Futures, FTX is not fully developed yet, still work in progress.

A bot for trading binance futures and FTX based on price action levels.

The bot supports any timeframes supported by the exchanges.
In current version (v1) it only works with 1 pair at a time.

It requires a separate config.py file where the API keys for each exchange and FTX subaccount name will be.

## How it works?
The goal of this bot is to trade (in long mode only for now) automatically, based on the levels it will find (levels are found according to certain price action formations that have been seen traditionally as key to find reactions from the market, could be considered support/resistances)

To run the bot, **first of all**, the specific variables will need to be populated in the vars.py file, which include the Exchange (Binance or FTX), the coin to use, the list of time frames where to look for levels, and some other variables related to the balance to use, where to take profit, etc.

This bot will run forever until a crash/exception occurs or its process is killed, there is no other mechanism to start/stop it.

When started, the bot will evaluate if there is already a position open for the specified asset, if there is one, it will check if the corresponding take profit orders are in place and will add them if they are not, otherwise it will keep monitoring the position every 5 seconds.

If there is no position, the bot will first start running the algorythm to calculate all levels that are not hit, in the corresponding timeframes specified in the vars.py file. The default timeframes I initially included are 1m, 5m, 15m, 1h, 4h and 12h, but those can be modified in the vars file.

Once the levels are found (initially configured to gather the 2 closest levels found per timeframe, but this can be modified via corresponding variable) it will calculate the DCA grid to see how many levels/DCA entries will be able to allocate and the corresponding size, and then will place the orders for the DCA grid.

With the grid in place, it will continue checking every 5 seconds to see if it's in position or not (the moment it detects a position, it will create the corresponding Take Profit grid) and if not in position, it will run the algo to gather new levels every 5 minutes.

The bot will leave records of all the actions in the screen where it's running.
