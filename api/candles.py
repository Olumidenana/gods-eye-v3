"""
Vercel Serverless Function: GET /api/candles
Returns OHLC candles for TradingView / Lightweight Charts.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data_feed import fetch_live_candles

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        sym = query.get("symbol", ["XAUUSD"])[0]
        count = int(query.get("count", ["120"])[0])

        bars = fetch_live_candles(sym, granularity=300, count=count)
        payload = json.dumps({"ok": True, "symbol": sym, "candles": bars}).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)
