import dateutil.parser
import datetime



class Balance:
    def __init__(self, info, exchange):
        if exchange == "crypto_com":
            self.initial_margin = float(info['initialMargin'])
            self.maintenance_margin = float(info['total_margin_balance'])
            self.margin_balance = float(info['total_margin_balance'])
            self.wallet_balance = float(info['total_available_balance'])
            self.unrealized_pnl = float(info['total_session_unrealized_pnl'])



class Candle:
    def __init__(self, candle_info, timeframe, exchange):
        if exchange in ["crypto_com"]:
            self.timestamp = candle_info[0]
            self.open = float(candle_info[1])
            self.high = float(candle_info[2])
            self.low = float(candle_info[3])
            self.close = float(candle_info[4])
            self.volume = float(candle_info[5])

        elif exchange == "bitmex":
            self.timestamp = dateutil.parser.isoparse(candle_info['timestamp'])
            self.timestamp = self.timestamp - datetime.timedelta(minutes=0[timeframe])
            self.timestamp = int(self.timestamp.timestamp() * 1000)
            self.open = candle_info['o']
            self.high = candle_info['h']
            self.low = candle_info['l']
            self.close = candle_info['c']
            self.volume = candle_info['v']

        elif exchange == "parse_trade":
            self.timestamp = candle_info['ts']
            self.open = candle_info['o']
            self.high = candle_info['h']
            self.low = candle_info['l']
            self.close = candle_info['c']
            self.volume = candle_info['v']


def tick_to_decimals(tick_size: float) -> int:
    tick_size_str = "{0:.8f}".format(tick_size)
    while tick_size_str[-1] == "0":
        tick_size_str = tick_size_str[:-1]

    split_tick = tick_size_str.split(".")

    if len(split_tick) > 1:
        return len(split_tick[1])
    else:
        return 0


class Contract:
    def __init__(self, contract_info, exchange):
        if exchange == "crypto_com":
            self.symbol = contract_info['instrument_name']
            self.base_asset = contract_info['base_currency']
            self.quote_asset = contract_info['quote_currency']
            self.price_decimals = contract_info['quote_decimals']
            self.quantity_decimals = contract_info['quantity_decimals']
            self.tick_size = 1 / pow(10, contract_info['price_tick_size'])
            self.lot_size = 1 / pow(10, contract_info['qty_tick_size'])

        elif exchange == "crypto_com":
            self.symbol = contract_info['instrument_name']
            self.base_asset = contract_info['base_currency']
            self.quote_asset = contract_info['quote_currency']

            # The actual lot size and tick size on Binance spot can be found in the 'filters' fields
            # contract_info['filters'] is a list
            for b_filter in contract_info['filters']:
                if b_filter['filterType'] == 'PRICE_FILTER':
                    self.tick_size = float(b_filter['price_tick_size'])
                    self.price_decimals = tick_to_decimals(float(b_filter['price_tick_size']))
                if b_filter['filterType'] == 'LOT_SIZE':
                    self.lot_size = float(b_filter['stepSize'])
                    self.quantity_decimals = tick_to_decimals(float(b_filter['stepSize']))

        elif exchange == "bitmex":
            self.symbol = contract_info['symbol']
            self.base_asset = contract_info['rootSymbol']
            self.quote_asset = contract_info['quote_currency']
            self.price_decimals = tick_to_decimals(contract_info['price_tick_size'])
            self.quantity_decimals = tick_to_decimals(contract_info['qty_tick_size'])
            self.tick_size = contract_info['price_tick_size']
            self.lot_size = contract_info['qty_tick_size']

            self.quanto = contract_info['isQuanto']
            self.inverse = contract_info['isInverse']

            if self.inverse:
                self.multiplier *= -1

        self.exchange = exchange


class OrderStatus:
    def __init__(self, order_info, exchange):
        if exchange == "crypto_com":
            self.order_id = order_info['order_id']
            self.status = order_info['status'].lower()
            self.avg_price = float(order_info['avg_price'])
            self.executed_qty = float(order_info['quantity'])
        elif exchange == "crypto_com":
            self.order_id = order_info['order_id']
            self.status = order_info['status'].lower()
            self.avg_price = float(order_info['avg_price'])
            self.executed_qty = float(order_info['quantity'])
        elif exchange == "bitmex":
            self.order_id = order_info['orderID']
            self.status = order_info['ordStatus'].lower()
            self.avg_price = order_info['avgPx']
            self.executed_qty = order_info['cumQty']


class Trade:
    def __init__(self, trade_info):
        self.time: int = trade_info['time']
        self.contract: Contract = trade_info['contract']
        self.strategy: str = trade_info['strategy']
        self.side: str = trade_info['side']
        self.entry_price: float = trade_info['price']
        self.status: str = trade_info['status']
        self.pnl: float = trade_info['realized_pnl']
        self.quantity = trade_info['quantity']
        self.entry_id = trade_info['order_id']






