import ccxt
import talib
import numpy as np
import datetime
import time
import sys
import pandas as pd
import json
import requests
# Initialize Bybit exchange object
exchange = ccxt.bybit({
    'apiKey': 'YrPe5CCJzfCCEorb1t',
    'secret': 'rGKGT1dk0LqyKZ3Bfmb2fy1RttprqajrYB97',
    'enableRateLimit': True,
    'rateLimit': 2000,
    
    'options': {
        'defaultType': 'future',
        #'recvWindow': 5000  # Set recv_window to 10 seconds (10000 milliseconds)
    }
})
bot_token = '6806933529:AAFrTyWtZMGpfQ1n_ovpEBdcnQxIkcBgw6Y'
# Define function to get recent OHLCV data
#def get_recent_data(symbol, timeframe):
#    return exchange.fetch_ohlcv(symbol, timeframe)[-100:]

def get_recent_data(symbol, timeframe):
    #ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
    #data = np.array(ohlcv)
    #print(data[-100:])
    current_datetime = datetime.datetime.now()

    # Set the start time to 12:00 AM (00:00:00) 7 days ago
    start_datetime = current_datetime - datetime.timedelta(days=1)
    #start_datetime = current_datetime - datetime.timedelta(minutes=5)
    start_datetime = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)

    # Set the end time to the current date and time
    end_datetime = current_datetime

    # Convert the datetime objects to timestamps in milliseconds
    start_timestamp = int(start_datetime.timestamp() * 1000)
    end_timestamp = int(end_datetime.timestamp() * 1000)
    con = symbol.replace('/','')
    kline_url = f'https://api.bybit.com/derivatives/v3/public/kline?category=linear&symbol={con}&interval=15&start={start_timestamp}&end={end_timestamp}'
    kline_response = requests.get(kline_url)
    print(kline_url)
    kline_data = kline_response.json()
    data2 = np.array(kline_data['result']['list'])
    # Convert the elements to float and int values
    converted_data = np.array([[int(item) if item.isdigit() else float(item) for item in row] for row in data2])

    #print(converted_data)
    #print(data2[-100:])
    #dee = converted_data[-100:]
    #print(dee[:,4])
    return converted_data[-100:]

# Define function to calculate moving averages
def calculate_moving_averages(data, ma_short_period, ma_long_period):
    ma_short = talib.SMA(data[:,4], timeperiod=ma_short_period)
    ma_long = talib.SMA(data[:,4], timeperiod=ma_long_period)
    return ma_short[-1], ma_long[-1], ma_short[-2], ma_long[-2]

# Define function to calculate RSI
def calculate_rsi(data, rsi_period):
    rsi = talib.RSI(data[:,4], timeperiod=rsi_period)
    return rsi[-1]
def calculate_cci(data, cci_period):
    cci = talib.CCI(data[:,2],data[:,3],data[:,4], timeperiod=cci_period)
    return cci[-1]
# Define function to calculate Bollinger Bands
def calculate_bollinger_bands(data):
    ma = talib.SMA(data[:,4], timeperiod=20)
    std = np.std(data[:,4])
    upper_band = ma + 2 * std
    lower_band = ma - 2 * std
    return upper_band[-1], lower_band[-1]

# Define function to place a buy order
def place_buy_order(symbol, price, quantity, take_profit=None, stop_loss=None, margin=None):
    params = {
        'stopLoss': stop_loss,  # your stop loss price
        'takeProfit': take_profit,
        'marginMode': 'isolated',
        'leverage': 50,
    }
    #if margin is not None:
    #    params['positionAmt'] = margin
    order = exchange.create_order(symbol+':USDT', 'limit', 'buy', quantity, price, params)
    #order = exchange.create_order(**params)
    #order = exchange.create_order(None, 'future', 'POST', '/v2/private/order/create', params)
    return order

# Define function to place a sell order
def place_sell_order(symbol, price, quantity, take_profit=None, stop_loss=None, margin=None):
    # for a stop loss order
    params = {
        'stopLoss': stop_loss,  # your stop loss price
        'takeProfit': take_profit,
        'marginMode': 'isolated',
        'leverage': 50,
    }
    
    #if margin is not None:
    #    params['positionAmt'] = margin

    order = exchange.create_order(symbol+':USDT', 'limit', 'sell', quantity, price, params)
    #order = exchange.create_order(**params)
    #order = exchange.create_order(None, 'future', 'POST', '/v2/private/order/create', params)
    return order

# Define function to check if there are any open orders
def check_open_orders(symbol):
    orders = exchange.fetch_open_orders(symbol+':USDT')
    return len(orders) > 0
