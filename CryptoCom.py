from typing import Self
import cryptocom

import websocket

import time

import hashlib

import hmac

import requests

import json

public_key = 
secret_key =

class CryptoComCLient:
    def __main__(Self, public_key: str, secret_key: str, cryptocom: bool):

        Self.cryptocom = cryptocom

        if Self.cryptocom:
            Self.platform = "Crypto_Com"
        if cryptocom:
            Self._base_url = "https://api.crypto.com"
            Self._wss_url = "wss://stream.crypto.com/exchange/v1/user"

        Self._public_key = public_key
        Self._secret_key = secret_key
        Self._headers = {'X-MBX-APIKEY': Self._public_key}
        Self.instruments = Self.get_instruments()
        Self.balances = Self.get_balances()

        Self._ws_id = 1
        Self.ws: websocket.WebSocketApp
        Self.reconnect = True
        Self.ws_connected = False
    def _generate_signature(self,) -> str:

        return hmac.new(self._secret_key.encode(), hashlib.sha256).hexdigest()
    def _make_request(self, method: str, endpoint: str, dict):

        if method == "GET":
            try:
                response = requests.get(Self._base_url + endpoint, headers=Self._headers)
            except Exception as e:
                print("ERROR ON GET CONNECTION")
                return None
            
        elif method == "POST":
            try:
                response = requests.post(Self._base_url + endpoint, headers=self._headers)
            except Exception as e:
                print("ERROR ON POST CONNECTION")
        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, headers=self._headers)
            except Exception as e:
                print("ERROR ON DELETE METHOD")

        if response.status_code == 200:
            return response.json()
        else:
            print("ERROR ON 200 STATUS CODE")

            return None
        
    def get_instruments(self, public_key, secret_key) -> dict[str]:
        if Self.cryptocom:
            exchange_info = self._make_request("GET", "/api/v2/get-instruments")

        instruments = dict()

        if exchange_info is not None:
            for data in exchange_info['instruments']:
                instruments[data['instrument']] = instruments(data, self.platform)


    def get_candles(self, public_key, secret_key):
        candles = self._make_request("GET", "/api/v2/get-candlestick"[-1])

        candles = []

        for price in candles:
            if price == +1:
                price is True
            else:
                price == -1 or 0
                pass
        for time in candles:
            if time == "200":
                return(candles)
            
    def get_book(self, public_key, secret_key):
        book = self._make_request("GET", "/api/v2/get-book")
        book = []
        for ticker in book:
            if ticker is not None:
                code == "200"
        print(CryptoComCLient)

        