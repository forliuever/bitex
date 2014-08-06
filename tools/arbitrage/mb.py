#!/usr/bin/env python
import sys
import urllib2
from time import sleep
import json

from arbitrator import BlinkTradeArbitrator

import datetime
import hmac
import hashlib
import ConfigParser
from ws4py.exc import HandshakeError


MB_API_KEY = 'XXXX'
MB_API_SECRET = 'YYYY'

def send_order_to_MB(sender, order):
  nonce = datetime.datetime.now().strftime('%s')
  message = 'sendorder' + str(MB_API_KEY) + str(nonce)
  signature = hmac.new(MB_API_SECRET, msg=message, digestmod=hashlib.sha256).hexdigest().upper()

  post_params = {
    'key': MB_API_KEY,
    'sign': signature,
    'pair': 'btc_brl',
    'volume': float(order['OrderQty']/1.e8),
    'price': float( order['Price'] / 1.e8)
  }

  if msg['Side'] == '1':
    post_params['type'] = 'buy'
  elif msg['Side'] == '2':
    post_params['type'] = 'sell'

  print datetime.datetime.now(), 'POST https://www.mercadobitcoin.com.br/tapi/' + message, str(post_params)

def main():
  candidates = ['arbitrage.ini', 'mb.ini' ]
  if len(sys.argv) > 1:
    candidates.append(sys.argv[1])


  config = ConfigParser.SafeConfigParser({
    'websocket_url': 'wss://127.0.0.1/trade/',
    'username': '',
    'password': '',
    'buy_fee': 0,
    'sell_fee': 0,
    'api_key': 'KEY',
    'api_secret': 'SECRET'
  })
  config.read( candidates )

  websocket_url = config.get('mb', 'websocket_url')
  username      = config.get('mb', 'username')
  password      = config.get('mb', 'password')
  buy_fee       = int(config.get('mb', 'buy_fee'))
  sell_fee      = int(config.get('mb', 'sell_fee'))
  api_key       = config.get('mb', 'api_key')
  api_secret    = config.get('mb', 'api_secret')

  print 'websocket_url:', websocket_url
  print 'username:', username
  print 'buy_fee:', buy_fee
  print 'sell_fee:', sell_fee

  arbitrator = BlinkTradeArbitrator(username,password,websocket_url, 'BTCBRL')
  arbitrator.connect()

  arbitrator.signal_order.connect(send_order_to_MB)

  while True:
    try:
      sleep(5)
      if arbitrator.is_connected():
        arbitrator.send_testRequest()
      else:
        try:
          arbitrator.reconnect()
        except HandshakeError,e:
          continue

      try:
        raw_data = urllib2.urlopen('https://www.mercadobitcoin.com.br/api/orderbook/').read()
      except Exception:
        print 'ERROR RETRIEVING ORDER BOOK'
        continue

      bids_asks = []
      try:
        bids_asks = json.loads(raw_data)
      except  Exception :
        pass

      if bids_asks:
        ask_list = [ [  int(float(o[0]) * 1e8 * (1. + sell_fee) ) , int(o[1] * 1e8) ] for o in bids_asks['asks'] ]
        bid_list = [ [  int(float(o[0]) * 1e8 * (1. + buy_fee) ) , int(o[1] * 1e8) ] for o in bids_asks['bids'] ]
        arbitrator.process_ask_list(ask_list)
        arbitrator.process_bid_list(bid_list)

    except urllib2.URLError as e:
      print datetime.datetime.now(), e

    except KeyboardInterrupt:
      arbitrator.cancel_all_orders()
      print 'wait....'
      sleep(5)
      arbitrator.close()
      break

main()