def fetch_completed_trades_today(since):
    total_trades = 0
    # Assuming you have a predefined list of symbols; otherwise, you can fetch all symbols from the exchange
    symbols = exchange.symbols  # or a subset, e.g., ['BTC/USDT', 'ETH/USDT']

    print(len(symbols))
    tradesv = exchange.fetch_orders()
    tradesf = exchange.fetch_closed_orders(since=since)
    tradesg = exchange.fetch_positions()
    print(tradesf)

    # for symbol in symbols:
    #     try:
    #         trades = exchange.fetch_my_trades(symbol)
    #         total_trades += len(trades)
    #     except Exception as e:
    #         print(f"Error fetching trades for {symbol}: {e}")
    return len(tradesf)

def check_day_trade_limit(limit=10):
    # Calculate the start of the current UTC day in milliseconds
    utc_now = datetime.datetime.utcnow()
    start_of_day = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
    since = int(start_of_day.timestamp()) * 1000  # Convert to milliseconds

    total_trades_today = fetch_completed_trades_today(since)
    return total_trades_today >= limit
# Define function to cancel all open orders
def cancel_all_orders(symbol):
    orders = exchange.fetch_open_orders(symbol+':USDT')
    for order in orders:
        exchange.cancel_order(order['id'], symbol)

# Define function to get the current price of a symbol
def get_current_price(symbol):
    ticker = exchange.fetch_ticker(symbol+':USDT')
    return ticker['last']

def execute_trade(symbol, strategy, strategy_params, stop_loss, take_profit, quantity):
    # Get recent data for the symbol
    data = get_recent_data(symbol, strategy_params['timeframe'])
    #print(data)
    newdata = pd.DataFrame(data)
    print(newdata)
    #print(f"Recent data for {symbol}:\n{data}")

    # Calculate the indicators based on the selected strategy
    if strategy == 'moving_average':
        ma_short, ma_long , ma_shortb, ma_longb = calculate_moving_averages(data, strategy_params['ma_short_period'], strategy_params['ma_long_period'])
        
        rsi = calculate_rsi(data, 24)

        print(f"MA Short: {ma_short}\nMA Long: {ma_long}\nRsi: {rsi}")
    # Calculate the indicators based on the selected strategy
    if strategy == 'ema_rsi_cci':
        ma_short, ma_long , ma_shortb, ma_longb = calculate_moving_averages(data, strategy_params['ma_short_period'], strategy_params['ma_long_period'])
        
        rsi = calculate_rsi(data, 24)

        cci = calculate_cci(data, 50)

        print(f"MA Short: {ma_short}\nMA Long: {ma_long}\nRsi: {rsi}")
    

    # Check if there are any open orders and cancel them
    if check_open_orders(symbol):
        return
        #cancel_all_orders(symbol)
    day_trade_limit_reached = check_day_trade_limit()
    if day_trade_limit_reached:
        print(f"Day trade limit reached for {symbol}.")
        bot_message = f"Day trade limit reached for {symbol}"
        bot_chatID = str(-1002061445446)
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        return
    #else:
    #    print(f"Day trade limit not yet reached for {symbol}. You can trade.")

    # Place a buy order if the conditions are met
    current_price = get_current_price(symbol)
    if strategy == 'moving_average':
        if ma_short > ma_long and current_price > ma_short and rsi<50:
            buy_price = current_price * (1 - 0.01)
            stop_loss_price = buy_price * (1 - stop_loss)
            take_profit_price = buy_price * (1 + take_profit)
            
            order = place_buy_order(symbol, buy_price, quantity, take_profit_price, stop_loss_price, 50)
            order_id = order['id']
            print(f"Buy order placed for {symbol} at {buy_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}")
            bot_message = f"Buy order placed for {symbol} at {buy_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}"
            bot_chatID = str(-1002061445446)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
        elif ma_short < ma_long and current_price < ma_short and rsi>50:
            sell_price = current_price * (1 + 0.01)
            stop_loss_price = sell_price * (1 + stop_loss)
            take_profit_price = sell_price * (1 - take_profit)
            
            order = place_sell_order(symbol, sell_price, quantity, take_profit_price, stop_loss_price, 50)
            order_id = order['id']
            
            print(f"Sell order placed for {symbol} at {sell_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}")
            bot_message = f"Sell order placed for {symbol} at {sell_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}"
            bot_chatID = str(-1002061445446)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
    if strategy == 'ema_rsi_cci':
        if (ma_shortb < ma_longb and ma_short > ma_long) and rsi<50 and cci>80:
            buy_price = current_price * (1 - 0.01)
            stop_loss_price = buy_price * (1 - stop_loss)
            take_profit_price = buy_price * (1 + take_profit)
            
            order = place_buy_order(symbol, buy_price, quantity, take_profit_price, stop_loss_price, 50)
            order_id = order['id']
            print(f"Buy order placed for {symbol} at {buy_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}")
            bot_message = f"Buy order placed for {symbol} at {buy_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}"
            bot_chatID = str(-1002061445446)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
        elif (ma_shortb > ma_longb and ma_short < ma_long) and rsi>50 and cci<45:
            sell_price = current_price * (1 + 0.01)
            stop_loss_price = sell_price * (1 + stop_loss)
            take_profit_price = sell_price * (1 - take_profit)
            
            order = place_sell_order(symbol, sell_price, quantity, take_profit_price, stop_loss_price, 50)
            order_id = order['id']
            
            print(f"Sell order placed for {symbol} at {sell_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}")
            bot_message = f"Sell order placed for {symbol} at {sell_price} with stop loss at {stop_loss_price} and take profit at {take_profit_price}"
            bot_chatID = str(-1002061445446)
            send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
            response = requests.get(send_text)
    # Monitor the open order
    while check_open_orders(symbol):
        orders = exchange.fetch_open_orders(symbol+':USDT')
        print(orders)
        order = orders[0]
        print(order)
        order_id = order['id']
        order_status = order['status']
        print(f"Order {order_id} status: {order_status}")
        time.sleep(10)

    # Print final result
    print("Trade complete!")
    time.sleep(15)

