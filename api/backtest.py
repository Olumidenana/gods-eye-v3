"""
Vercel Serverless Function: GET /api/backtest
Runs Research Lab backtest engine on live/historical candles and returns Net R metrics.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data_feed import MARKET_SPECS, fetch_live_candles
from engine.backtest import run_backtest

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        sym = query.get("symbol", ["XAUUSD"])[0]
        enable_smt = query.get("enable_smt", ["1"])[0] == "1"
        tp1_r = float(query.get("tp1", ["1.25"])[0])
        tp2_r = float(query.get("tp2", ["3.50"])[0])
        count = int(query.get("count", ["300"])[0])

        spec = MARKET_SPECS.get(sym, MARKET_SPECS["XAUUSD"])
        bars = fetch_live_candles(sym, granularity=300, count=count)
        partner_bars = None
        if spec.get("partner"):
            partner_bars = fetch_live_candles(spec["partner"], granularity=300, count=count)

        report = run_backtest(
            bars=bars,
            partner_bars=partner_bars,
            symbol=sym,
            decimals=spec["decimals"],
            enable_smt=enable_smt,
            tp1_r=tp1_r,
            tp2_r=tp2_r
        )

        payload = json.dumps({"ok": True, "report": report}, indent=2).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)
