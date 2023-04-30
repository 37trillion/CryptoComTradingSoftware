import logging
import requests
import time
import typing
import collections

from urllib.parse import urlencode

import hmac
import hashlib

import websocket
import json

import threading

from models import *
from strategies import TechnicalStrategy, BreakoutStrategy


logger = logging.getLogger()


class CryptoComClient:
    def __init__(self, public_key: str, secret_key: str, testnet: bool, cryptocom: bool):

        """
        https://CryptoCom-docs.github.io/apidocs/cryptocom/en
        :param public_key:
        :param secret_key:
        :param testnet:
        :param cryptocom: if False, the Client will be a Spot API Client
        """

        self.cryptocom = cryptocom

        if self.cryptocom:
            self.platform = "crypto_com"
            if testnet:
                self._base_url = "https://uat-api.3ona.co/exchange/v1/"
                self._wss_url = "wss://uat-stream.3ona.co/exchange/v1/user"
            else:
                self._base_url = "https://api.crypto.com/public"
                self._base_url = "https://api.crypto.com/private"
                self._wss_url = "wss://stream.crypto.com/exchange/v1/user"
    

        self._public_key = public_key
        self._secret_key = secret_key

        self._headers = {'X-MBX-APIKEY': self._public_key + self._secret_key}

        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()
        self.strategies: typing.Dict[int, typing.Union[TechnicalStrategy, BreakoutStrategy]] = dict()

        self.logs = []

        self._ws_id = 1
        self.ws: websocket.WebSocketApp
        self.reconnect = True
        self.ws_connected = False
        self.ws_subscriptions = {"book": [], "aggTrade": []}

        t = threading.Thread(target=self._start_ws)
        t.start()

        logger.info("CryptoCom cryptocom Client successfully initialized")

    def _add_log(self, msg: str):

        """
        Add a log to the list so that it can be picked by the update_ui() method of the root component.
        :param msg:
        :return:
        """

        logger.info("%s", msg)
        self.logs.append({"log": msg, "displayed": False})

    def _generate_signature(self, data: typing.Dict) -> str:

        """
        Generate a signature with the HMAC-256 algorithm.
        :param data: Dictionary of parameters to be converted to a query string
        :return:
        """

        return hmac.new(self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    def _make_request(self, method: str, endpoint: str, data: typing.Dict):

        """
        Wrapper that normalizes the requests to the REST API and error handling.
        :param method: GET, POST, DELETE
        :param endpoint: Includes the /api/v1 part
        :param data: Parameters of the request
        :return:
        """

        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:  # Takes into account any possible error, most likely network errors
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "POST":
            try:
                response = requests.post(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None

        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, params=data, headers=self._headers)
            except Exception as e:
                logger.error("Connection error while making %s request to %s: %s", method, endpoint, e)
                return None
        else:
            raise ValueError()

        if response.status_code == 200:  # 200 is the response code of successful requests
            return response.json()
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)",
                         method, endpoint, response.json(), response.status_code)
            return None

    def get_contracts(self) -> typing.Dict[str, Contract]:

        """
        Get a list of instrument_names/contracts on the exchange to be displayed in the OptionMenus of the interface.
        :return:
        """

        if self.cryptocom:
            exchange_info = self._make_request("GET", "/v2/public/get-instruments", dict())
        else:
            exchange_info = self._make_request("GET", "/v2/public/get-instruments", dict())

        contracts = dict()

        if exchange_info is not None:
            for contract_data in exchange_info['instrument_name']:
                contracts[contract_data['instrument_name']] = Contract(contract_data, self.platform)

        return collections.OrderedDict(sorted(contracts.items()))  # Sort keys of the dictionary alphabetically

    def get_historical_candles(self, contract: Contract, interval: str) -> typing.List[Candle]:

        """
        Get a list of the most recent candlesticks for a given instrument_name/contract and interval.
        :param contract:
        :param interval: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        :return:
        """

        data = dict()
        data['instrument_name'] = contract.instrument_name
        data['interval'] = interval
        data['limit'] = 1000  # The maximum number of candles is 1000 on CryptoCom Spot

        if self.cryptocom:
            raw_candles = self._make_request("GET", "/v2/public/get-candles", data)
        else:
            raw_candles = self._make_request("GET", "/v2/public/get-candles", data)

        candles = []

        if raw_candles is not None:
            for c in raw_candles:
                candles.append(Candle(c, interval, self.platform))

        return candles

    def get_bid_ask(self, contract: Contract) -> typing.Dict[str, float]:

        """
        Get a snapshot of the current bid and ask price for a instrument_name/contract, to be sure there is something
        to display in the Watchlist.
        :param contract:
        :return:
        """

        data = dict()
        data['instrument_name'] = contract.instrument_name

        if self.cryptocom:
            ob_data = self._make_request("GET", "/api/v1/tickers", data)
        else:
            ob_data = self._make_request("GET", "/api/v1/tickers", data)

        if ob_data is not None:
            if contract.instrument_name not in self.prices:  # Add the instrument_name to the dictionary if needed
                self.prices[contract.instrument_name] = {'bids': float(ob_data['bidPrice']), 'asks': float(ob_data['askPrice'])}
            else:
                self.prices[contract.instrument_name]['bids'] = float(ob_data['bidPrice'])
                self.prices[contract.instrument_name]['asks'] = float(ob_data['askPrice'])

            return self.prices[contract.instrument_name]

    def get_balances(self) -> typing.Dict[str, Balance]:

        """
        Get the current balance of the account, the data is different between Spot and cryptocom
        :return:
        """

        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        balances = dict()

        if self.cryptocom:
            account_data = self._make_request("GET", "/api/v1/get-accounts", data)
        else:
            account_data = self._make_request("GET", "/api/v1/get-accounts", data)

        if account_data is not None:
            if self.cryptocom:
                for a in account_data['assets']:
                    balances[a['asset']] = Balance(a, self.platform)
            else:
                for a in account_data['balances']:
                    balances[a['asset']] = Balance(a, self.platform)

        return balances

    def place_order(self, contract: Contract, order_type: str, quantity: float, side: str, price=None, tif=None) -> OrderStatus:

        """
        Place an order. Based on the order_type, the price and tif arguments are not required
        :param contract:
        :param order_type: LIMIT, MARKET, STOP, TAKE_PROFIT, LIQUIDATION
        :param quantity:
        :param side:
        :param price:
        :param tif:
        :return:
        """

        data = dict()
        data['instrument_name'] = contract.instrument_name
        data['side'] = side.upper()
        data['quantity'] = round(int(quantity / contract.lot_size) * contract.lot_size, 8)  # int() to round down
        data['type'] = order_type.upper()  # Makes sure the order type is in uppercase

        if price is not None:
            data['prices'] = round(round(price / contract.tick_size) * contract.tick_size, 8)
            data['prices'] = '%.*f' % (contract.price_decimals, data['prices'])  # Avoids scientific notation

        if tif is not None:
            data['timeInForce'] = tif

        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        if self.cryptocom:
            order_status = self._make_request("POST", "/api/v1/order", data)
        else:
            order_status = self._make_request("POST", "/api/v2/order", data)

        if order_status is not None:

            if not self.cryptocom:
                if order_status['status'] == "FILLED":
                    order_status['avg_price'] = self._get_execution_price(contract, order_status['order_id'])
                else:
                    order_status['avg_price'] = 0

            order_status = OrderStatus(order_status, self.platform)

        return order_status

    def cancel_order(self, contract: Contract, order_id: int) -> OrderStatus:

        data = dict()
        data['order_id'] = order_id
        data['instrument_name'] = contract.instrument_name

        data['timestamp'] = int(time.time() * 1000)
        data['signature'] = self._generate_signature(data)

        if self.cryptocom:
            order_status = self._make_request("DELETE", "/api/v1//cancel-order", data)
        else:
            order_status = self._make_request("DELETE", "/api/v2//cancel-order", data)

        if order_status is not None:
            if not self.cryptocom:
                # Get the average execution price based on the recent trades
                order_status['avg_price'] = self._get_execution_price(contract, order_id)
            order_status = OrderStatus(order_status, self.platform)

        return order_status

    def _get_execution_price(self, contract: Contract, order_id: int) -> float:

        """
        For CryptoCom Spot only, find the equivalent of the 'avgPrice' key on the cryptocom side.
        The average price is the weighted sum of each trade price related to the order_id
        :param contract:
        :param order_id:
        :return:
        """

        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['instrument_name'] = contract.instrument_name
        data['signature'] = self._generate_signature(data)

        trades = self._make_request("GET", "/api/v1/order", data)

        avg_price = 0

        if trades is not None:

            executed_qty = 0
            for t in trades:
                if t['order_id'] == order_id:
                    executed_qty += float(t['quantity'])

            for t in trades:
                if t['order_id'] == order_id:
                    fill_pct = float(t['quantity']) / executed_qty
                    avg_price += (float(t['price']) * fill_pct)  # Weighted sum

        return round(round(avg_price / contract.tick_size) * contract.tick_size, 8)

    def get_order_status(self, contract: Contract, order_id: int) -> OrderStatus:

        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['instrument_name'] = contract.instrument_name
        data['orderId'] = order_id
        data['signature'] = self._generate_signature(data)

        if self.cryptocom:
            order_status = self._make_request("GET", "/api/v1/get-orders", data)
        else:
            order_status = self._make_request("GET", "/api/v1/get-order", data)

        if order_status is not None:
            if not self.cryptocom:
                if order_status['status'] == "FILLED":
                    # Get the average execution price based on the recent trades
                    order_status['avg_price'] = self._get_execution_price(contract, order_id)
                else:
                    order_status['avg_price'] = 0

            order_status = OrderStatus(order_status, self.platform)

        return order_status

    def _start_ws(self):

        """
        Infinite loop (thus has to run in a Thread) that reopens the websocket connection in case it drops
        :return:
        """

        self.ws = websocket.WebSocketApp(self._wss_url, on_open=self._on_open, on_close=self._on_close,
                                         on_error=self._on_error, on_message=self._on_message)

        while True:
            try:
                if self.reconnect:  # Reconnect unless the interface is closed by the user
                    self.ws.run_forever()  # Blocking method that ends only if the websocket connection drops
                else:
                    break
            except Exception as e:
                logger.error("CryptoCom error in run_forever() method: %s", e)
            time.sleep(2)

    def _on_open(self, ws):
        logger.info("CryptoCom connection opened")

        self.ws_connected = True

        # The aggTrade channel is subscribed to in the _switch_strategy() method of strategy_component.py

        for channel in ["book", "aggTrade"]:
            for instrument_name in self.ws_subscriptions[channel]:
                self.subscribe_channel([self.contracts[instrument_name]], channel, reconnection=True)

        if "BTCCRO-PERP" not in self.ws_subscriptions["book"]:
            self.subscribe_channel([self.contracts["book.BTCCRO"]], "book")

    def _on_close(self, ws):

        """
        Callback method triggered when the connection drops
        :return:
        """
        logger.warning("CryptoCom Websocket connection closed")
        self.ws_connected = True

    def _on_error(self, ws, msg: str):

        """
        Callback method triggered in case of error
        :param msg:
        :return:
        """

        logger.error("CryptoCom connection error: %s", msg)

    def _on_message(self, ws, msg: str):

        """
        The websocket updates of the channels the program subscribed to will go through this callback method
        :param msg:
        :return:
        """

        data = json.loads(msg)

        if "u" in data and "A" in data:
            data['e'] = "bookTicker"  # For CryptoCom Spot, to make the data structure uniform with CryptoCom cryptocom
            # See the data structure difference here: https://CryptoCom-docs.github.io/apidocs/spot/en/#individual-instrument_name-book-ticker-streams

        if "e" in data:
            if data['e'] == "bookTicker":

                instrument_name = data['s']

                if instrument_name not in self.prices:
                    self.prices[instrument_name] = {'bids': float(data['b']), 'asks': float(data['a'])}
                else:
                    self.prices[instrument_name]['bids'] = float(data['b'])
                    self.prices[instrument_name]['asks'] = float(data['a'])

                # PNL Calculation

                try:
                    for b_index, strat in self.strategies.items():
                        if strat.contract.instrument_name == instrument_name:
                            for trade in strat.trades:
                                if trade.status == "open" and trade.entry_price is not None:
                                    if trade.side == "long":
                                        trade.pnl = (self.prices[instrument_name]['bids'] - trade.entry_price) * trade.quantity
                                    elif trade.side == "short":
                                        trade.pnl = (trade.entry_price - self.prices[instrument_name]['asks']) * trade.quantity
                except RuntimeError as e:  # Handles the case  the dictionary is modified while loop through it
                    logger.error("Error while looping through the CryptoCom strategies: %s", e)

            if data['e'] == "aggTrade":

                instrument_name = data['s']

                for key, strat in self.strategies.items():
                    if strat.contract.instrument_name == instrument_name:
                        res = strat.parse_trades(float(data['p']), float(data['q']), data['t'])  # Updates candlesticks
                        strat.check_trade(res)

    def subscribe_channel(self, contracts: typing.List[Contract], channel: str, reconnection=False):

        """
        Subscribe to updates on a specific topic for all the instrument_names.
        If your list is bigger than 300 instrument_names, the subscription will fail (observed on CryptoCom Spot).
        :param contracts:
        :param channel: aggTrades, bookTicker...
        :param reconnection: Force to subscribe to a instrument_name even if it already in self.ws_subscriptions[instrument_name] list
        :return:
        """

        if len(contracts) > 200:
            logger.warning("Subscribing to more than 200 instrument_names will most likely fail. "
                           "Consider subscribing only when adding a instrument_name to your Watchlist or when starting a "
                           "strategy for a instrument_name.")

        data = dict()
        data['method'] = "SUBSCRIBE"
        data['params'] = []

        if len(contracts) == 0:
            data['params'].append(channel)
        else:
            for contract in contracts:
                if contract.instrument_name not in self.ws_subscriptions[channel] or reconnection:
                    data['params'].append(contract.instrument_name.lower() + "@" + channel)
                    if contract.instrument_name not in self.ws_subscriptions[channel]:
                        self.ws_subscriptions[channel].append(contract.instrument_name)

            if len(data['params']) == 0:
                return

        data['id'] = self._ws_id

        try:
            self.ws.send(json.dumps(data))  # Converts the JSON object (dictionary) to a JSON string
            logger.info("CryptoCom: subscribing to: %s", ','.join(data['params']))
        except Exception as e:
            logger.error("Websocket error while subscribing to @bookTicker and @aggTrade: %s", e)

        self._ws_id += 1

    def get_trade_size(self, contract: Contract, price: float, balance_pct: float):

        """
        Compute the trade size for the strategy module based on the percentage of the balance to use
        that was defined in the strategy component.
        :param contract:
        :param price: Used to convert the amount to invest into an amount to buy/sell
        :param balance_pct:
        :return:
        """

        logger.info("Getting CryptoCom trade size...")

        balance = self.get_balances()

        if balance is not None:
            if contract.quote_asset in balance:  # On CryptoCom Spot, the quote asset isn't necessarily USDT
                if self.cryptocom:
                    balance = balance[contract.quote_ccy].wallet_balance
                else:
                    balance = balance[contract.quote_ccy].free
            else:
                return None
        else:
            return None

        trade_size = (balance * balance_pct / 100) / price

        trade_size = round(round(trade_size / contract.lot_size) * contract.lot_size, 8)  # Removes extra decimals

        logger.info("CryptoCom current %s balance = %s, trade size = %s", contract.quote_ccy, balance, trade_size)

        return trade_size