# Set the symbol, strategy, strategy parameters, stop loss, take profit, and quantity
#symbol = 'APT/USDT'
symbol = sys.argv[1]
print(symbol)

#time.sleep(50)

if symbol == 'USDC/USDT' or symbol == 'BUSD/USDT' or symbol == 'TUSD/USDT' or symbol == 'ARKMUSDT':
    sys.exit(1)


strategy = sys.argv[2]

if strategy == 'moving_average':
    strategy_params = {'timeframe': '30m', 'ma_short_period': 5, 'ma_long_period': 22}
if strategy == 'ema_rsi_cci':
    strategy_params = {'timeframe': '30m', 'ma_short_period': 5, 'ma_long_period': 21}
stop_loss = 0.02
take_profit = 0.04
#quantity = 11
leverage = 25
# Get the global USDT balance
usdt_balance = exchange.fetch_balance()['total']['USDT']
max_risk_amount = usdt_balance * 0.02
current_price = get_current_price(symbol)
print(f"Global USDT Balance: {usdt_balance}")

try:
    params = {
        'sell_leverage':25,
        'buy_leverage':25
    }
    params2 = {}
    try:
        mar = exchange.set_margin_mode('isolated',symbol+':USDT',params)
    
        print(mar)
    except ccxt.ExchangeError as e:
        error_msg = e.args[0]  # Get the error message
        #print(str(error_msg).replace('bybit ',''))
        print(error_msg)
        error_json = json.loads(str(error_msg).replace('bybit ',''))
        # Handle specific exchange errors
        print("Exchange error passing 25X:", str(e))
        print('pass')
    lev = exchange.set_leverage(25,symbol+':USDT',params2)
    print("lev")
    
    print(lev['retMsg'])
    
    
#except:
#    sys.exit(1)
    #as_json = json.loads(lev)
    if lev['retMsg'] == 'Ok':
        #max_risk_amount = max_risk_amount + max_risk_amount
        bot_message = f"Reading... for {symbol} margin 25x set"
        bot_chatID = str(-1002061445446)
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
    
except ccxt.ExchangeError as e:
    error_msg = e.args[0]  # Get the error message
    #print(str(error_msg).replace('bybit ',''))
    error_json = json.loads(str(error_msg).replace('bybit ',''))
    # Handle specific exchange errors
    print("Exchange error passing 25X:", str(e))
    #error_json = json.loads(str(e))
    #print(error_json)
    ret_msg = error_json['retMsg']
    
    if ret_msg == 'Set leverage not modified':
        #max_risk_amount = max_risk_amount + max_risk_amount
        leverage = 25
        bot_message = f"Reading... for {symbol} margin 25x modified before"
        bot_chatID = str(-1002061445446)
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
            # Handle the specific error case
    #    print("Isolated margin type not modified.")
    #    bot_message = f"Reading... for {symbol} Isolated margin 50x type not modified cause was added before."
    #    bot_chatID = str(-1002061445446)
    #    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    #    response = requests.get(send_text)
        pass
    #elif ret_msg == 'params error: buy or sell leverage is greater than 25':
    elif ret_msg == 'buy leverage invalid':
        
        try:
            params = {
                        'sell_leverage':20,
                        'buy_leverage':20
                     }
            params2 = {}
            try:
                mar = exchange.set_margin_mode('isolated',symbol+':USDT',params)
            
                print(mar)
            except:
                print('pass')
            lev = exchange.set_leverage(20,symbol+':USDT',params2)
            print(lev)
            #mar = exchange.set_margin_mode('isolated',symbol+':USDT',params)

            #print(mar)
            #as_json = json.loads(lev)
            if lev['retMsg'] == 'Ok':
                leverage = 20
                bot_message = f"Reading... for {symbol} margin 20x set"
                bot_chatID = str(-1002061445446)
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
                response = requests.get(send_text)
        except ccxt.ExchangeError as e:
            error_msg3 = e.args[0]  # Get the error message
            #print(str(error_msg2).replace('bybit ',''))
            error_json3 = json.loads(str(error_msg3).replace('bybit ',''))
            # Handle specific exchange errors
            print("Exchange error passing 20x:", str(e))
            #error_json = json.loads(str(e))
            #print(error_json)
            ret_msg3 = error_json3['retMsg']

            if ret_msg3 == 'Set leverage not modified':
                leverage = 20
                bot_message = f"Reading... for {symbol} margin 20x modified before"
                bot_chatID = str(-1002061445446)
                send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
                response = requests.get(send_text)
                pass

            elif ret_msg3 == 'buy leverage invalid':
                params = {
                            'sell_leverage':10,
                            'buy_leverage':10
                        }
                params2 = {}
                try:
                    try:
                        mar = exchange.set_margin_mode('isolated',symbol+':USDT',params)
                    
                        print(mar)
                    except:
                        print('pass')
                    lev = exchange.set_leverage(10,symbol+':USDT',params2)
                    
                    print(lev)
                    
                    # Handle the specific error case
                    #as_json = json.loads(lev)
                    if lev['retMsg'] == 'Ok':
                        leverage = 10
                        bot_message = f"Reading... for {symbol} Isolated margin 10x set."
                        bot_chatID = str(-1002061445446)
                        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
                        response = requests.get(send_text)
                        
                except ccxt.ExchangeError as e:
                    error_msg2 = e.args[0]  # Get the error message
                    #print(str(error_msg2).replace('bybit ',''))
                    error_json2 = json.loads(str(error_msg2).replace('bybit ',''))
                    # Handle specific exchange errors
                    print("Exchange error passing 10X:", str(e))
                    leverage = 10
                    pass
    else:
            # Handle other exchange errors
        print("Exchange error:", str(e))
        time.sleep(15)
        sys.exit(1)

# Update the pair configuration with the desired margin type and leverage
#pair_config['info']['marginType'] = 'isolated'
#pair_config['info']['leverage'] = 50

# Calculate the maximum risk amount


if usdt_balance > 0 and usdt_balance <= 300:
    max_risk_amount = max_risk_amount / 2
if usdt_balance > 300 and usdt_balance <= 500:
    max_risk_amount = max_risk_amount / 2
if usdt_balance > 500 and usdt_balance <= 1000:
    max_risk_amount = max_risk_amount / 2
#print(max_risk_amount)
#symbols = exchange.fetch_markets()
#for symbol in symbols:
#    print(symbol['symbol'])
# Get market information for the trading pair
#symbol = 'OP/USDT:USDT'
#market = exchange.market(symbol)

# Get the margin mode for the trading pair
#margin_mode = market['info']['margin_mode']
#print(f"Margin Mode for {symbol}: {margin_mode}")

#order = place_buy_order('OP/USDT:USDT', 1.6713, quantity)

# Define the initial order value and the increment step
initial_order_value = 1
increment_step = 0.1

# Initialize variables
order_value = initial_order_value
actual_risk_amount = 0
qty = 0

# Iterate until the actual risk amount is less than the maximum risk amount
while actual_risk_amount < max_risk_amount:
    # Calculate the quantity using the current order value, order price, and leverage
    #print(actual_risk_amount)
    qty = (order_value / current_price) * leverage

    # Calculate the actual risk amount based on the calculated quantity
    actual_risk_amount = (qty * current_price) / leverage

    # Increment the order value
    order_value += increment_step

# Adjust the order value based on the iteration result
order_value -= increment_step

print(f"Order Value: {order_value:.2f}")
print(f"Qty: {qty:.2f}")
print(f"Actual Risk Amount: {actual_risk_amount:.2f}")

quantity = qty



# Execute the trade
execute_trade(symbol, strategy, strategy_params, stop_loss, take_profit, quantity)
